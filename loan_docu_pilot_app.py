import os
import uuid
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import streamlit as st
from PyPDF2 import PdfReader
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from classification import classify_document

# Load environment variables
load_dotenv()
BLOB_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
FORM_RECOGNIZER_KEY = os.getenv("FORM_RECOGNIZER_KEY")
FORM_RECOGNIZER_ENDPOINT = os.getenv("FORM_RECOGNIZER_ENDPOINT")

# Azure Clients Initialization
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
form_recognizer = DocumentAnalysisClient(
    endpoint=FORM_RECOGNIZER_ENDPOINT,
    credential=AzureKeyCredential(FORM_RECOGNIZER_KEY)
)
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.create_database_if_not_exists(id="LoanApplicationDB")
container = database.create_container_if_not_exists(
    id="DocumentMetadata",
    partition_key=PartitionKey(path="/applicant_id"),
    offer_throughput=400
)

# Streamlit UI setup
st.set_page_config(page_title="📄 Personal Loan DocuPilot", layout="centered")
st.title("📄 Personal Loan Application DocuPilot")

if "applicant_id" not in st.session_state:
    st.session_state["applicant_id"] = str(uuid.uuid4())[:8]
applicant_id = st.session_state["applicant_id"]
st.markdown(f"**Your Application ID:** `{applicant_id}`")

categories = {
    "KYC": ["Aadhaar Card", "PAN Card", "Address Proof"],
    "Income Proof": ["Salary Slip", "Form 16", "ITR"],
    "Banking": ["Bank Statement", "Cancelled Cheque"],
    "Employment": ["Offer Letter", "Employee ID"],
    "Loan Forms": ["Loan Application Form", "Consent Form", "FATCA"],
    "Optional": ["Co-Applicant ID", "Insurance"]
}

st.subheader("📤 Upload Your Documents")
uploaded_files = {}
for group, docs in categories.items():
    st.markdown(f"### 📁 {group}")
    for doc in docs:
        file = st.file_uploader(f"{doc}:", type=["pdf", "jpg", "jpeg", "png"], key=f"{group}_{doc}")
        if file:
            uploaded_files[f"{group}-{doc}"] = file

st.markdown("---")
if uploaded_files:
    st.success(f"{len(uploaded_files)} documents ready to upload.")
else:
    st.info("No documents uploaded yet.")

if st.checkbox("✅ I confirm my uploads are correct."):
    if st.button("🚀 Submit"):
        container_name = f"applicant-{applicant_id}".lower()
        try:
            blob_service_client.create_container(container_name)
        except:
            pass

        for label, file_obj in uploaded_files.items():
            doc_type = label.split("-")[1]
            blob_path = f"{applicant_id}/{doc_type}/{file_obj.name}"
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
            blob_client.upload_blob(file_obj, overwrite=True)

            file_obj.seek(0)
            text = ""
            try:
                poller = form_recognizer.begin_analyze_document("prebuilt-document", file_obj)
                result = poller.result()
                lines = [line.content for page in result.pages for line in page.lines]
                text = "\n".join(lines)
            except Exception as e:
                text = f"[OCR failed: {e}]"

            st.code(text[:500])

            try:
                classification = classify_document(text)
            except Exception as e:
                st.error(f"❌ Error in classification: {e}")
                classification = {
                    "document_type": "Others",
                    "reason": f"Classification failed: {str(e)}"
                }

            metadata = {
                "id": str(uuid.uuid4()),
                "applicant_id": applicant_id,
                "blob_url": blob_client.url,
                "original_label": label,
                "predicted_classification": classification["document_type"],
                "reasoning": classification["reason"],
                "upload_time": datetime.now(timezone.utc).isoformat(),
                "blob_path": blob_path,
                "file_name": file_obj.name
            }
            container.upsert_item(metadata)

        st.success("✅ Documents uploaded and classified successfully!")
        st.balloons()
else:
    st.warning("Please confirm uploads before submitting.")
