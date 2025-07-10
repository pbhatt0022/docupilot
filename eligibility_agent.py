import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel #Data validation and parsing for API requests/responses
from typing import Dict, Any
from azure.cosmos import CosmosClient #Azure Cosmos DB client

# --- Load environment variables ---
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB = os.getenv("COSMOS_DB", "LoanApplicationDB")
COSMOS_CONTAINER = os.getenv("COSMOS_CONTAINER", "DocumentMetadata")

# --- Initialize Cosmos DB client ---
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.get_database_client(COSMOS_DB)
container = database.get_container_client(COSMOS_CONTAINER)

# --- Load eligibility rules (could be from file or DB) ---
def load_rules():
    # For now, use a static dict; replace with file/db as needed
    return {
        "min_age": 21,
        "max_age": 60,
        "min_income": 25000,
        "required_docs": ["Aadhaar Card", "PAN Card", "Salary Slip"]
    }

# --- FastAPI app ---
app = FastAPI(title="Eligibility Agent")

# --- Pydantic models for request/response ---
class EligibilityRequest(BaseModel):
    applicant_id: str

class EligibilityResult(BaseModel):
    eligible: bool
    reasoning: str
    missing_fields: list
    flagged: bool = False
    flagged_reason: str = ""

# --- Helper: Fetch applicant data from Cosmos DB ---
def fetch_applicant_data(applicant_id: str) -> Dict[str, Any]:
    query = f"SELECT * FROM c WHERE c.applicant_id = '{applicant_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if not items:
        raise ValueError("Applicant not found")
    # Aggregate extracted fields from all docs
    extracted = {}
    for item in items:
        extracted.update(item.get("extracted_fields", {}))
    return {
        "docs": items,
        "extracted_fields": extracted
    }

# --- Core: Apply eligibility rules ---
def evaluate_eligibility(applicant_data: Dict[str, Any], rules: Dict[str, Any]) -> EligibilityResult:
    extracted = applicant_data["extracted_fields"]
    docs = applicant_data["docs"]
    missing_fields = []
    reasoning = []

    # Check required docs
    uploaded_docs = [doc.get("predicted_classification") for doc in docs]
    for req_doc in rules["required_docs"]:
        if req_doc not in uploaded_docs:
            missing_fields.append(req_doc)
    if missing_fields:
        reasoning.append(f"Missing required documents: {', '.join(missing_fields)}")

    # Check age
    age = extracted.get("age")
    if age is not None:
        try:
            age = int(age)
            if age < rules["min_age"] or age > rules["max_age"]:
                reasoning.append(f"Applicant age {age} not in allowed range ({rules['min_age']}-{rules['max_age']})")
        except Exception:
            reasoning.append("Could not parse applicant age")
    else:
        missing_fields.append("age")
        reasoning.append("Missing applicant age")

    # Check income
    income = extracted.get("income")
    if income is not None:
        try:
            income = float(income)
            if income < rules["min_income"]:
                reasoning.append(f"Applicant income {income} below minimum {rules['min_income']}")
        except Exception:
            reasoning.append("Could not parse applicant income")
    else:
        missing_fields.append("income")
        reasoning.append("Missing applicant income")

    eligible = not missing_fields and not any("not in allowed range" in r or "below minimum" in r for r in reasoning)
    return EligibilityResult(
        eligible=eligible,
        reasoning="; ".join(reasoning) if reasoning else "Eligible",
        missing_fields=missing_fields
    )

# --- REST endpoint ---
@app.post("/check_eligibility", response_model=EligibilityResult)
def check_eligibility(req: EligibilityRequest):
    try:
        applicant_data = fetch_applicant_data(req.applicant_id)
        rules = load_rules()
        result = evaluate_eligibility(applicant_data, rules)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- For local testing only ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 