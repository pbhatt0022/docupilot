import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from azure.cosmos import CosmosClient

REQUIRED_DOCS = ["PAN Card", "Income Tax Return", "Bank Statement", "Credit Report", "Passport"]

class VerificationRequest(BaseModel):
    applicant_id: str

class VerificationResponse(BaseModel):
    all_documents_present: bool
    missing_documents: List[str]
    message: str

app = FastAPI(title="Verification Agent (Stand-In)")

# Cosmos DB setup
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DB_NAME = os.getenv("COSMOS_DB", "LoanApplicationDB")
CONTAINER_NAME = os.getenv("COSMOS_CONTAINER", "DocumentMetadata")
client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
container = client.get_database_client(DB_NAME).get_container_client(CONTAINER_NAME)

@app.post("/verify-documents", response_model=VerificationResponse)
def verify_documents(req: VerificationRequest):
    try:
        query = f"SELECT * FROM c WHERE c.applicant_id = '{req.applicant_id}'"
        docs = list(container.query_items(query=query, enable_cross_partition_query=True))
        uploaded_docs = {doc.get("predicted_classification", "") for doc in docs}
        missing = [doc for doc in REQUIRED_DOCS if doc not in uploaded_docs]
        all_present = len(missing) == 0
        return VerificationResponse(
            all_documents_present=all_present,
            missing_documents=missing,
            message="All required documents are present." if all_present else f"Missing: {', '.join(missing)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 