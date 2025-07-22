from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("SEARCH_API_KEY")
AZURE_SEARCH_INDEX = os.getenv("SEARCH_INDEX", "rag-2")

app = FastAPI()

class VerificationRequest(BaseModel):
    document_id: str
    query: str

class ApplicantAnalysisRequest(BaseModel):
    applicant_id: str
    query: str = ""

# Initialize the Azure Search client
search_client = None
if AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY:
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX,
        credential=AzureKeyCredential(AZURE_SEARCH_KEY)
    )

def run_verification_logic(document_id: str, query: str) -> Dict[str, Any]:
    if not search_client:
        return {"status": "error", "message": "Azure Search client not configured."}
    filter_expr = f"filename eq '{document_id}'"
    results = list(search_client.search(query, filter=filter_expr, top=3))
    if not results:
        return {"status": "not_found", "message": f"No results found for document {document_id}."}
    top_chunk = results[0].get("chunk", "No chunk found.")
    # Example: Add a dummy issue flag for demonstration
    issues = []
    if "signature missing" in top_chunk.lower():
        issues.append("Signature missing")
    return {
        "status": "success",
        "document_id": document_id,
        "query": query,
        "top_chunk": top_chunk,
        "num_results": len(results),
        "issues": issues
    }

def analyze_applicant_documents(applicant_id: str, query: str = "") -> Dict[str, Any]:
    if not search_client:
        return {"status": "error", "message": "Azure Search client not configured."}
    # Fetch all documents for the applicant
    filter_expr = f"applicant_id eq '{applicant_id}'"
    docs = list(search_client.search("*", filter=filter_expr, top=100))
    if not docs:
        return {"status": "not_found", "message": f"No documents found for applicant {applicant_id}."}
    breakdown = []
    num_verified = 0
    num_flagged = 0
    for doc in docs:
        doc_id = doc.get("filename") or doc.get("id")
        doc_name = doc.get("filename", "Unknown Document")
        # Run verification logic for each document
        result = run_verification_logic(doc_id, query)
        status_icon = "✅" if not result.get("issues") else "⚠️"
        if result.get("status") == "success" and not result.get("issues"):
            num_verified += 1
        if result.get("issues"):
            num_flagged += 1
        breakdown.append({
            "document": doc_name,
            "status": result.get("status"),
            "icon": status_icon,
            "issues": result.get("issues"),
            "summary": result.get("top_chunk", "No summary available.")
        })
    # Structured summary
    lines = [
        f"Document Verification Summary for Applicant: {applicant_id}",
        f"- Total Documents: {len(docs)}",
        f"- Verified: {num_verified}",
        f"- Flagged: {num_flagged}",
        "",
        "Breakdown:"
    ]
    for b in breakdown:
        issue_str = f" Issues: {', '.join(b['issues'])}" if b["issues"] else ""
        lines.append(f"• {b['document']}: {b['icon']} {b['status'].capitalize()}.{issue_str}")
    lines.append("")
    if num_flagged == 0:
        lines.append("All documents verified. No issues found.")
    else:
        lines.append(f"{num_flagged} document(s) flagged for issues. Please review.")
    summary = "\n".join(lines)
    return {
        "status": "success",
        "applicant_id": applicant_id,
        "breakdown": breakdown,
        "summary": summary,
        "num_verified": num_verified,
        "num_flagged": num_flagged,
        "total_documents": len(docs)
    }

@app.post("/verify")
def verify_document(req: VerificationRequest) -> Dict[str, Any]:
    result = run_verification_logic(req.document_id, req.query)
    return result

@app.post("/analyze-applicant")
def analyze_applicant(req: ApplicantAnalysisRequest) -> Dict[str, Any]:
    result = analyze_applicant_documents(req.applicant_id, req.query)
    return result

# To run: uvicorn agents.verification_agent.main:app --reload 