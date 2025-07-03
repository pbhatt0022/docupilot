import streamlit as st
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Azure Blob Setup ---
blob_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
blob_container_name = "raw-documents"

# --- Azure Cosmos DB Setup ---
cosmos_url = os.getenv("COSMOS_ENDPOINT")
cosmos_key = os.getenv("COSMOS_KEY")
cosmos_db_name = "LoanApplicationsDB"
cosmos_container_name = "DocumentMetadata"

cosmos_client = CosmosClient(cosmos_url, credential=cosmos_key)
cosmos_db = cosmos_client.create_database_if_not_exists(id=cosmos_db_name)
cosmos_container = cosmos_db.create_container_if_not_exists(
    id=cosmos_container_name,
    partition_key=PartitionKey(path="/applicant_id"),
    offer_throughput=400
)

# --- Streamlit App ---
st.set_page_config(page_title="Loan Doc Upload", layout="centered")
st.title("📄 Personal Loan Document Uploader")

if "applicant_id" not in st.session_state:
    st.session_state["applicant_id"] = str(uuid.uuid4())[:8]

applicant_id = st.session_state["applicant_id"]
st.markdown(f"**Your Application ID**: `{applicant_id}`")

# Document categories
categories = {
    "KYC": ["Aadhaar Card", "PAN Card", "Address Proof"],
    "Income": ["Salary Slips", "Form 16", "ITR"],
    "Banking": ["Bank Statements", "Cancelled Cheque"],
    "Employment": ["Offer Letter", "Employee ID Card"],
    "Loan Forms": ["Loan Application", "Consent Form", "Sanction Letter"]
}

uploaded_summary = {}

st.subheader("📤 Upload Documents")

for cat, docs in categories.items():
    st.markdown(f"### 📁 {cat}")
    for doc_type in docs:
        file = st.file_uploader(f"{doc_type}", type=["pdf", "jpg", "jpeg", "png"], key=f"{cat}-{doc_type}")
        if file:
            folder_path = f"applicant-{applicant_id}/{cat}/{file.name}"
            blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=folder_path)
            blob_client.upload_blob(file, overwrite=True)

            blob_url = blob_client.url
            cosmos_container.upsert_item({
                "id": str(uuid.uuid4()),
                "applicant_id": applicant_id,
                "document_type": doc_type,
                "category": cat,
                "filename": file.name,
                "upload_time": datetime.utcnow().isoformat(),
                "blob_url": blob_url,
                "status": "Uploaded"
            })
            uploaded_summary[f"{cat} - {doc_type}"] = file.name

st.markdown("---")
st.subheader("📋 Upload Summary")
if uploaded_summary:
    for k, v in uploaded_summary.items():
        st.success(f"✅ {k}: `{v}`")
else:
    st.info("No documents uploaded yet.")

if st.checkbox("✅ I confirm all uploads are complete."):
    if st.button("🚀 Submit Application"):
        st.success("Submitted! Your application has been received.")
        st.balloons()
