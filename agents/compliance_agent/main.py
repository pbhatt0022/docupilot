from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from .executor import run_compliance_pipeline
from .rules.rule_definitions import RuleCategory
from agents.data.cosmos_utils import get_full_applicant_data

app = FastAPI(title="Loan Compliance Agent")

class Document(BaseModel):
    document_path: str
    document_type: str
    uploaded_date: Optional[datetime] = Field(default_factory=datetime.now)
    metadata: Optional[dict] = None

class ComplianceRequest(BaseModel):
    applicant_id: str
    # All other fields will be fetched from Cosmos DB

class ViolationDetail(BaseModel):
    rule_id: str
    rule_category: str
    severity: str
    message: str
    recommendation: Optional[str] = None

class RiskFlag(BaseModel):
    type: str
    category: str
    severity: str
    message: str
    detection_time: datetime = Field(default_factory=datetime.now)

class ComplianceSummary(BaseModel):
    kyc_status: str
    credit_status: str
    fraud_check_status: str
    document_status: str

class ApplicationSummary(BaseModel):
    applicant_id: str
    loan_type: str
    loan_amount: float
    credit_score: int
    monthly_income: float
    risk_score: float

class ComplianceResponse(BaseModel):
    compliance_status: str
    application_summary: ApplicationSummary
    violations: Dict[str, List[ViolationDetail]]  # Categorized violations
    missing_documents: List[str]
    risk_assessment: Dict[str, any]
    compliance_summary: ComplianceSummary
    recommendations: List[str]
    is_compliant: bool
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"arbitrary_types_allowed": True}

@app.post("/check-compliance")
async def check_compliance(request: ComplianceRequest):
    """
    Check loan application compliance with regulatory requirements
    """
    try:
        applicant_data = get_full_applicant_data(request.applicant_id)
        if not applicant_data:
            raise HTTPException(status_code=404, detail=f"Applicant {request.applicant_id} not found in database.")

        documents = {doc["type"]: doc for doc in applicant_data.get("documents", []) if "type" in doc}

        result = await run_compliance_pipeline(
            applicant_id=request.applicant_id,
            loan_type=applicant_data.get("loan_purpose"),
            loan_amount=applicant_data.get("loan_amount"),
            documents=documents,
            credit_score=applicant_data.get("credit_score"),
            income=applicant_data.get("income"),
            dob=applicant_data.get("dob"),
            tenure_months=applicant_data.get("tenure_months"),
            emi=applicant_data.get("emi"),
            interest_rate=applicant_data.get("interest_rate"),
            name=applicant_data.get("name"),
            email=applicant_data.get("email"),
            phone=applicant_data.get("phone")
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print("Exception in /check-compliance endpoint:", e)
        raise HTTPException(status_code=500, detail=f"Error processing compliance check: {str(e)}")

@app.get("/compliance-requirements")
async def get_compliance_requirements():
    """
    Get the list of compliance requirements and document checklist
    """
    from .rules.rule_definitions import INTERNAL_RULES, RBI_RULES, RuleCategory
    
    # Group rules by category
    kyc_rules = [r for r in INTERNAL_RULES if r.category == RuleCategory.KYC]
    identity_rules = [r for r in INTERNAL_RULES if r.category == RuleCategory.IDENTITY]
    document_rules = [r for r in INTERNAL_RULES if r.category == RuleCategory.FORM]
    income_rules = [r for r in INTERNAL_RULES if r.category == RuleCategory.INCOME]
    rbi_rules = [r for r in RBI_RULES]
    
    return {
        "kyc_requirements": {
            "rules": [
                {
                    "id": r.rule_id,
                    "title": r.title,
                    "content": r.content
                } for r in kyc_rules
            ],
            "required_documents": {
                "optional": {
                    "aadhaar": {
                        "name": "Aadhaar Card",
                        "type": "IDENTITY",
                        "validity_duration": "PERMANENT"
                    },
                    "pan_card": {
                        "name": "PAN Card",
                        "type": "IDENTITY",
                        "validity_duration": "PERMANENT"
                    }
                },
                "mandatory": {
                    "passport": {
                        "name": "Passport",
                        "type": "IDENTITY",
                        "validity_duration": "10_YEARS"
                    }
                }
            }
        },
        "document_requirements": {
            "rules": [
                {
                    "id": r.rule_id,
                    "title": r.title,
                    "content": r.content,
                    "validation_criteria": r.validation_criteria if hasattr(r, 'validation_criteria') else None
                } for r in document_rules
            ],
            "income_proof": {
                "mandatory": {
                    "bank_statements": {
                        "name": "Bank Statements",
                        "type": "FINANCIAL",
                        "required_duration": "6_MONTHS",
                        "max_age": "1_MONTH"
                    },
                    "income_proof": {
                        "name": "Income Proof",
                        "type": "FINANCIAL",
                        "accepted_types": ["Form 16", "Salary Slips", "Income Tax Returns"],
                        "max_age": "3_MONTHS"
                    }
                },
                "employment_proof": {
                    "name": "Employment Proof",
                    "type": "EMPLOYMENT",
                    "max_age": "3_MONTHS"
                }
            }
        },
        "rbi_guidelines": {
            "rules": [
                {
                    "id": r.rule_id,
                    "title": r.title,
                    "content": r.content,
                    "source": r.source,
                    "entity": r.entity,
                    "enforcement_level": "MANDATORY"
                }
                for r in rbi_rules
            ]
        },
        "verification_requirements": {
            "identity_verification": {
                "name_match": "EXACT",
                "address_match": "FUZZY",
                "age_criteria": {
                    "min_age": 21,
                    "max_age": 58
                }
            },
            "income_verification": {
                "minimum_income": 25000,
                "proof_requirements": ["SALARY_SLIPS", "BANK_STATEMENTS"],
                "consistency_check": "REQUIRED"
            },
            "credit_requirements": {
                "minimum_credit_score": 700,
                "maximum_dti_ratio": 0.40,
                "credit_report_max_age": "1_MONTH"
            }
        },
        "fraud_prevention": {
            "document_checks": {
                "tampering_detection": "REQUIRED",
                "digital_verification": "REQUIRED",
                "signature_validation": "REQUIRED"
            },
            "risk_thresholds": {
                "high_risk_score": 70,
                "medium_risk_score": 30
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agents.compliance_agent.main:app",
        host="0.0.0.0",
        port=8004,
        reload=True
    )
