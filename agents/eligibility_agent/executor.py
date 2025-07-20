### agents/eligibility/executor.py
from agents.tools.mcp_client import callMCPTool
from .scoring import score_eligibility
from agents.data.cosmos_utils import store_eligibility_result

async def run_eligibility_pipeline(applicant_id: str):
    # Step 1: Retrieve structured fields using MCP tools
    passport_pan = await callMCPTool("parse_passport_pan", {"applicant_id": applicant_id})
    credit_report = await callMCPTool("parse_credit_report", {"applicant_id": applicant_id})
    itr_data = await callMCPTool("parse_itr_fields", {"applicant_id": applicant_id})
    bank_data = await callMCPTool("parse_bank_statements", {"applicant_id": applicant_id})

    # Step 2: Score eligibility
    result = score_eligibility(
        income=itr_data["annual_income"],
        credit_score=credit_report["credit_score"],
        emi_pct=credit_report["emi_burden_pct"],
        avg_balance=bank_data["average_balance"],
        overdrafts=bank_data["overdraft_instances"],
        itr_years=itr_data["consistency_years"]
    )

    # Step 3: Store to blob
    report_json = {
        "decision": result["decision"],
        "confidence_score": result["confidence_score"],
        "summary": generate_summary(result),
        "criteria": result["criteria"]
    }

    blob_url = await callMCPTool("upload_blob", {
        "container_name": "eligibility-reports",
        "file_name": f"{applicant_id}-eligibility.json",
        "content": report_json
    })

    # Store result in Cosmos DB
    store_eligibility_result(applicant_id, report_json)

    return {
        "decision": result["decision"],
        "score": result["confidence_score"],
        "report_url": blob_url
    }


def generate_summary(result):
    decision = result["decision"]
    cs = result["confidence_score"]
    phrases = [c["comments"] for c in result["criteria"]]
    summary = ". ".join(phrases) + "."
    return f"{decision} candidate (score {cs}/10). {summary}"
