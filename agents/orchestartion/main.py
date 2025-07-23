from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import requests
from datetime import datetime
from agents.data.cosmos_utils import container, store_eligibility_result
from agents.communication_agent.main import CommunicationRequest
from agents.audit.audit_logger import audit_ai_decision, AuditLogger
import logging

app = FastAPI(title="DocuPilot Orchestration Service")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ApplicationSubmission(BaseModel):
    applicant_id: str
    documents: List[Dict[str, Any]]
    loan_application: Dict[str, Any]

class ProcessingStatus(BaseModel):
    applicant_id: str
    stage: str
    status: str
    details: Dict[str, Any]
    timestamp: str

# Application state tracking
APPLICATION_STAGES = [
    "submitted",
    "classification_complete", 
    "extraction_complete",
    "validation_complete",
    "eligibility_complete",
    "officer_review",
    "decision_made",
    "notification_sent"
]

async def update_application_status(applicant_id: str, stage: str, status: str, details: Dict = None):
    """Update application processing status in Cosmos DB"""
    try:
        status_doc = {
            "id": f"{applicant_id}_status",
            "applicant_id": applicant_id,
            "type": "application_status",
            "stage": stage,
            "status": status,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        container.upsert_item(status_doc)
        logger.info(f"Updated status for {applicant_id}: {stage} - {status}")
    except Exception as e:
        logger.error(f"Failed to update status for {applicant_id}: {e}")

async def run_classification_pipeline(applicant_id: str):
    """Run classification for all documents of an applicant"""
    try:
        # Get all documents for applicant
        query = "SELECT * FROM c WHERE c.applicant_id = @applicant_id AND c.type != @type"
        params = [
            {"name": "@applicant_id", "value": applicant_id},
            {"name": "@type", "value": "application_status"}
        ]
        docs = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        
        classified_count = 0
        for doc in docs:
            if doc.get("predicted_classification"):
                classified_count += 1
        
        await update_application_status(
            applicant_id, 
            "classification_complete", 
            "success",
            {"total_documents": len(docs), "classified_documents": classified_count}
        )
        return True
    except Exception as e:
        await update_application_status(applicant_id, "classification_complete", "failed", {"error": str(e)})
        return False

async def run_extraction_pipeline(applicant_id: str):
    """Run field extraction for all documents"""
    try:
        # This would integrate with your existing extraction logic
        # For now, we'll assume extraction happens during upload
        await update_application_status(applicant_id, "extraction_complete", "success")
        return True
    except Exception as e:
        await update_application_status(applicant_id, "extraction_complete", "failed", {"error": str(e)})
        return False

async def run_validation_pipeline(applicant_id: str):
    """Run document validation checks"""
    try:
        # Check for required documents
        required_docs = ["PAN Card", "Passport", "Bank Statement", "Income Tax Return", "Credit Report"]
        
        query = "SELECT c.predicted_classification FROM c WHERE c.applicant_id = @applicant_id"
        params = [{"name": "@applicant_id", "value": applicant_id}]
        docs = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        
        found_types = set(doc.get("predicted_classification") for doc in docs if doc.get("predicted_classification"))
        missing_docs = [doc for doc in required_docs if doc not in found_types]
        
        validation_result = {
            "required_documents": required_docs,
            "found_documents": list(found_types),
            "missing_documents": missing_docs,
            "is_complete": len(missing_docs) == 0
        }
        
        status = "success" if len(missing_docs) == 0 else "incomplete"
        await update_application_status(applicant_id, "validation_complete", status, validation_result)
        return len(missing_docs) == 0
    except Exception as e:
        await update_application_status(applicant_id, "validation_complete", "failed", {"error": str(e)})
        return False

async def run_eligibility_pipeline(applicant_id: str):
    """Run eligibility assessment"""
    try:
        # Call eligibility agent
        response = requests.post(
            "http://localhost:8000/check-eligibility",
            json={"applicant_id": applicant_id},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Log audit event for eligibility decision
            audit_ai_decision(
                applicant_id=applicant_id,
                agent_type="eligibility",
                decision=result,
                confidence_score=result.get("score")
            )
            
            await update_application_status(
                applicant_id, 
                "eligibility_complete", 
                "success",
                {
                    "decision": result.get("decision"),
                    "score": result.get("score"),
                    "summary": result.get("summary")
                }
            )
            return True
        else:
            await update_application_status(applicant_id, "eligibility_complete", "failed", {"error": "Eligibility service error"})
            return False
    except Exception as e:
        await update_application_status(applicant_id, "eligibility_complete", "failed", {"error": str(e)})
        return False

async def send_notification(applicant_id: str, notification_type: str):
    """Send notification to customer"""
    try:
        # Get customer info and eligibility result
        from agents.data.cosmos_utils import get_applicant_contact_info
        customer_name, customer_email = get_applicant_contact_info(applicant_id)
        
        if not customer_name or not customer_email:
            raise Exception("Customer contact info not found")
        
        # Get eligibility decision for notification
        eligibility_query = "SELECT * FROM c WHERE c.applicant_id = @applicant_id AND c.type = @type"
        params = [
            {"name": "@applicant_id", "value": applicant_id},
            {"name": "@type", "value": "eligibility_result"}
        ]
        eligibility_docs = list(container.query_items(query=eligibility_query, parameters=params, enable_cross_partition_query=True))
        
        eligibility_decision = {}
        if eligibility_docs:
            eligibility_decision = eligibility_docs[0].get("report", {})
        
        # Send notification
        comm_request = CommunicationRequest(
            applicant_id=applicant_id,
            customer_name=customer_name,
            customer_email=customer_email,
            eligibility_decision=eligibility_decision,
            notification_type=notification_type
        )
        
        notification_response = requests.post(
            "http://localhost:8001/send-notification",
            json=comm_request.dict(),
            timeout=30
        )
        
        if notification_response.status_code == 200:
            await update_application_status(applicant_id, "notification_sent", "success", {"type": notification_type})
            
            # Log notification audit event
            AuditLogger.log_notification_sent(
                applicant_id=applicant_id,
                notification_type=notification_type,
                recipient=customer_email,
                success=True
            )
            
            return True
        else:
            await update_application_status(applicant_id, "notification_sent", "failed", {"error": "Notification service error"})
            
            # Log failed notification
            AuditLogger.log_notification_sent(
                applicant_id=applicant_id,
                notification_type=notification_type,
                recipient=customer_email,
                success=False
            )
            
            return False
    except Exception as e:
        await update_application_status(applicant_id, "notification_sent", "failed", {"error": str(e)})
        
        # Log failed notification
        AuditLogger.log_notification_sent(
            applicant_id=applicant_id,
            notification_type=notification_type,
            recipient="unknown",
            success=False
        )
        
        return False

async def process_application_pipeline(applicant_id: str):
    """Run the complete application processing pipeline"""
    logger.info(f"Starting processing pipeline for applicant {applicant_id}")
    
    # Stage 1: Classification
    if not await run_classification_pipeline(applicant_id):
        return
    
    # Stage 2: Extraction (already done during upload, just mark complete)
    if not await run_extraction_pipeline(applicant_id):
        return
    
    # Stage 3: Validation
    validation_success = await run_validation_pipeline(applicant_id)
    
    # Stage 4: Eligibility (run even if validation incomplete)
    eligibility_success = await run_eligibility_pipeline(applicant_id)
    
    # Stage 5: Determine next step
    if validation_success and eligibility_success:
        await update_application_status(applicant_id, "officer_review", "ready")
        # Send submission confirmation
        await send_notification(applicant_id, "submission")
    else:
        await update_application_status(applicant_id, "officer_review", "requires_attention")
        # Send notification about issues
        await send_notification(applicant_id, "verification")

@app.post("/process-application")
async def process_application(submission: ApplicationSubmission, background_tasks: BackgroundTasks):
    """Trigger application processing pipeline"""
    try:
        # Mark as submitted
        await update_application_status(submission.applicant_id, "submitted", "processing")
        
        # Start background processing
        background_tasks.add_task(process_application_pipeline, submission.applicant_id)
        
        return {
            "status": "accepted",
            "message": f"Application {submission.applicant_id} is being processed",
            "applicant_id": submission.applicant_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{applicant_id}")
async def get_application_status(applicant_id: str):
    """Get current processing status of an application"""
    try:
        query = "SELECT * FROM c WHERE c.applicant_id = @applicant_id AND c.type = @type"
        params = [
            {"name": "@applicant_id", "value": applicant_id},
            {"name": "@type", "value": "application_status"}
        ]
        status_docs = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        
        if not status_docs:
            return {"applicant_id": applicant_id, "stage": "not_found", "status": "unknown"}
        
        latest_status = max(status_docs, key=lambda x: x.get("timestamp", ""))
        return {
            "applicant_id": applicant_id,
            "stage": latest_status.get("stage"),
            "status": latest_status.get("status"),
            "details": latest_status.get("details", {}),
            "timestamp": latest_status.get("timestamp")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/officer-decision")
async def record_officer_decision(applicant_id: str, decision: str, reason: str, officer_id: str):
    """Record loan officer's final decision"""
    try:
        decision_doc = {
            "id": f"{applicant_id}_officer_decision",
            "applicant_id": applicant_id,
            "type": "officer_decision",
            "decision": decision,
            "reason": reason,
            "officer_id": officer_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        container.upsert_item(decision_doc)
        
        # Log officer decision audit event
        from agents.audit.audit_logger import audit_officer_action
        audit_officer_action(
            applicant_id=applicant_id,
            action_type="final_decision",
            details={
                "decision": decision,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            },
            officer_id=officer_id
        )
        
        await update_application_status(applicant_id, "decision_made", "complete", {
            "decision": decision,
            "officer_id": officer_id
        })
        
        # Send final notification
        notification_type = "eligibility" if decision in ["approved", "rejected"] else "decision"
        await send_notification(applicant_id, notification_type)
        
        return {"status": "success", "message": "Decision recorded and notification sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)