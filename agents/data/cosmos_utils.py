from azure.cosmos import CosmosClient
import os
from dotenv import load_dotenv
load_dotenv()

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB_NAME = os.getenv("COSMOS_DB", "LoanApplicationDB")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER", "DocumentMetadata")

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
container = client.get_database_client(COSMOS_DB_NAME).get_container_client(COSMOS_CONTAINER_NAME)

async def get_fields_for_doc(applicant_id: str, doc_type: str):
    query = (
        "SELECT * FROM c WHERE c.applicant_id = @applicant_id AND c.predicted_classification = @doc_type"
    )
    params = [
        {"name": "@applicant_id", "value": applicant_id},
        {"name": "@doc_type", "value": doc_type},
    ]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    if items:
        # Return the first matching document's fields (customize as needed)
        return items[0].get("fields", items[0])
    else:
        return {}

def store_eligibility_result(applicant_id: str, report_json: dict):
    # Store the eligibility result as a new document in Cosmos DB
    item = {
        "id": f"{applicant_id}_eligibility_result",
        "applicant_id": applicant_id,
        "type": "eligibility_result",
        "report": report_json
    }
    container.upsert_item(item)
    return item

def all_required_docs_present(applicant_id: str) -> bool:
    required_types = [
        'PAN Card',
        'Passport',
        'Bank Statement',
        'Income Tax Return',
        'Credit Report'
    ]
    found_types = set()
    query = "SELECT c.predicted_classification FROM c WHERE c.applicant_id = @applicant_id"
    params = [
        {"name": "@applicant_id", "value": applicant_id}
    ]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    for item in items:
        doc_type = item.get("predicted_classification")
        if doc_type in required_types:
            found_types.add(doc_type)
    return all(t in found_types for t in required_types)

def get_applicant_contact_info(applicant_id: str):
    query = "SELECT * FROM c WHERE c.applicant_id = @applicant_id"
    params = [{"name": "@applicant_id", "value": applicant_id}]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    for doc in items:
        loan_app = doc.get("loan_application")
        if loan_app:
            # 1. In loan_application['fields']
            fields = loan_app.get("fields", {})
            name = fields.get("ApplicantName")
            email = loan_app.get("email")
            if name or email:
                return name, email
            # 2. Directly in loan_application
            name = loan_app.get("ApplicantName")
            if name or email:
                return name, email
        # 3. Top-level fields
        name = doc.get("ApplicantName")
        email = doc.get("email")
        if name or email:
            return name, email
    return None, None

def get_all_applicant_ids():
    """
    Fetch all unique applicant_id values from the Cosmos DB container.
    Returns:
        List of applicant_id strings.
    """
    query = "SELECT DISTINCT c.applicant_id FROM c WHERE IS_DEFINED(c.applicant_id)"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    # Each item is a dict like {"applicant_id": "..."}
    return [item["applicant_id"] for item in items if "applicant_id" in item]

def get_all_eligibility_results():
    """
    Fetch all eligibility result documents from the Cosmos DB container.
    Returns:
        List of eligibility result documents (dicts).
    """
    query = "SELECT * FROM c WHERE c.type = @type"
    params = [{"name": "@type", "value": "eligibility_result"}]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    return items

def mark_eligibility_email_sent(applicant_id: str):
    """
    Set email_sent: true in the eligibility result document for the given applicant_id.
    """
    # Find the eligibility result document
    query = "SELECT * FROM c WHERE c.applicant_id = @applicant_id AND c.type = @type"
    params = [
        {"name": "@applicant_id", "value": applicant_id},
        {"name": "@type", "value": "eligibility_result"}
    ]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    if not items:
        print(f"[ERROR] No eligibility result found for applicant_id: {applicant_id}")
        return False
    doc = items[0]
    doc["email_sent"] = True
    # Remove system fields
    for key in ["_rid", "_self", "_etag", "_attachments", "_ts"]:
        doc.pop(key, None)
    try:
        container.replace_item(item=doc["id"], body=doc, partition_key=doc["applicant_id"])
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update eligibility result for applicant_id: {applicant_id}: {e}")
        return False

def mark_submission_email_sent(applicant_id: str):
    """
    Set submission_email_sent: true in the applicant's main document (with loan_application) for the given applicant_id.
    """
    # Find the main applicant document
    query = "SELECT * FROM c WHERE c.applicant_id = @applicant_id AND IS_DEFINED(c.loan_application)"
    params = [
        {"name": "@applicant_id", "value": applicant_id}
    ]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    if not items:
        print(f"[ERROR] No document found for applicant_id: {applicant_id}")
        return False
    doc = items[0]
    doc["submission_email_sent"] = True
    # Remove system fields
    for key in ["_rid", "_self", "_etag", "_attachments", "_ts"]:
        doc.pop(key, None)
    try:
        container.replace_item(item=doc["id"], body=doc, partition_key=doc["applicant_id"])
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update document for applicant_id: {applicant_id}: {e}")
        return False
    
def get_full_applicant_data(applicant_id: str):
    query = "SELECT * FROM c WHERE c.applicant_id = @applicant_id"
    params = [{"name": "@applicant_id", "value": applicant_id}]
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    applicant_data = {
        "applicant_id": applicant_id,
        "name": None,
        "email": None,
        "phone": None,
        "dob": None,
        "loan_amount": None,
        "tenure_months": None,
        "loan_purpose": None,
        "emi": None,
        "interest_rate": None,
        "credit_score": None,
        "income": None,
        "documents": []
    }

    for doc in items:
        # Loan application doc
        if doc.get("id", "").endswith("_loan_app"):
            loan_app = doc.get("loan_application", {})
            fields = loan_app.get("fields", {})
            applicant_data["name"] = fields.get("ApplicantName") or fields.get("FirstName")
            applicant_data["email"] = loan_app.get("email")
            applicant_data["phone"] = fields.get("Phone")
            applicant_data["dob"] = fields.get("DateOfBirth")
            applicant_data["loan_amount"] = loan_app.get("loan_amount")
            applicant_data["tenure_months"] = loan_app.get("tenure_months")
            applicant_data["loan_purpose"] = loan_app.get("loan_purpose")
            applicant_data["emi"] = loan_app.get("emi")
            applicant_data["interest_rate"] = loan_app.get("interest_rate")
            applicant_data["credit_score"] = fields.get("CreditScore")
            applicant_data["income"] = fields.get("GrossIncome")
        # Document record
        elif doc.get("predicted_classification"):
            doc_info = {
                "type": doc.get("predicted_classification"),
                "blob_url": doc.get("blob_url"),
                "file_name": doc.get("file_name"),
                "status": doc.get("status"),
                "extracted_fields": doc.get("extracted_fields", {}),
                "is_complete": doc.get("is_complete", False),
                "missing_fields": doc.get("missing_fields", []),
                "flagged_by_ai": doc.get("flagged_by_ai", False),
                "flagged_reason": doc.get("flagged_reason", ""),
            }
            applicant_data["documents"].append(doc_info)
    return applicant_data if items else None
    