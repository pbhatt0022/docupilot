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