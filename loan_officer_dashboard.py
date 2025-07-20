import streamlit as st
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime
import difflib
import re
import requests
from streamlit_lottie import st_lottie
import json
import math

# RAG-related imports
import openai
from openai import AzureOpenAI
# Assuming rag_pipeline.py is in the same directory or accessible via PYTHONPATH
from rag_pipeline import get_embedding, search_vector_top_k, clean_chunks, build_context, get_answer

# Load Lottie animation for feedback (if available)
lottie_json = None
try:
    with open("Search  Processing.json", "r") as f:
        lottie_json = json.load(f)
except Exception:
    pass

# Clean, professional CSS focused on banking UI/UX
st.markdown(
    """
    <style>
    /* Import Microsoft Fluent UI fonts */
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', 'Helvetica Neue', sans-serif;
    }
    
    .block-container {
        padding: 1.5rem 2rem;
        max-width: 1400px;
    }
    
    /* Clean Header */
    .main-header {
        background: white;
        color: #323130;
        padding: 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #0078d4;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 1.75rem;
        font-weight: 600;
        color: #323130;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        color: #605e5c;
        font-weight: 400;
    }
    
    /* Clean Tab Navigation */
    .tab-container {
        background: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
        overflow: hidden;
    }
    
    .tab-button {
        background: transparent;
        border: none;
        padding: 1rem 1.5rem;
        font-size: 0.9rem;
        font-weight: 500;
        color: #605e5c;
        cursor: pointer;
        transition: all 0.2s ease;
        border-bottom: 3px solid transparent;
    }
    
    .tab-button.active {
        color: #0078d4;
        border-bottom: 3px solid #0078d4;
        background: #f8f9fa;
    }
    
    .tab-button:hover:not(.active) {
        background: #f3f2f1;
        color: #323130;
    }
    
    /* Simplified Cards */
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #edebe9;
        transition: all 0.2s ease;
        text-align: center;
    }
    
    .metric-card:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        transform: translateY(-1px);
    }
    
    .metric-title {
        color: #605e5c;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        color: #0078d4;
        font-size: 1.8rem;
        font-weight: 700;
        line-height: 1.2;
    }
    
    .metric-icon {
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        opacity: 0.7;
    }
    
    /* Clean Card Containers */
    .card-container {
        background: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #edebe9;
        margin-bottom: 1.5rem;
    }
    
    /* Section Headers */
    .section-header {
        color: #323130;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #edebe9;
    }
    
    /* Clean Buttons */
    .stButton > button {
        background: #0078d4;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 500;
        padding: 0.6rem 1.2rem;
        font-size: 0.85rem;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0, 120, 212, 0.3);
        min-height: 36px;
    }
    
    .stButton > button:hover {
        background: #106ebe;
        box-shadow: 0 2px 6px rgba(0, 120, 212, 0.4);
        transform: translateY(-1px);
    }
    
    .stButton > button[kind="secondary"] {
        background: white;
        color: #0078d4;
        border: 1px solid #0078d4;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: #f8f9fa;
        border-color: #106ebe;
        color: #106ebe;
    }
    
    /* Form Controls */
    .stSelectbox > div > div {
        border-radius: 4px;
        border: 1px solid #d2d0ce;
        min-height: 36px;
        font-size: 0.9rem;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #0078d4;
        box-shadow: 0 0 0 1px #0078d4;
    }
    
    .stTextInput > div > input {
        border-radius: 4px;
        border: 1px solid #d2d0ce;
        min-height: 36px;
        padding: 0.5rem 0.75rem;
        font-size: 0.9rem;
    }
    
    .stTextInput > div > input:focus {
        border-color: #0078d4;
        box-shadow: 0 0 0 1px #0078d4;
        outline: none;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.6rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .status-approved {
        background: #dff6dd;
        color: #107c10;
    }
    
    .status-pending {
        background: #fff4ce;
        color: #8a6914;
    }
    
    .status-incomplete {
        background: #fde7e9;
        color: #a80000;
    }
    
    .status-flagged {
        background: #fde7e9;
        color: #a80000;
    }
    
    /* Document List */
    .document-item {
        background: white;
        border: 1px solid #edebe9;
        border-radius: 6px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .document-item:hover {
        border-color: #0078d4;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    }
    
    .document-item.selected {
        border-color: #0078d4;
        background: #f8f9ff;
        box-shadow: 0 0 0 1px #0078d4;
    }
    
    .doc-name {
        font-weight: 500;
        color: #323130;
        margin-bottom: 0.25rem;
        font-size: 0.9rem;
    }
    
    .doc-meta {
        font-size: 0.75rem;
        color: #605e5c;
        margin-bottom: 0.5rem;
    }
    
    /* Alert Styles */
    .alert {
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        border-left: 3px solid;
        font-size: 0.85rem;
    }
    
    .alert-success {
        background: #dff6dd;
        border-left-color: #107c10;
        color: #107c10;
    }
    
    .alert-warning {
        background: #fff4ce;
        border-left-color: #ffb900;
        color: #8a6914;
    }
    
    .alert-error {
        background: #fde7e9;
        border-left-color: #d13438;
        color: #a80000;
    }
    
    .alert-info {
        background: #deecf9;
        border-left-color: #0078d4;
        color: #005a9e;
    }
    
    /* DataFrames */
    .stDataFrame {
        background: white;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #edebe9;
        overflow: hidden;
    }
    
    /* Chat Container */
    .chat-container {
        background: white;
        border: 1px solid #edebe9;
        border-radius: 6px;
        height: 400px;
        overflow-y: auto;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Spacing Improvements */
    .stMetric {
        background: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
        border: 1px solid #edebe9;
        text-align: center;
    }
    
    .stMetric:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        transform: translateY(-1px);
    }
    
    .stMetric [data-testid="metric-container"] > div:first-child {
        color: #605e5c;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stMetric [data-testid="metric-container"] > div:nth-child(2) {
        color: #0078d4;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
        
        .main-header {
            padding: 1.5rem;
        }
        
        .metric-card {
            padding: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Load environment variables
load_dotenv()
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB_NAME = "LoanApplicationDB"
COSMOS_CONTAINER_NAME = "DocumentMetadata"
BLOB_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# Initialize Azure clients
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.get_database_client(COSMOS_DB_NAME)
container = database.get_container_client(COSMOS_CONTAINER_NAME)
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)

# Page configuration
st.set_page_config(
    page_title="Loan Officer Dashboard", 
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🏦"
)

# Clean header
st.markdown(
    """
    <div class="main-header">
        <h1>Loan Officer Dashboard</h1>
        <p>Review applications, documents, and manage loan approvals</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Helper functions
def create_status_badge(status, is_flagged=False):
    """Create a clean status badge"""
    if is_flagged:
        return f'<span class="status-badge status-flagged">🚩 FLAGGED</span>'
    
    status_classes = {
        'approved': 'status-approved',
        'pending_review': 'status-pending',
        'incomplete': 'status-incomplete',
        'under review': 'status-pending',
        'rejected': 'status-incomplete'
    }
    
    status_text = {
        'approved': '✅ APPROVED',
        'pending_review': '⏳ PENDING',
        'incomplete': '❌ INCOMPLETE',
        'under review': '⏳ UNDER REVIEW',
        'rejected': '❌ REJECTED'
    }
    
    css_class = status_classes.get(status, 'status-pending')
    text = status_text.get(status, status.upper())
    
    return f'<span class="status-badge {css_class}">{text}</span>'

def create_metric_card(title, value, icon="📊"):
    """Create a clean metric card"""
    return f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """

def clean_cosmos_document(doc):
    # Convert Series to dict if needed
    if hasattr(doc, 'to_dict'):
        doc = doc.to_dict()
    # Remove Pandas index name if present
    doc.pop('Name', None)
    # Remove Cosmos system fields
    for key in list(doc.keys()):
        if key.startswith('_'):
            doc.pop(key)
    # Replace NaN with None
    for k, v in doc.items():
        if isinstance(v, float) and math.isnan(v):
            doc[k] = None
    return doc

# Fetch all metadata from Cosmos
@st.cache_data(ttl=60)
def fetch_all_documents():
    try:
        query = "SELECT * FROM c"
        docs = list(container.query_items(query=query, enable_cross_partition_query=True))
        return pd.DataFrame(docs)
    except Exception as e:
        st.error(f"Error fetching documents: {e}")
        return pd.DataFrame()

# Load data
with st.spinner("Loading data..."):
    df = fetch_all_documents()

if df.empty:
    st.error("No documents or loan applications found in Cosmos DB.")
    st.stop()

# Separate document items and loan application items
doc_mask = ~df['id'].str.endswith('_loan_app')
loan_app_mask = df['id'].str.endswith('_loan_app')
doc_df = df[doc_mask].copy()
loan_app_df = df[loan_app_mask].copy()

# Ensure status column exists and has default values
if 'status' not in doc_df or doc_df['status'].isnull().any():
    doc_df['status'] = doc_df['status'].fillna('pending_review')
doc_df.loc[doc_df['status'] == '', 'status'] = 'pending_review'

# RAG: Initialize session state for chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# RAG: Pipeline wrapper function
def process_rag_query(question):
    try:
        embedding = get_embedding(question)
        raw_chunks = search_vector_top_k(embedding)
        cleaned_chunks = clean_chunks(raw_chunks)
        context, file_set = build_context(cleaned_chunks)
        answer = get_answer(question, context)
        return answer, file_set
    except Exception as e:
        return f"Error processing query: {str(e)}", set()

# Initialize active tab in session state if not exists
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0

# Clean tab navigation
tab_names = ["📊 Overview", "📋 Application Review", "🤖 AI Tools", "💬 Document Assistant"]

st.markdown('<div class="tab-container">', unsafe_allow_html=True)
cols = st.columns(4)
for i, tab_name in enumerate(tab_names):
    with cols[i]:
        if st.button(
            tab_name,
            key=f"tab_button_{i}",
            use_container_width=True,
            type="primary" if st.session_state.active_tab == i else "secondary"
        ):
            st.session_state.active_tab = i
st.markdown('</div>', unsafe_allow_html=True)

# TAB 1: OVERVIEW
if st.session_state.active_tab == 0:
    # Calculate metrics
    total_applicants = len(set(doc_df["applicant_id"].unique().tolist() + loan_app_df["applicant_id"].unique().tolist()))
    total_documents = len(doc_df)
    pending_docs = len(doc_df[doc_df['status'] == 'pending_review'])
    approved_docs = len(doc_df[doc_df['status'] == 'approved'])
    flagged_docs = len(doc_df[doc_df.get('flagged_by_ai', False) == True])
    
    # Loan metrics
    total_loan_amount = 0
    if not loan_app_df.empty:
        for _, row in loan_app_df.iterrows():
            loan_app = row.get('loan_application', {})
            amount = loan_app.get('loan_amount', 0)
            if isinstance(amount, (int, float)):
                total_loan_amount += amount
    
    # Display metrics in a clean grid
    st.markdown('<div class="section-header">Application Metrics</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    
    with col1:
        st.metric("Total Applicants", total_applicants)
    
    with col2:
        st.metric("Total Documents", total_documents)
    
    with col3:
        st.metric("Pending Review", pending_docs)
    
    with col4:
        st.metric("Approved", approved_docs)
    
    with col5:
        st.metric("AI Flagged", flagged_docs)
    
    with col6:
        formatted_amount = f"₹{total_loan_amount:,.0f}" if total_loan_amount > 0 else "₹0"
        st.metric("Total Loan Amount", formatted_amount)
    
    # Recent Applications Table
    st.markdown('<div class="section-header">Recent Loan Applications</div>', unsafe_allow_html=True)
    
    if not loan_app_df.empty:
        # Prepare summary data
        summary_data = []
        for _, row in loan_app_df.iterrows():
            la = row.get('loan_application', {})
            summary_data.append({
                'Applicant ID': row.get('applicant_id', ''),
                'Loan Amount': f"₹{la.get('loan_amount', 0):,.0f}",
                'Tenure': f"{la.get('tenure_months', 0)} months",
                'Purpose': la.get('loan_purpose', ''),
                'EMI': f"₹{la.get('emi', 0):,.0f}",
                'Status': la.get('status', 'under review'),
                'Submitted': la.get('submitted_at', '')[:10] if la.get('submitted_at') else ''
            })
        
        loan_summary_df = pd.DataFrame(summary_data)
        
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        st.dataframe(loan_summary_df, use_container_width=True, hide_index=True)
        
        # Download button
        csv = loan_summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name='loan_applications_summary.csv',
            mime='text/csv',
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No loan applications found.")

# TAB 2: APPLICATION REVIEW
elif st.session_state.active_tab == 1:
    st.markdown('<div class="section-header">Filter Applications</div>', unsafe_allow_html=True)
    
    # Clean filter section
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        all_applicants = sorted(set(doc_df["applicant_id"].unique().tolist() + loan_app_df["applicant_id"].unique().tolist()))
        applicant_filter = st.selectbox("Applicant ID", ["All Applicants"] + all_applicants)
    
    with col2:
        doc_types = doc_df["predicted_classification"].dropna().astype(str).unique().tolist()
        doc_type_filter = st.selectbox("Document Type", ["All Types"] + sorted(doc_types))
    
    with col3:
        status_filter = st.selectbox("Status", ["All Statuses", "pending_review", "approved", "incomplete"])
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        apply_filters = st.button("🔍 Apply Filters", type="primary")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Apply filters
    filtered_doc_df = doc_df.copy()
    if applicant_filter != "All Applicants":
        filtered_doc_df = filtered_doc_df[filtered_doc_df["applicant_id"] == applicant_filter]
    if status_filter != "All Statuses":
        filtered_doc_df = filtered_doc_df[filtered_doc_df["status"] == status_filter]
    if doc_type_filter != "All Types":
        filtered_doc_df = filtered_doc_df[filtered_doc_df["predicted_classification"] == doc_type_filter]
    
    # Two-column layout for document list and details
    col_list, col_detail = st.columns([1, 2])
    
    with col_list:
        st.markdown(f'<div class="section-header">Documents ({len(filtered_doc_df)})</div>', unsafe_allow_html=True)
        
        if not filtered_doc_df.empty:
            st.markdown('<div class="card-container" style="max-height: 500px; overflow-y: auto;">', unsafe_allow_html=True)
            
            # Create clean document list
            for idx, row in filtered_doc_df.iterrows():
                is_selected = 'selected_doc' in st.session_state and st.session_state.selected_doc.get('id') == row.get('id')
                
                # Create clickable document item
                if st.button(
                    f"📄 {row.get('file_name', 'Unknown')}",
                    key=f"doc_select_{row.get('id', idx)}",
                    help=f"Type: {row.get('predicted_classification', 'Unknown')} | Status: {row.get('status', 'pending_review')}",
                    use_container_width=True
                ):
                    st.session_state.selected_doc = row
                
                # Show metadata and status
                st.caption(f"{row.get('applicant_id', 'Unknown')} • {row.get('predicted_classification', 'Unknown')}")
                status_html = create_status_badge(row.get('status', 'pending_review'), row.get('flagged_by_ai', False))
                st.markdown(status_html, unsafe_allow_html=True)
                st.markdown("---")
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No documents match your filters.")
    
    with col_detail:
        st.markdown('<div class="section-header">Document Details</div>', unsafe_allow_html=True)
        
        if 'selected_doc' in st.session_state:
            row = st.session_state.selected_doc
            
            st.markdown('<div class="card-container">', unsafe_allow_html=True)
            
            # Document header
            st.markdown(f"### {row.get('file_name', 'Unknown Document')}")
            
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"**Type:** {row.get('predicted_classification', 'Unknown')}")
                st.markdown(f"**Applicant:** {row.get('applicant_id', 'Unknown')}")
            with col_info2:
                st.markdown(f"**Uploaded:** {row.get('upload_time', 'Unknown')[:10] if row.get('upload_time') else 'Unknown'}")
                st.markdown(f"**Size:** {row.get('file_size', 'Unknown')}")
            
            # AI Flag Status
            flagged = row.get("flagged_by_ai", False)
            flagged_reason = row.get("flagged_reason", "")
            
            if flagged:
                st.markdown(
                    f'<div class="alert alert-error"><strong>🚩 Flagged by AI:</strong> {flagged_reason}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="alert alert-success"><strong>✅ Document Verified:</strong> No issues found</div>',
                    unsafe_allow_html=True
                )
            
            # Extracted Fields
            extracted = row.get("extracted_fields", {})
            if extracted:
                with st.expander("📋 Extracted Information", expanded=True):
                    extracted_df = pd.DataFrame(list(extracted.items()), columns=["Field", "Value"])
                    st.table(extracted_df)
            
            # Document actions
            st.markdown("---")
            
            col_view, col_status, col_save = st.columns([1, 2, 1])
            
            with col_view:
                if st.button("👁️ View", key=f"view_{row.get('id')}", use_container_width=True):
                    st.markdown(f"[🗂 Open Document]({row.get('blob_url', '#')})")
            
            with col_status:
                # Status update
                status_options = ["pending_review", "approved", "incomplete"]
                current_status = row.get("status", "pending_review")
                new_status = st.selectbox(
                    "Update Status",
                    status_options,
                    index=status_options.index(current_status),
                    key=f"status_update_{row.get('id')}"
                )
            
            with col_save:
                save_updates = st.button("💾 Save", key=f"save_updates_{row.get('id')}", type="primary", use_container_width=True)
            
            # Comments
            with st.expander("💬 Officer Comments"):
                new_comment = st.text_area(
                    "Add your comments:",
                    value=row.get("officer_comments", ""),
                    key=f"comment_update_{row.get('id')}",
                    height=100
                )
            
            # Save button action
            if save_updates:
                try:
                    updated = row.copy()
                    updated["status"] = new_status
                    updated["officer_comments"] = new_comment
                    updated["last_updated"] = datetime.utcnow().isoformat()
                    
                    print("UPDATING DOCUMENT:", updated)
                    updated = clean_cosmos_document(updated)
                    print("CLEANED DOCUMENT:", updated)
                    container.upsert_item(updated)
                    
                    st.success("✅ Document updated successfully!")
                    st.cache_data.clear()
                    
                    # Show success animation if available
                    
                except Exception as e:
                    st.error(f"❌ Error updating document: {e}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card-container">', unsafe_allow_html=True)
            st.info("👈 Select a document from the list to view details")
            st.markdown('</div>', unsafe_allow_html=True)

# TAB 3: AI TOOLS
elif st.session_state.active_tab == 2:
    st.markdown('<div class="section-header">AI Eligibility Assessment</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    
    st.markdown("""
    The AI eligibility agent will analyze the applicant's documents and loan application to provide 
    a comprehensive eligibility assessment with confidence scoring.
    """)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        all_applicants = sorted(set(doc_df["applicant_id"].unique().tolist() + loan_app_df["applicant_id"].unique().tolist()))
        selected_applicant = st.selectbox(
            "Applicant ID for Evaluation",
            [""] + all_applicants,
            key="eligibility_applicant"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_assessment = st.button(
            "🔍 Run Assessment",
            disabled=not selected_applicant,
            type="primary",
            use_container_width=True
        )
    
    if run_assessment and selected_applicant:
        with st.spinner("Running AI eligibility assessment..."):
            try:
                response = requests.post(
                    "http://localhost:8000/check-eligibility",
                    json={"applicant_id": selected_applicant},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display results
                    st.markdown("---")
                    st.markdown("### 📊 Assessment Results")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        decision = result.get('decision', 'Unknown')
                        if decision.lower() == 'approved':
                            st.markdown(
                                f'<div class="alert alert-success"><strong>Decision:</strong> ✅ {decision}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div class="alert alert-error"><strong>Decision:</strong> ❌ {decision}</div>',
                                unsafe_allow_html=True
                            )
                    
                    with col2:
                        score = result.get('score', 0)
                        st.metric("Confidence Score", f"{score}%")
                    
                    with col3:
                        report_url = result.get('report_url', '#')
                        st.markdown(f"[📄 View Full Report]({report_url})")
                    
                    # Reasoning
                    reasoning = result.get('reasoning', 'No reasoning provided')
                    st.markdown("**AI Reasoning:**")
                    st.markdown(
                        f'<div class="alert alert-info">{reasoning}</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Show success animation if available
                    if lottie_json:
                        st_lottie(lottie_json, height=120, key="eligibility_success")
                        
                else:
                    st.error(f"❌ Eligibility agent error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                st.error("❌ Request timed out. The eligibility agent may be busy.")
            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to eligibility agent. Please ensure it's running on localhost:8000")
            except Exception as e:
                st.error(f"❌ Failed to contact eligibility agent: {e}")
    
    elif run_assessment and not selected_applicant:
        st.warning("Please select an applicant ID first.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# TAB 4: DOCUMENT ASSISTANT (RAG)
elif st.session_state.active_tab == 3:
    st.markdown('<div class="section-header">Document Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.markdown("Ask questions about the loan documents and get AI-powered answers.")
    
    # Only show chat container if there are messages
    if st.session_state.messages:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant" and "sources" in message:
                    if message["sources"]:
                        st.caption(f"📁 Sources: {', '.join(message['sources'])}")
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the documents...", key="rag_chat_input"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from RAG pipeline
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer, sources = process_rag_query(prompt)
                st.markdown(answer)
                if sources:
                    st.caption(f"📁 Sources: {', '.join(sources)}")
        
        # Add assistant response to chat history
        st.session_state.messages.append({
            "role": "assistant", 
            "content": answer,
            "sources": sources
        })
    
    # Clear chat button
    col_clear, col_spacer = st.columns([1, 4])
    with col_clear:
        if st.button("🗑️ Clear Chat", key="rag_clear_chat_button"):
            st.session_state.messages = []
    
    st.markdown('</div>', unsafe_allow_html=True)

# Clean footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #605e5c; font-size: 0.8rem; padding: 1rem;">
        🏦 Loan Officer Dashboard | Powered by Azure Cosmos DB & AI
    </div>
    """,
    unsafe_allow_html=True,
)