import os
import uuid
import json
import datetime
from dotenv import load_dotenv
import streamlit as st
from PyPDF2 import PdfReader # This import is not used in the provided code, can be removed if not needed elsewhere.
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
lottie_processing_json = None
try:
    with open("Search  Processing.json", "r") as f:
        lottie_processing_json = json.load(f)
except Exception:
    pass

lottie_success_json = None
try:
    # Assuming you have a success animation JSON, replace with actual path
    # For demonstration, I'll use a placeholder or you can provide one.
    # If not available, this will gracefully fail.
    with open("success_animation.json", "r") as f: # Placeholder, replace with your actual success Lottie JSON
        lottie_success_json = json.load(f)
except Exception:
    pass


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
st.set_page_config(
    page_title="DocuPilot: Loan Preapproval Portal",
    layout="wide", # Changed to wide for better layout control
    initial_sidebar_state="collapsed"
)

# --- Microsoft-style CSS with comprehensive styling ---
st.markdown(
    """
    <style>
    /* Global Styles */
    .stApp {
        background-color: #f8f9fa; /* Light gray background */
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', 'Helvetica Neue', sans-serif;
        color: #323130; /* Dark gray text */
    }
    
    .block-container {
        padding: 1.5rem 2rem 2rem 2rem;
        max-width: 1200px;
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #0078D4 0%, #106ebe 100%); /* Microsoft Blue gradient */
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 120, 212, 0.15);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 600;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Sidebar Navigation */
    .stSidebar [data-testid="stSidebarNav"] {
        background-color: #ffffff;
        border-right: 1px solid #e1dfdd;
        padding-top: 2rem;
    }
    
    .stSidebar [data-testid="stSidebarNav"] ul {
        list-style: none;
        padding: 0;
    }
    
    .stSidebar [data-testid="stSidebarNav"] li {
        margin-bottom: 0.5rem;
    }
    
    .stSidebar [data-testid="stSidebarNav"] a {
        display: flex;
        align-items: center;
        padding: 0.75rem 1.5rem;
        color: #605e5c;
        text-decoration: none;
        font-weight: 500;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    
    .stSidebar [data-testid="stSidebarNav"] a:hover {
        background-color: #f3f2f1;
        color: #323130;
    }
    
    .stSidebar [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #e6f2fb; /* Light blue for active tab */
        color: #005a9e; /* Darker blue for active text */
        font-weight: 600;
    }
    
    /* Card Containers */
    .card-container {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border: 1px solid #e1dfdd;
        margin-bottom: 1.5rem;
    }
    
    /* Section Headers */
    .section-header {
        color: #323130;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e1dfdd;
    }
    
    /* Buttons */
    .stButton > button {
        background: #0078D4;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        padding: 0.75rem 1.5rem;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 120, 212, 0.2);
    }
    
    .stButton > button:hover {
        background: #106ebe;
        box-shadow: 0 4px 8px rgba(0, 120, 212, 0.3);
        transform: translateY(-1px);
    }
    
    .stButton > button:disabled {
        background: #a6a6a6;
        box-shadow: none;
        transform: none;
        cursor: not-allowed;
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: #0078D4;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        padding: 0.75rem 1.5rem;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 120, 212, 0.2);
    }
    
    .stDownloadButton > button:hover {
        background: #106ebe;
        box-shadow: 0 4px 8px rgba(0, 120, 212, 0.3);
        transform: translateY(-1px);
    }
    
    /* Form Controls */
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 1px solid #d2d0ce;
        transition: all 0.2s ease;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #0078D4;
        box-shadow: 0 0 0 2px rgba(0, 120, 212, 0.2);
    }
    
    .stTextInput > div > input {
        border-radius: 8px;
        border: 1px solid #d2d0ce;
        transition: all 0.2s ease;
    }
    
    .stTextInput > div > input:focus {
        border-color: #0078D4;
        box-shadow: 0 0 0 2px rgba(0, 120, 212, 0.2);
    }
    
    .stNumberInput > div > input {
        border-radius: 8px;
        border: 1px solid #d2d0ce;
        transition: all 0.2s ease;
    }
    
    .stNumberInput > div > input:focus {
        border-color: #0078D4;
        box-shadow: 0 0 0 2px rgba(0, 120, 212, 0.2);
    }
    
    .stTextArea > div > textarea {
        border-radius: 8px;
        border: 1px solid #d2d0ce;
        transition: all 0.2s ease;
    }
    
    .stTextArea > div > textarea:focus {
        border-color: #0078D4;
        box-shadow: 0 0 0 2px rgba(0, 120, 212, 0.2);
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid;
    }
    
    .stAlert.success {
        background: #dff6dd;
        border-left-color: #107c10;
        color: #107c10;
    }
    
    .stAlert.warning {
        background: #fff4ce;
        border-left-color: #ffb900;
        color: #8a6914;
    }
    
    .stAlert.error {
        background: #fde7e9;
        border-left-color: #d13438;
        color: #a80000;
    }
    
    .stAlert.info {
        background: #deecf9;
        border-left-color: #0078D4;
        color: #005a9e;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.75rem;
        font-weight: 500;
        color: #323130;
    }
    
    /* Lottie Animation Container */
    .lottie-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
        
        .main-header {
            padding: 1.5rem;
        }
        
        .main-header h1 {
            font-size: 2rem;
        }
        
        .card-container {
            padding: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Main header
st.markdown(
    """
    <div class="main-header">
        <h1>DocuPilot: Loan Preapproval Portal</h1>
        <p>Streamlined document processing and loan application for a seamless experience</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Streamlit Sidebar Tabs ---
page = st.sidebar.radio(
    "Navigation",
    ["Upload Documents", "Loan Application"],
    key="main_navigation"
)

# --- Helper function for metric cards (reused from previous refactor) ---
def create_metric_card(title, value, icon="📊"):
    """Create a styled metric card"""
    return f"""
    <div class="card-container" style="padding: 1rem; text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="color: #605e5c; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;">
            {title}
        </div>
        <div style="color: #0078D4; font-size: 1.8rem; font-weight: 700;">
            {value}
        </div>
    </div>
    """

if page == "Upload Documents":
    st.markdown('<div class="section-header">📄 Document Upload & Processing</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="card-container">
            <p style="font-size: 1.1em; font-weight: 500; color: #323130;">
                Your unique Application ID: <code style="background-color: #f3f2f1; padding: 0.2em 0.5em; border-radius: 4px; font-weight: bold;">{applicant_id}</code>
            </p>
            <p style="color: #605e5c;">Please keep this ID for tracking your application.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- UI for Required Documents ---
    REQUIRED_DOCS = [
        ("PAN Card", "Permanent Account Number for tax purposes", "💳"),
        ("Passport", "Valid Indian passport (as address or identity proof)", "🛂"),
        ("Bank Statement", "Salary or main account statement for last 3–6 months", "🏦"),
        ("Income Tax Return", "Last 1–3 years' ITR documents", "🧾"),
        ("Credit Report", "CIBIL or Experian report", "📈")
    ]

    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: #2c3e50; margin-bottom: 1rem;">Required Documents Checklist</h4>', unsafe_allow_html=True)
    
    cols = st.columns(len(REQUIRED_DOCS))
    for i, (doc_name, doc_desc, icon) in enumerate(REQUIRED_DOCS):
        with cols[i]:
            st.markdown(create_metric_card(doc_name, icon, ""), unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 0.85em; text-align: center; color: #605e5c;'>{doc_desc}</p>", unsafe_allow_html=True)
    
    st.markdown("""
        <p style='font-size: 0.9em; color: #605e5c; margin-top: 1.5rem;'>
            You can drag and drop all 5 files below. Supported formats: PDF, JPG, JPEG, PNG.
        </p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True) # End of Required Documents card

    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "📁 Upload your documents here:",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="Upload PAN Card, Passport, Bank Statement, Income Tax Return, and Credit Report."
    )

    # --- Show loaded documents ---
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} document(s) loaded:")
        for file in uploaded_files:
            st.markdown(f"- <b>{file.name}</b>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ No documents uploaded yet. Please upload all 5 required documents.")

    # --- Submit button triggers processing state ---
    if uploaded_files and st.button("🚀 Submit & Extract Documents", key="submit_extract_btn"):
        st.session_state["processing"] = True
        st.session_state["extraction_results"] = []
        st.toast("Starting document processing...", icon="🚀")

    st.markdown('</div>', unsafe_allow_html=True) # End of Upload Area card

    # --- Processing block ---
    if st.session_state["processing"]:
        st.markdown('<div class="card-container lottie-container">', unsafe_allow_html=True)
        if lottie_processing_json:
            st_lottie(lottie_processing_json, height=220, key="processing_overlay")
        st.markdown(
            "<div style='font-size:1.5em; color:#2c3e50; margin-top:1.5em; font-weight:600; text-align: center;'>Processing your documents...</div>",
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True) # End of Processing card

        extraction_results = []
        for file_obj in uploaded_files:
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, file_obj.name)
            file_obj.seek(0)
            with open(temp_path, "wb") as temp_file:
                temp_file.write(file_obj.getbuffer())
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
            document_type = classification["document_type"]
            # Use RAG blob path format: applicant_id/document_type/filename
            blob_path = f"{applicant_id}/{document_type}/{file_obj.name}"
            blob_client = blob_service_client.get_blob_client(container=BLOB_CONTAINER_NAME, blob=blob_path)
            file_obj.seek(0) # Reset file pointer before upload
            blob_client.upload_blob(file_obj, overwrite=True)
            
            try:
                extracted_fields, is_complete, missing_fields, flagged_by_ai, flagged_reason, raw_extracted = extract_fields_with_model(temp_path, classification["document_type"])
            except Exception as e:
                st.error(f"❌ Extraction failed for {file_obj.name} ({classification['document_type']}): {e}")
                extracted_fields = {}
                is_complete = False
                missing_fields = []
                flagged_by_ai = True
                flagged_reason = f"Extraction failed: {str(e)}"
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
                "raw_extracted_fields": {} # raw_extracted is no longer returned
            }
            container.upsert_item(metadata)
            extraction_results.append({
                "file_name": file_obj.name,
                "classification": classification["document_type"],
                "reason": classification["reason"],
                "extracted_text": text,
                "extracted_fields": extracted_fields,
                "raw_extracted": {}, # raw_extracted is no longer returned
                "flagged_by_ai": flagged_by_ai,
                "flagged_reason": flagged_reason,
                "missing_fields": missing_fields
            })
        st.session_state["extraction_results"] = extraction_results
        st.session_state["processing"] = False
        st.balloons()
        st.toast("All documents processed and extracted!", icon="🎉")
        if lottie_success_json:
            st.markdown('<div class="lottie-container">', unsafe_allow_html=True)
            st_lottie(lottie_success_json, height=150, key="success_animation_docs")
            st.markdown('</div>', unsafe_allow_html=True)


    # --- Always show results if available ---
    extraction_results = st.session_state.get("extraction_results", [])
    if extraction_results:
        st.markdown('<div class="section-header">📝 Document Extraction Results</div>', unsafe_allow_html=True)
        for result in extraction_results:
            st.markdown('<div class="card-container">', unsafe_allow_html=True)
            st.markdown(f"### 📄 {result['file_name']} <span style='font-size:0.8em; color:#605e5c;'>({result['classification']})</span>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-style: italic; color: #605e5c;'>{result['reason']}</p>", unsafe_allow_html=True)
            
            if result["flagged_by_ai"]:
                st.error(f"🚩 AI Flagged: {result['flagged_reason']}")
                if result["missing_fields"]:
                    st.markdown("**Missing Fields:**")
                    for field in result["missing_fields"]:
                        st.markdown(f"- {field}")
            else:
                st.success("✅ AI Verified: No issues found.")

            col1, col2 = st.columns(2)
            with col1:
                with st.expander("Show Final Extracted Fields", expanded=True):
                    if result["extracted_fields"]:
                        st.table(list(result["extracted_fields"].items()))
                    else:
                        st.warning("No extracted fields found.")
            with col2:
                with st.expander("Show Raw Extracted Fields (from Azure)", expanded=False):
                    if result["raw_extracted"]:
                        st.table(list(result["raw_extracted"].items()))
                    else:
                        st.info("No raw extracted fields available.")
            
            with st.expander("Show Extracted Text (for review)", expanded=False):
                st.code(result["extracted_text"][:2000] + ("..." if len(result["extracted_text"]) > 2000 else ""))
            
            st.markdown('</div>', unsafe_allow_html=True) # End of individual result card

    # After balloons, prompt user to move to next tab
    if st.session_state.get("extraction_results") and not st.session_state["processing"]:
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        st.info("🎉 Document processing complete! Please proceed to the 'Loan Application' tab to review and submit your application.")
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "Loan Application":
    st.markdown('<div class="section-header">📝 Loan Application Form</div>', unsafe_allow_html=True)
    
    extraction_results = st.session_state.get("extraction_results", [])
    # Aggregate all extracted fields into a single dict
    extracted_data = {}
    for result in extraction_results:
        extracted_data.update(result.get("extracted_fields", {}))
    
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    with st.form("loan_app_form", clear_on_submit=False):
        st.markdown('<h4>Review and Edit Your Details</h4>', unsafe_allow_html=True)
        edited_fields = {}
        
        # Arrange extracted fields in columns
        field_keys = list(extracted_data.keys())
        num_cols = 2 # You can adjust this based on how many fields you have
        cols = st.columns(num_cols)
        
        for i, key in enumerate(field_keys):
            with cols[i % num_cols]:
                edited_fields[key] = st.text_input(key, extracted_data[key], key=f"edited_field_{key}")
        
        st.markdown('<h4 style="margin-top: 1.5rem;">Loan Details</h4>', unsafe_allow_html=True)
        min_amt = validation_data["min_loan_amount"]
        max_amt = validation_data["max_loan_amount"]
        min_tenure = validation_data["min_tenure_months"]
        max_tenure = validation_data["max_tenure_months"]
        interest_rate = validation_data["interest_rate"]
        loan_purposes = validation_data["loan_purposes"]
        
        col_loan_amt, col_tenure = st.columns(2)
        with col_loan_amt:
            loan_amount = st.number_input(
                "Loan Amount (₹)",
                min_value=int(min_amt),
                max_value=int(max_amt),
                value=int(min_amt),
                step=10000,
                key="loan_amount_input"
            )
        with col_tenure:
            tenure = st.number_input("Tenure (months)", min_value=min_tenure, max_value=max_tenure, value=int(min_tenure), step=1, key="tenure_input")
        
        loan_purpose = st.selectbox("Loan Purpose", loan_purposes, key="loan_purpose_select")
        if loan_purpose == "Other":
            loan_purpose = st.text_input("Please specify loan purpose", key="other_purpose_input")
        
        # Move email input inside form and get its value properly
        email = st.text_input("Email Address for Updates", key="email_input_form", placeholder="Enter your email address")
        
        # Validate inputs
        validation_errors = []
        
        # Check email validation
        if not email or not email.strip():
            validation_errors.append("Email address is required.")
        elif "@" not in email or "." not in email.split("@")[-1]:
            validation_errors.append("Please enter a valid email address.")
        
        # Calculate EMI
        emi = None
        if loan_amount and tenure and interest_rate:
            try:
                P = loan_amount
                R = interest_rate / 12 / 100
                N = tenure
                emi = (P * R * (1 + R) ** N) / ((1 + R) ** N - 1)
            except Exception:
                emi = None
        
        # Show validation errors
        if validation_errors:
            for err in validation_errors:
                st.error(err)
        
        # Submit button
        submitted = st.form_submit_button("Submit Application", type="primary")
        
        # Handle form submission
        if submitted:
            # Re-validate on submission (in case of any edge cases)
            email_clean = email.strip() if email else ""
            
            if not email_clean:
                st.error("Email address is required.")
            elif "@" not in email_clean or "." not in email_clean.split("@")[-1]:
                st.error("Please enter a valid email address.")
            else:
                # Proceed with submission
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
                        "email": email_clean,
                        "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "status": "under review" # Initial status for loan application
                    }
                }
                
                try:
                    container.upsert_item(final_dict)
                    st.balloons()
                    st.toast("Loan application submitted successfully!", icon="🎉")
                    if lottie_success_json:
                        st.markdown('<div class="lottie-container">', unsafe_allow_html=True)
                        st_lottie(lottie_success_json, height=150, key="success_animation_loan")
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.success("Your application has been submitted!")
                    st.session_state["loan_submitted"] = True # Set a flag to prevent re-submission on refresh
                    # st.experimental_rerun() # Removed to avoid error in older Streamlit versions
                except Exception as e:
                    st.error(f"Error submitting application: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True) # End of Loan Application Form card
