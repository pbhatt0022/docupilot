from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
import os

from dotenv import load_dotenv
load_dotenv()

from agents.data.blob_utils import download_json_blob
import asyncio
from agents.data.cosmos_utils import get_applicant_contact_info
import time
from agents.data.cosmos_utils import get_all_applicant_ids, mark_submission_email_sent
from agents.data.cosmos_utils import get_all_eligibility_results, mark_eligibility_email_sent

app = FastAPI(title="Communication Agent (Email Notifications)")

# Logic App URL for sending emails
LOGIC_APP_URL = os.getenv("LOGIC_APP_URL")
class CommunicationRequest(BaseModel):
    applicant_id: str
    customer_name: str
    customer_email: str
    eligibility_decision: dict  # JSON output from eligibility agent
    notification_type: Optional[str] = None  # New field for notification stage/type

class CommunicationResponse(BaseModel):
    success: bool
    message: str
    email_sent: bool

def format_eligibility_decision(decision: dict) -> dict:
    """
    Format the eligibility decision for email communication
    """
    decision_mapping = {
        "Yes": "APPROVED",
        "No": "REJECTED", 
        "Needs Review": "UNDER REVIEW"
    }
    
    # Map the decision to email-friendly status
    status = decision_mapping.get(decision.get("decision", "Needs Review"), "UNDER REVIEW")
    
    # Build the reason text
    reason = decision.get("reason", "No specific reason provided")
    
    # Handle missing fields
    missing_fields = decision.get("missing_fields", [])
    missing_fields_text = ""
    if missing_fields:
        missing_fields_text = f"\n\nMissing Required Documents:\n" + "\n".join([f"• {field}" for field in missing_fields])
    
    # Handle flagged cases
    flagged = decision.get("flagged", False)
    flagged_reason = decision.get("flagged_reason", "")
    flagged_text = ""
    if flagged and flagged_reason:
        flagged_text = f"\n\n⚠️ FLAGGED FOR REVIEW:\n{flagged_reason}"
    
    return {
        "status": status,
        "reason": reason,
        "missing_fields_text": missing_fields_text,
        "flagged_text": flagged_text
    }

# --- EMAIL GENERATION HELPERS ---

def generate_submission_email(customer_name: str) -> dict:
    """
    Generate email content for submission confirmation.
    """
    subject = f"Loan Application Submitted - {customer_name}"
    body = f"""
Dear {customer_name},

Thank you for submitting your loan application. We have received your application and will begin processing it shortly.

You will receive updates as your application progresses through verification and eligibility checks.

Best regards,
Loan Processing Team
    """
    return {"subject": subject.strip(), "body": body.strip()}

def generate_verification_email(customer_name: str, missing_info: str = "") -> dict:
    """
    Generate email content for verification update.
    If missing_info is provided, it will be included in the email.
    """
    subject = f"Loan Application Verification Update - {customer_name}"
    if missing_info:
        body = f"""
Dear {customer_name},

Your document verification is complete. However, the following information is missing or incomplete:
{missing_info}

Please provide the required information to proceed with your application.

Best regards,
Loan Processing Team
        """
    else:
        body = f"""
Dear {customer_name},

Your documents have been successfully verified. No missing information was found.

We will now proceed to the eligibility check. You will receive another update soon.

Best regards,
Loan Processing Team
        """
    return {"subject": subject.strip(), "body": body.strip()}

def generate_eligibility_email(customer_name: str, formatted_decision: dict) -> dict:
    """
    Generate email content for eligibility decision (approved, rejected, under review).
    """
    status = formatted_decision["status"]
    reason = formatted_decision["reason"]
    missing_fields_text = formatted_decision["missing_fields_text"]
    flagged_text = formatted_decision["flagged_text"]
    if status == "APPROVED":
        subject = f"🎉 Loan Application Approved - {customer_name}"
        body = f"""
Dear {customer_name},

We are pleased to inform you that your loan application has been APPROVED!

📋 Decision Details:
• Status: APPROVED
• Reason: {reason}

Next Steps:
1. You will receive detailed loan terms within 2-3 business days
2. Please review the terms and conditions carefully
3. Contact our loan officer if you have any questions

Thank you for choosing our services!

Best regards,
Loan Processing Team
        """
    elif status == "REJECTED":
        subject = f"Loan Application Update - {customer_name}"
        body = f"""
Dear {customer_name},

We regret to inform you that your loan application has been REJECTED.

📋 Decision Details:
• Status: REJECTED
• Reason: {reason}{missing_fields_text}

We understand this may be disappointing. If you believe there has been an error or if your circumstances have changed, you may:
1. Request a review of your application
2. Reapply after addressing the identified issues
3. Contact our customer service for guidance

Thank you for your interest in our services.

Best regards,
Loan Processing Team
        """
    else:  # UNDER REVIEW
        subject = f"Loan Application Under Review - {customer_name}"
        body = f"""
Dear {customer_name},

Your loan application is currently UNDER REVIEW.

📋 Current Status:
• Status: UNDER REVIEW
• Reason: {reason}{missing_fields_text}{flagged_text}

We are carefully evaluating your application and may need additional information. You will be contacted if:
• Additional documents are required
• Clarification is needed on any information
• A decision has been reached

We appreciate your patience during this process.

Best regards,
Loan Processing Team
        """
    return {"subject": subject.strip(), "body": body.strip()}

def generate_decision_email(customer_name: str, decision: str, explanation: str = "") -> dict:
    """
    Generate email content for final decision (preapproved, approved, or rejected).
    """
    subject = f"Loan Application Decision - {customer_name}"
    body = f"""
Dear {customer_name},

We are writing to inform you that your loan application has been {decision.upper()}.

{explanation}

If you have any questions or require further clarification, please contact our support team.

Best regards,
Loan Processing Team
    """
    return {"subject": subject.strip(), "body": body.strip()}

# --- MAIN NOTIFICATION ENDPOINT ---

@app.post("/send-notification", response_model=CommunicationResponse)
async def send_notification(request: CommunicationRequest):
    """
    Send an email notification based on the notification_type:
    - submission: Fetch ApplicantName and email from Cosmos DB using applicant_id
    - verification: Use provided customer_name and customer_email
    - eligibility: Use provided customer_name and customer_email
    - decision: Use provided customer_name and customer_email
    """
    try:
        notification_type = request.notification_type or "unspecified"
        print(f"Notification type: {notification_type}")

        # --- Branch logic for each notification type ---
        if notification_type == "submission":
            # Fetch from Cosmos DB and generate email content
            customer_name, customer_email = get_applicant_contact_info(request.applicant_id)
            if not customer_name or not customer_email:
                raise HTTPException(status_code=404, detail="ApplicantName or email not found in Cosmos DB.")
            email_content = generate_submission_email(customer_name)
        elif notification_type == "verification":
            customer_name = request.customer_name
            customer_email = request.customer_email
            missing_info = request.eligibility_decision.get("missing_info", "")
            email_content = generate_verification_email(customer_name, missing_info)
        elif notification_type == "eligibility":
            customer_name = request.customer_name
            customer_email = request.customer_email
            formatted_decision = format_eligibility_decision(request.eligibility_decision)
            email_content = generate_eligibility_email(customer_name, formatted_decision)
        elif notification_type == "decision":
            customer_name = request.customer_name
            customer_email = request.customer_email
            decision = request.eligibility_decision.get("decision", "Undecided")
            explanation = request.eligibility_decision.get("reason", "No explanation provided.")
            email_content = generate_decision_email(customer_name, decision, explanation)
        else:
            customer_name = request.customer_name
            customer_email = request.customer_email
            formatted_decision = format_eligibility_decision(request.eligibility_decision)
            email_content = generate_eligibility_email(customer_name, formatted_decision)

        # --- Send the email via Logic App ---
        payload = {
            "customer_name": customer_name,
            "customer_email": customer_email,
            "subject": email_content["subject"],
            "body": email_content["body"]
        }
        response = requests.post(LOGIC_APP_URL, json=payload)
        if response.status_code == 200:
            return CommunicationResponse(
                success=True,
                message="Email notification sent successfully",
                email_sent=True
            )
        else:
            return CommunicationResponse(
                success=False,
                message=f"Failed to send email. Status code: {response.status_code}",
                email_sent=False
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending notification: {str(e)}")

@app.post("/format-decision")
async def format_decision_only(request: CommunicationRequest):
    """
    Format eligibility decision for preview (without sending email)
    """
    try:
        formatted_decision = format_eligibility_decision(request.eligibility_decision)
        email_content = generate_eligibility_email(request.customer_name, formatted_decision) # Use generate_eligibility_email for consistency
        
        return {
            "formatted_decision": formatted_decision,
            "email_content": email_content,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error formatting decision: {str(e)}")

@app.get("/example-eligibility-output")
async def get_example_eligibility_output():
    """
    Show example of how to use the communication agent with eligibility agent output
    """
    example_eligibility_output = {
        "decision": "Yes",
        "reason": "All documents are consistent, applicant meets all criteria, and loan amount is within range.",
        "missing_fields": [],
        "flagged": False,
        "flagged_reason": ""
    }
    
    example_request = {
        "applicant_id": "APP123456",
        "customer_name": "John Smith",
        "customer_email": "john.smith@email.com",
        "eligibility_decision": example_eligibility_output
    }
    
    return {
        "message": "Example of how to connect eligibility agent with communication agent",
        "example_eligibility_output": example_eligibility_output,
        "example_communication_request": example_request,
        "usage": "POST /send-notification with the communication request to send email"
    }

class NotificationFromBlobRequest(BaseModel):
    applicant_id: str
    notification_type: Optional[str] = None

@app.post("/send-notification-from-blob", response_model=CommunicationResponse)
async def send_notification_from_blob(request: NotificationFromBlobRequest):
    """
    Fetch the notification payload from Azure Blob Storage and send the email.
    """
    try:
        file_name = f"{request.applicant_id}-eligibility.json"
        blob_data = await download_json_blob("eligibility-reports", file_name)
        # Expect blob_data to contain at least customer_name, customer_email, eligibility_decision
        customer_name = blob_data.get("customer_name")
        customer_email = blob_data.get("customer_email")
        eligibility_decision = blob_data.get("eligibility_decision", blob_data)  # fallback: blob is the decision
        # Reuse the main notification logic
        comm_request = CommunicationRequest(
            applicant_id=request.applicant_id,
            customer_name=customer_name,
            customer_email=customer_email,
            eligibility_decision=eligibility_decision,
            notification_type=request.notification_type
        )
        # Call the main notification logic
        # Since send_notification is async, call it directly
        return await send_notification(comm_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending notification from blob: {str(e)}")

def get_applicant_main_doc(applicant_id):
    """
    Helper to fetch the main applicant document (with loan_application) for a given applicant_id.
    """
    from agents.data.cosmos_utils import container
    query = "SELECT * FROM c WHERE c.applicant_id = @applicant_id AND IS_DEFINED(c.loan_application)"
    params = [{"name": "@applicant_id", "value": applicant_id}]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    return items[0] if items else None

notified_applicants = set()  # In-memory set to avoid duplicate notifications per process run

async def auto_send_submission_notifications(interval_seconds: int = 60):
    """
    Periodically fetch all applicant IDs and send submission notifications for new applicants.
    Now checks submission_email_sent in Cosmos DB to avoid duplicates.
    """
    while True:
        try:
            applicant_ids = get_all_applicant_ids()
            for applicant_id in applicant_ids:
                # Fetch main doc to check submission_email_sent
                main_doc = get_applicant_main_doc(applicant_id)
                if not main_doc:
                    print(f"[AUTO] No main doc for applicant_id: {applicant_id}")
                    continue
                if main_doc.get("submission_email_sent") is True:
                    continue  # Already sent
                customer_name, customer_email = get_applicant_contact_info(applicant_id)
                print(f"[DEBUG] applicant_id: {applicant_id}, customer_name: {customer_name}, customer_email: {customer_email}")
                if customer_name and customer_email:
                    comm_request = CommunicationRequest(
                        applicant_id=applicant_id,
                        customer_name=customer_name,
                        customer_email=customer_email,
                        eligibility_decision={},
                        notification_type="submission"
                    )
                    # Call the main notification logic
                    try:
                        await send_notification(comm_request)
                        mark_submission_email_sent(applicant_id)
                        print(f"[AUTO] Submission email sent for applicant_id: {applicant_id}")
                    except Exception as e:
                        print(f"[AUTO] Failed to send email for {applicant_id}: {e}")
                else:
                    print(f"[AUTO] Missing name/email for applicant_id: {applicant_id}")
        except Exception as e:
            print(f"[AUTO] Error in auto notification loop: {e}")
        await asyncio.sleep(interval_seconds)

async def auto_send_eligibility_notifications(interval_seconds: int = 60):
    """
    Periodically fetch all eligibility result documents and send eligibility emails for those not yet sent.
    """
    while True:
        try:
            eligibility_results = get_all_eligibility_results()
            for result in eligibility_results:
                applicant_id = result.get("applicant_id")
                if not applicant_id:
                    continue
                if result.get("email_sent") is True:
                    continue  # Already sent
                # Fetch applicant contact info
                customer_name, customer_email = get_applicant_contact_info(applicant_id)
                print(f"[DEBUG][ELIG] applicant_id: {applicant_id}, customer_name: {customer_name}, customer_email: {customer_email}")
                if customer_name and customer_email:
                    # Prepare eligibility_decision for email
                    eligibility_decision = result.get("report", {})
                    comm_request = CommunicationRequest(
                        applicant_id=applicant_id,
                        customer_name=customer_name,
                        customer_email=customer_email,
                        eligibility_decision=eligibility_decision,
                        notification_type="eligibility"
                    )
                    try:
                        await send_notification(comm_request)
                        mark_eligibility_email_sent(applicant_id)
                        print(f"[AUTO][ELIG] Eligibility email sent for applicant_id: {applicant_id}")
                    except Exception as e:
                        print(f"[AUTO][ELIG] Failed to send eligibility email for {applicant_id}: {e}")
                else:
                    print(f"[AUTO][ELIG] Missing name/email for applicant_id: {applicant_id}")
        except Exception as e:
            print(f"[AUTO][ELIG] Error in auto eligibility notification loop: {e}")
        await asyncio.sleep(interval_seconds)

@app.on_event("startup")
async def startup_event():
    # Start the background tasks for auto notifications
    asyncio.create_task(auto_send_submission_notifications())
    asyncio.create_task(auto_send_eligibility_notifications())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8001,
        reload=True
    )
