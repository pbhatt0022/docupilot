import os
import uuid
import json
import datetime
from dotenv import load_dotenv
import streamlit as st
from PyPDF2 import PdfReader
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from classification import classify_document
from azure_extraction import extract_text_from_blob_url, extract_fields_with_model
import tempfile
import os

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
    "KYC Documents": [
        ("Aadhaar Card", "Government-issued unique identity card"),
        ("PAN Card", "Permanent Account Number for tax purposes"),
        ("Passport", "Valid Indian passport (as address or identity proof)"),
        ("VoterID", "Voter ID card (as address or identity proof)"),
        ("Driving License", "Valid driving license (as address or identity proof)")
    ],
    "Income Proof": [
        ("Salary Slip", "Last 3–6 months' salary slips"),
        ("Form 16", "Annual Form 16 from employer"),
        ("Income Tax Return", "Last 1–3 years' ITR documents"),
        ("Bank Statement", "Salary or main account statement for last 3–6 months")
    ],
    "Employment Verification": [
        ("Offer Letter", "For new employees joining the company"),
        ("Employment Certificate", "Certificate of employment from employer"),
        ("Employee ID", "Official employee ID card"),
        ("Increment Letter", "Latest increment letter"),
        ("Appraisal Letter", "Latest appraisal letter")
    ],
    "Banking and Loan-Related": [
        ("Cancelled Cheque", "For ECS mandate"),
        ("Loan Application Form", "With applicant declaration and loan details"),
        ("Consent Form", "For CIBIL check and data access"),
        ("FATCA Declaration", "For NRIs or regulatory compliance")
    ],
    "Other Supporting Documents": [
        ("Proof of Residence", "E.g., electricity bill, rent agreement, etc."),
        ("Photograph", "Passport-size photograph"),
        ("Co-Applicant Document", "Same as above, if applicable")
    ],
    "Optional": [
        ("Credit Report", "CIBIL or Experian report"),
        ("Insurance Proof", "If bundled with loan"),
        ("Digital Consent", "For eKYC"),
        ("Video KYC", "Geo-tagged selfie or video KYC")
    ]
}

st.subheader("📤 Upload Your Documents")
uploaded_files = {}
for group, docs in categories.items():
    st.markdown(f"### 📁 {group}")
    for doc, help_text in docs:
        file = st.file_uploader(f"{doc}:", type=["pdf", "jpg", "jpeg", "png"], key=f"{group}_{doc}", help=help_text)
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

            # Use system temp directory for saving the file
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, file_obj.name)
            with open(temp_path, "wb") as temp_file:
                temp_file.write(file_obj.getbuffer())

            # Extract structured fields and check completeness
            try:
                extracted_fields, is_complete, missing_fields, flagged_by_ai, flagged_reason, raw_extracted = extract_fields_with_model(temp_path, classification["document_type"])
            except Exception as e:
                print(f"Extraction failed for {file_obj.name} ({classification['document_type']}): {e}")
                extracted_fields = {}
                is_complete = False
                missing_fields = []
                flagged_by_ai = True
                flagged_reason = f"Extraction failed: {str(e)}"
                raw_extracted = {}

            def serialize_dates_in_dict(d):
                for k, v in d.items():
                    if isinstance(v, (datetime.date, datetime.datetime)):
                        d[k] = v.isoformat()
                return d

            # Convert all date/datetime objects in extracted_fields and raw_extracted to strings
            extracted_fields = serialize_dates_in_dict(extracted_fields)
            raw_extracted = serialize_dates_in_dict(raw_extracted)

            metadata = {
                "id": str(uuid.uuid4()),
                "applicant_id": applicant_id,
                "blob_url": blob_client.url,
                "original_label": label,
                "predicted_classification": classification["document_type"],
                "reasoning": classification["reason"],
                "upload_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "blob_path": blob_path,
                "file_name": file_obj.name,
                "status": "incomplete" if not is_complete else "pending_review",
                "officer_comments": "",            
                "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "reviewed_by": "officer_001",          
                "flagged_by_ai": flagged_by_ai,
                "flagged_reason": flagged_reason,
                "extracted_fields": extracted_fields,
                "is_complete": is_complete,
                "missing_fields": missing_fields,
                "raw_extracted_fields": raw_extracted
            }
            container.upsert_item(metadata)

        st.success("✅ Documents uploaded, classified, and extracted successfully!")
        st.balloons()
else:
    st.warning("Please confirm uploads before submitting.")
