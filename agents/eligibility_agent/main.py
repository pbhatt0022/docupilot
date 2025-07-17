from fastapi import FastAPI, HTTPException
from models import EligibilityRequest, EligibilityDecision
from azure.cosmos import CosmosClient
from gpt_client import call_gpt_eligibility
import os
import json

app = FastAPI(title="Eligibility Agent (GPT-powered")

# Cosmos DB setup
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DB_NAME = os.getenv("COSMOS_DB", "LoanApplicationDB")
CONTAINER_NAME = os.getenv("COSMOS_CONTAINER", "DocumentMetadata")
client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
container = client.get_database_client(DB_NAME).get_container_client(CONTAINER_NAME)

def build_gpt_prompt(applicant_id: str, docs: list) -> str:
    # Aggregate extracted fields and document summaries
    extracted_fields = {}
    doc_summaries = []
    for doc in docs:
        doc_type = doc.get("predicted_classification", "")
        ef = doc.get("extracted_fields", {})
        doc_summaries.append({
            "type": doc_type,
            "fields": ef
        })
        for k, v in ef.items():
            if k not in extracted_fields or not extracted_fields[k]:
                extracted_fields[k] = v

    # Example loan request and bank product info (stubbed for now)
    loan_request = {
        "amount": extracted_fields.get("loan_amount", "N/A"),
        "purpose": extracted_fields.get("loan_purpose", "N/A")
    }
    bank_products = {
        "min_amount": 50000,
        "max_amount": 2000000,
        "min_rate": 8.5,
        "max_rate": 12.0
    }

    # Few-shot example (optional, can be expanded)
    few_shot = """
Example:
Applicant Data:
- Extracted fields: {"age": 30, "income": 60000, "address": "123 Main St"}
- Documents: [{"type": "PAN Card", "fields": {"name": "A. Kumar"}}, ...]
- Loan request: {"amount": 300000, "purpose": "Home Renovation"}
- Bank products: {"min_amount": 50000, "max_amount": 2000000, "min_rate": 8.5, "max_rate": 12.0}
Response:
{
  "decision": "Yes",
  "reason": "All documents are consistent, applicant meets all criteria, and loan amount is within range.",
  "missing_fields": [],
  "flagged": false,
  "flagged_reason": ""
}
"""

    prompt = f"""
You are a loan eligibility expert. Given the following applicant data and documents, decide if the applicant qualifies for a personal loan.
Check for:
- Consistency of identity, address, and income across documents
- Presence of all required documents (PAN Card, Income Tax Return, Bank Statement, Credit Report, Passport)
- Whether the applicant meets the bank’s base rules (age 21-60, income >= 25000, etc.)
- Whether the requested loan amount is reasonable given the applicant’s profile and the bank’s products

Respond ONLY in this JSON format:
{{
  "decision": "Yes"|"No"|"Needs Review",
  "reason": "...",
  "missing_fields": [...],
  "flagged": false,
  "flagged_reason": ""
}}

{few_shot}

Applicant Data:
- Extracted fields: {json.dumps(extracted_fields)}
- Documents: {json.dumps(doc_summaries)}
- Loan request: {json.dumps(loan_request)}
- Bank products: {json.dumps(bank_products)}
"""
    return prompt

@app.post("/check-eligibility", response_model=EligibilityDecision)
def check_eligibility(req: EligibilityRequest):
    try:
        query = f"SELECT * FROM c WHERE c.applicant_id = '{req.applicant_id}'"
        docs = list(container.query_items(query=query, enable_cross_partition_query=True))
        if not docs:
            raise HTTPException(status_code=404, detail="Applicant not found")
        prompt = build_gpt_prompt(req.applicant_id, docs)
        result = call_gpt_eligibility(prompt)
        return EligibilityDecision(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 