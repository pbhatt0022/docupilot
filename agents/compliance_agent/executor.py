from typing import Dict, List
from datetime import datetime
from .rules.rules_engine import ComplianceRulesEngine
from .rules.rule_definitions import RuleCategory
# from agents.data.cosmos_utils import store_compliance_result
from agents.tools.mcp_client import callMCPTool

async def run_compliance_pipeline(
    applicant_id: str,
    loan_type: str,
    loan_amount: float,
    documents: Dict
) -> Dict:
    """
    Execute the compliance check pipeline with integrated rules engine
    """
    # Initialize rules engine
    rules_engine = ComplianceRulesEngine()
    
    # Get comprehensive application data from MCP tools
    credit_report = await callMCPTool("parse_credit_report", {"applicant_id": applicant_id})
    employment_data = await callMCPTool("verify_employment", {"applicant_id": applicant_id})
    bank_data = await callMCPTool("parse_bank_statements", {"applicant_id": applicant_id})
    kyc_data = await callMCPTool("verify_kyc_details", {"applicant_id": applicant_id})
    fraud_check = await callMCPTool("check_fraud_indicators", {"applicant_id": applicant_id})
    
    # Prepare comprehensive application data
    application_data = {
        "applicant_id": applicant_id,
        "loan_type": loan_type,
        "loan_amount": loan_amount,
        
        # Credit and Financial Data
        "credit_score": credit_report.get("credit_score", 0),
        "credit_history_years": credit_report.get("credit_history_years", 0),
        "existing_loans": credit_report.get("active_loans", []),
        "total_emi": credit_report.get("total_emi", 0),
        "credit_utilization": credit_report.get("credit_utilization", 0),
        
        # Employment and Income Data
        "employment_verified": employment_data.get("is_verified", False),
        "employment_type": employment_data.get("employment_type", ""),
        "employer_name": employment_data.get("employer_name", ""),
        "employment_duration": employment_data.get("duration_years", 0),
        "monthly_income": employment_data.get("monthly_income", 0),
        
        # Banking Data
        "avg_bank_balance": bank_data.get("average_balance", 0),
        "bank_statement_months": bank_data.get("months_covered", 0),
        "salary_credits": bank_data.get("salary_credits", []),
        "bounced_checks": bank_data.get("bounced_checks", 0),
        
        # KYC Data
        "kyc_verified": kyc_data.get("is_verified", False),
        "address_verified": kyc_data.get("address_verified", False),
        "identity_verified": kyc_data.get("identity_verified", False),
        "pan_verified": kyc_data.get("pan_verified", False),
        "document_expiry_dates": kyc_data.get("document_expiry_dates", {}),
        
        # Fraud Check Data
        "fraud_alerts": fraud_check.get("alerts", []),
        "risk_score": fraud_check.get("risk_score", 0),
        "blacklist_status": fraud_check.get("blacklisted", False),
        
        # Application Metadata
        "application_date": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }
    
    # Run comprehensive compliance checks
    is_compliant, violations, recommendations = await rules_engine.run_all_checks(
        application_data=application_data,
        documents=documents
    )
    
    # Categorize violations by rule type
    categorized_violations = {category.value: [] for category in RuleCategory}
    for violation in violations:
        rule_category = violation.get("rule_category", RuleCategory.COMPLIANCE.value)
        categorized_violations[rule_category].append(violation)
    
    # Prepare detailed result
    result = {
        "compliance_status": "COMPLIANT" if is_compliant else "NON_COMPLIANT",
        "application_summary": {
            "applicant_id": applicant_id,
            "loan_type": loan_type,
            "loan_amount": loan_amount,
            "credit_score": application_data["credit_score"],
            "monthly_income": application_data["monthly_income"],
            "risk_score": application_data["risk_score"]
        },
        "violations": {
            "kyc_violations": categorized_violations[RuleCategory.KYC.value],
            "identity_violations": categorized_violations[RuleCategory.IDENTITY.value],
            "income_violations": categorized_violations[RuleCategory.INCOME.value],
            "document_violations": categorized_violations[RuleCategory.FORM.value],
            "rbi_violations": categorized_violations[RuleCategory.RBI.value]
        },
        "missing_documents": [
            v["message"] for v in violations 
            if v["rule_id"].startswith("KYC") and "missing" in v["message"].lower()
        ],
        "risk_assessment": {
            "risk_level": "HIGH" if application_data["risk_score"] > 70 else 
                         "MEDIUM" if application_data["risk_score"] > 30 else "LOW",
            "fraud_alerts": application_data["fraud_alerts"],
            "risk_flags": [
                {
                    "type": v["rule_id"],
                    "category": v.get("rule_category", "UNKNOWN"),
                    "severity": v["severity"],
                    "message": v["message"]
                }
                for v in violations if v["severity"] == "HIGH"
            ]
        },
        "compliance_summary": {
            "kyc_status": "VERIFIED" if application_data["kyc_verified"] else "PENDING",
            "credit_status": "APPROVED" if application_data["credit_score"] >= 700 else "REJECTED",
            "fraud_check_status": "CLEAR" if not application_data["blacklist_status"] else "FLAGGED",
            "document_status": "COMPLETE" if not categorized_violations[RuleCategory.FORM.value] else "INCOMPLETE"
        },
        "recommendations": recommendations,
        "is_compliant": is_compliant,
        "timestamp": datetime.now().isoformat()
    }
    
    # Store comprehensive result in Cosmos DB
    # await store_compliance_result(applicant_id, result)
    
    return result
