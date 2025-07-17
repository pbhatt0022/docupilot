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
from streamlit_lottie import st_lottie
import re

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

# Use a single shared container for all applicants
BLOB_CONTAINER_NAME = "loan-documents"
# Ensure the container exists (create once)
try:
    blob_service_client.create_container(BLOB_CONTAINER_NAME)
except Exception:
    pass

# Load the Lottie animation from the local file
with open("Search  Processing.json", "r") as f:
    lottie_json = json.load(f)

# Load validation data for loan application
with open("loan_validation.json", "r") as f:
    validation_data = json.load(f)

# Initialize session state variables
if "processing" not in st.session_state:
    st.session_state["processing"] = False
if "extraction_results" not in st.session_state:
    st.session_state["extraction_results"] = []
# Ensure applicant_id is always set
if "applicant_id" not in st.session_state:
    st.session_state["applicant_id"] = str(uuid.uuid4())[:8]
applicant_id = st.session_state["applicant_id"]

# Streamlit UI setup
st.set_page_config(page_title="DocuPilot: Loan Preapproval Portal", layout="centered")

# --- Streamlit Sidebar Tabs ---
page = st.sidebar.radio("Navigation", ["Upload Documents", "Loan Application"])

if page == "Upload Documents":
    st.title("DocuPilot: Loan Preapproval Portal")

    st.markdown(f"**Your Application ID:** `{applicant_id}`")

    # --- UI for Required Documents ---
    REQUIRED_DOCS = [
        ("PAN Card", "Permanent Account Number for tax purposes"),
        ("Passport", "Valid Indian passport (as address or identity proof)"),
        ("Bank Statement", "Salary or main account statement for last 3–6 months"),
        ("Income Tax Return", "Last 1–3 years' ITR documents"),
        ("Credit Report", "CIBIL or Experian report")
    ]

    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 1.5em; border-radius: 10px; margin-bottom: 1em;'>
        <h4 style='color: #2c3e50;'>Required Documents</h4>
        <ul style='color: #34495e;'>
            <li><b>PAN Card</b>: Permanent Account Number for tax purposes</li>
            <li><b>Passport</b>: Valid Indian passport (as address or identity proof)</li>
            <li><b>Bank Statement</b>: Salary or main account statement for last 3–6 months</li>
            <li><b>Income Tax Return</b>: Last 1–3 years' ITR documents</li>
            <li><b>Credit Report</b>: CIBIL or Experian report</li>
        </ul>
        <span style='color: #888;'>You can drag and drop all 5 files below. Supported formats: PDF, JPG, JPEG, PNG.</span>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Drag and drop your 5 required documents here:",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="Upload PAN Card, Passport, Bank Statement, Income Tax Return, and Credit Report."
    )

    # --- Show loaded documents ---
    if uploaded_files:
        st.success(f"{len(uploaded_files)} document(s) loaded:")
        for file in uploaded_files:
            st.markdown(f"- <b>{file.name}</b>", unsafe_allow_html=True)
    else:
        st.info("No documents uploaded yet. Please upload all 5 required documents.")

    # --- Submit button triggers processing state ---
    if uploaded_files and st.button("🚀 Submit & Extract"):
        st.session_state["processing"] = True
        st.session_state["extraction_results"] = []

    # --- Processing block ---
    if st.session_state["processing"]:
        st_lottie(lottie_json, height=220, key="processing_overlay")
        st.markdown(
            "<div style='font-size:1.5em; color:#2c3e50; margin-top:1.5em; font-weight:600;'>Processing your documents...</div>",
            unsafe_allow_html=True,
        )
        extraction_results = []
        for file_obj in uploaded_files:
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, file_obj.name)
            file_obj.seek(0)
            with open(temp_path, "wb") as temp_file:
                temp_file.write(file_obj.getbuffer())
            file_obj.seek(0)
            # Use new blob path format: applicant_id/document_type/filename
            document_type = classification["document_type"]
            blob_path = f"{applicant_id}/{document_type}/{file_obj.name}"
            blob_client = blob_service_client.get_blob_client(container=BLOB_CONTAINER_NAME, blob=blob_path)
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
            try:
                classification = classify_document(text)
            except Exception as e:
                st.error(f"❌ Error in classification: {e}")
                classification = {
                    "document_type": "Others",
                    "reason": f"Classification failed: {str(e)}"
                }
            try:
                extracted_fields, is_complete, missing_fields, flagged_by_ai, flagged_reason, raw_extracted = extract_fields_with_model(temp_path, classification["document_type"])
            except Exception as e:
                st.error(f"❌ Extraction failed for {file_obj.name} ({classification['document_type']}): {e}")
                extracted_fields = {}
                is_complete = False
                missing_fields = []
                flagged_by_ai = True
                flagged_reason = f"Extraction failed: {str(e)}"
                raw_extracted = {}
            metadata = {
                "id": str(uuid.uuid4()),
                "applicant_id": applicant_id,
                "blob_url": blob_client.url,
                "original_label": file_obj.name,
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
            extraction_results.append({
                "file_name": file_obj.name,
                "classification": classification["document_type"],
                "reason": classification["reason"],
                "extracted_text": text,
                "extracted_fields": extracted_fields,
                "raw_extracted": raw_extracted
            })
        st.session_state["extraction_results"] = extraction_results
        st.session_state["processing"] = False
        st.balloons()
        st.success("✅ All documents processed and extracted!")

    # --- Always show results if available ---
    extraction_results = st.session_state.get("extraction_results", [])
    if extraction_results:
        st.markdown("---")
        st.header("📝 Extraction Results")
        for result in extraction_results:
            st.subheader(f"📄 {result['file_name']} ({result['classification']})")
            st.markdown(f"<i>{result['reason']}</i>", unsafe_allow_html=True)
            with st.expander("Show Extracted Text", expanded=False):
                st.code(result["extracted_text"][:2000] + ("..." if len(result["extracted_text"]) > 2000 else ""))
            with st.expander("Show Final Extracted Fields", expanded=True):
                if result["extracted_fields"]:
                    st.table(list(result["extracted_fields"].items()))
                else:
                    st.warning("No extracted fields found.")
            with st.expander("Show Raw Extracted Fields (from Azure)", expanded=False):
                if result["raw_extracted"]:
                    st.table(list(result["raw_extracted"].items()))
                else:
                    st.info("No raw extracted fields available.")

    # After balloons, prompt user to move to next tab
    if st.session_state.get("extraction_results"):
        st.info("Extraction complete! Please proceed to the 'Loan Application' tab to review and submit your application.")

elif page == "Loan Application":
    st.header("Loan Application")
    extraction_results = st.session_state.get("extraction_results", [])
    # Aggregate all extracted fields into a single dict
    extracted_data = {}
    for result in extraction_results:
        extracted_data.update(result.get("extracted_fields", {}))
    # Editable fill-in-the-blanks form
    with st.form("loan_app_form"):
        st.subheader("Review and Edit Your Details")
        edited_fields = {}
        for key, value in extracted_data.items():
            edited_fields[key] = st.text_input(key, value)
        st.subheader("Loan Details")
        min_amt = validation_data["min_loan_amount"]
        max_amt = validation_data["max_loan_amount"]
        min_tenure = validation_data["min_tenure_months"]
        max_tenure = validation_data["max_tenure_months"]
        interest_rate = validation_data["interest_rate"]
        loan_purposes = validation_data["loan_purposes"]
        loan_amount = st.number_input("Loan Amount", min_value=min_amt, max_value=max_amt, value=min_amt, step=10000)
        tenure = st.number_input("Tenure (months)", min_value=min_tenure, max_value=max_tenure, value=min_tenure, step=1)
        purpose_options = loan_purposes
        loan_purpose = st.selectbox("Loan Purpose", purpose_options)
        if loan_purpose == "Other":
            loan_purpose = st.text_input("Please specify loan purpose")
        # Prompt for email (required)
        email = st.text_input("Email Address for Updates", value="", help="We'll send you updates about your application.")
        email = email.strip()
        # Validation flags and messages
        validation_errors = []
        # Improved email validation regex
        email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        # Calculate EMI and validation BEFORE the submit button
        P = loan_amount
        R = interest_rate / 12 / 100
        N = tenure
        emi = None
        if P and R and N and not validation_errors:
            try:
                emi = (P * R * (1 + R) ** N) / ((1 + R) ** N - 1)
            except Exception:
                emi = None

        # Show errors/info
        if validation_errors:
            for err in validation_errors:
                st.error(err)
        if emi:
            st.success(f"Calculated EMI: ₹{emi:,.2f} at {interest_rate}% p.a.")
        elif not validation_errors:
            st.info(f"Enter valid loan amount and tenure to calculate EMI. Allowed loan: ₹{min_amt:,}–₹{max_amt:,}, tenure: {min_tenure}–{max_tenure} months.")

        # Now create the submit button
        submitted = st.form_submit_button("Submit Loan Application", disabled=emi is None or bool(validation_errors))

        if submitted and emi and not validation_errors:
            # Prepare final dictionary
            final_dict = {
                "id": f"{applicant_id}_loan_app",
                "applicant_id": applicant_id,
                "loan_application": {
                    "fields": edited_fields,
                    "loan_amount": loan_amount,
                    "tenure_months": tenure,
                    "loan_purpose": loan_purpose,
                    "emi": emi,
                    "interest_rate": interest_rate,
                    "email": email,
                    "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            }
            container.upsert_item(final_dict)
            st.balloons()
            st.success("🎉 Loan application submitted successfully!")
