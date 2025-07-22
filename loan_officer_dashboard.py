import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.stoggle import stoggle
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_lottie import st_lottie
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import difflib
import re
import requests
import json
import math
import base64

# Load environment variables from .env file at the very top
from dotenv import load_dotenv
load_dotenv()

# RAG-related imports
import openai
from openai import AzureOpenAI
from rag_pipeline import get_embedding, search_vector_top_k, clean_chunks, build_context, get_answer

# Load Lottie animation for feedback (if available)
lottie_json = None
try:
    with open("Search  Processing.json", "r") as f:
        lottie_json = json.load(f)
except Exception:
    pass

# Microsoft Fluent UI color palette
PRIMARY_BLUE = "#0078D4"
NEUTRAL_GREY = "#F3F2F1"
DARK_GREY = "#605E5C"
WHITE = "#FFFFFF"

# Custom CSS for Microsoft look
st.markdown(
    f"""
    <style>
    html, body, [class*='css']  {{
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        background-color: {NEUTRAL_GREY};
    }}
    .stApp {{
        background-color: {NEUTRAL_GREY};
    }}
    .main-header {{
        background: {WHITE};
        color: {DARK_GREY};
        padding: 2rem 2rem 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border-left: 5px solid {PRIMARY_BLUE};
    }}
    .main-header h1 {{
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        color: {PRIMARY_BLUE};
    }}
    .main-header p {{
        font-size: 1rem;
        color: {DARK_GREY};
        margin: 0.5rem 0 0 0;
    }}
    .card-container {{
        background: {WHITE};
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #E1DFDD;
    }}
    .section-header {{
        color: {PRIMARY_BLUE};
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        border-bottom: 2px solid #E1DFDD;
        padding-bottom: 0.5rem;
    }}
    .stButton > button {{
        background: {PRIMARY_BLUE};
        color: {WHITE};
        border-radius: 4px;
        font-weight: 500;
        padding: 0.6rem 1.2rem;
        font-size: 1rem;
        border: none;
        box-shadow: 0 1px 3px rgba(0,120,212,0.08);
        min-height: 36px;
    }}
    .stButton > button:hover {{
        background: #106ebe;
        color: {WHITE};
    }}
    .stSelectbox > div > div {{
        border-radius: 4px;
        border: 1px solid #d2d0ce;
        min-height: 36px;
        font-size: 1rem;
    }}
    .stTextInput > div > input {{
        border-radius: 4px;
        border: 1px solid #d2d0ce;
        min-height: 36px;
        padding: 0.5rem 0.75rem;
        font-size: 1rem;
    }}
    .stTextInput > div > input:focus {{
        border-color: {PRIMARY_BLUE};
        box-shadow: 0 0 0 1px {PRIMARY_BLUE};
        outline: none;
    }}
    .alert {{
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid {PRIMARY_BLUE};
        font-size: 1rem;
        background: #deecf9;
        color: #005a9e;
    }}
    .alert-success {{
        background: #dff6dd;
        border-left-color: #107c10;
        color: #107c10;
    }}
    .alert-error {{
        background: #fde7e9;
        border-left-color: #d13438;
        color: #a80000;
    }}
    .alert-info {{
        background: #deecf9;
        border-left-color: {PRIMARY_BLUE};
        color: #005a9e;
    }}
    .metric-card {{
        background: {WHITE};
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        padding: 1.2rem 1rem;
        text-align: center;
        border: 1px solid #E1DFDD;
        margin-bottom: 1rem;
    }}
    .metric-title {{
        color: {DARK_GREY};
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }}
    .metric-value {{
        color: {PRIMARY_BLUE};
        font-size: 2rem;
        font-weight: 700;
    }}
    .metric-icon {{
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
        opacity: 0.8;
    }}
    .stDataFrame {{
        background: {WHITE};
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        border: 1px solid #E1DFDD;
        overflow: hidden;
    }}
    .ai-tool-widget {{
        background-color: {WHITE};
        border: 1px solid #E1DFDD;
        border-radius: 10px;
            padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        min-height: 350px; /* Ensures consistent tile height */
    }}
    .ai-tool-widget h3 {{
        font-size: 1.2rem;
        font-weight: 600;
        color: {PRIMARY_BLUE};
        margin-top: 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E1DFDD;
    }}
    .ai-tool-widget p {{
        font-size: 1rem;
        color: {DARK_GREY};
        margin-bottom: 1.5rem;
    }}
    .clickable-widget {{
        cursor: pointer;
        transition: all 0.2s ease-in-out;
    }}
    .clickable-widget:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }}
    .active-widget {{
        border: 2px solid {PRIMARY_BLUE};
        box-shadow: 0 4px 12px rgba(0, 120, 212, 0.2);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Load environment variables
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

def verify_document_via_api(document_id, query, api_url="http://localhost:8000/verify"):
    payload = {"document_id": document_id, "query": query}
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
    st.markdown('<div class="section-header">AI Tools</div>', unsafe_allow_html=True)

    with st.expander("📊 Eligibility Assessment"):
        st.markdown("<p>Analyzes an applicant's documents to provide a comprehensive eligibility assessment and confidence score.</p>", unsafe_allow_html=True)
        all_applicants = sorted(set(doc_df["applicant_id"].unique().tolist()))
        selected_applicant = st.selectbox("Select Applicant", [""] + all_applicants, key="eligibility_applicant")
        if st.button("🔍 Run Assessment", disabled=not selected_applicant, type="primary", use_container_width=True):
            with st.spinner("Running AI eligibility assessment..."):
                try:
                    response = requests.post(
                        "http://localhost:8000/check-eligibility",
                        json={"applicant_id": selected_applicant},
                        timeout=30
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.markdown("---")
                        st.markdown("### 📊 Assessment Results")
                        col1_res, col2_res, col3_res = st.columns(3)
                        with col1_res:
                            decision = result.get('decision', 'Unknown')
                            decision_icon = '✅' if decision.lower() == 'yes' else ('⚠️' if decision.lower() == 'needs review' else '❌')
                            alert_class = 'alert-success' if decision.lower() == 'yes' else ('alert-warning' if decision.lower() == 'needs review' else 'alert-error')
                            st.markdown(f'<div class="alert {alert_class}"><strong>Decision:</strong> {decision_icon} {decision}</div>', unsafe_allow_html=True)
                        with col2_res:
                            score = result.get('score', 0)
                            st.metric("Confidence Score", f"{score}")
                        summary = result.get('summary', 'No reasoning provided')
                        st.markdown("**AI Reasoning:**")
                        st.markdown(f'<div class="alert alert-info">{summary}</div>', unsafe_allow_html=True)
                        # Download full report as JSON
                        report_data = {
                            'decision': result.get('decision'),
                            'score': result.get('score'),
                            'summary': result.get('summary'),
                            'criteria': result.get('criteria'),
                            'report_url': result.get('report_url')
                        }
                        st.download_button(
                            label="📥 Download Full Report (JSON)",
                            data=json.dumps(report_data, indent=2),
                            file_name=f"{selected_applicant}_eligibility_report.json",
                            mime="application/json"
                        )
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

    with st.expander("🛡️ Document Verification"):
        st.markdown("<p>Analyze all documents for an applicant for authenticity, content, compliance, and potential risks. Issues will be highlighted in the breakdown.</p>", unsafe_allow_html=True)
        all_applicants = sorted(set(doc_df["applicant_id"].unique().tolist()))
        selected_verif_applicant = st.selectbox("Select Applicant for Verification", [""] + all_applicants, key="verification_applicant")
        verif_query = st.text_area("Verification query (optional):", key="verification_query_applicant")
        if st.button("🔍 Run Applicant Analysis", disabled=not selected_verif_applicant, type="primary", use_container_width=True):
            with st.spinner("Running applicant document analysis..."):
                try:
                    response = requests.post(
                        "http://localhost:8000/analyze-applicant",
                        json={"applicant_id": selected_verif_applicant, "query": verif_query},
                        timeout=30
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.markdown("---")
                        st.markdown("### 🛡️ Applicant Document Verification Results")
                        st.markdown(f'<div class="alert alert-info" style="white-space: pre-line;">{result.get('summary', 'No summary provided')}</div>', unsafe_allow_html=True)
                        # Show breakdown as a table
                        breakdown = result.get('breakdown', [])
                        if breakdown:
                            st.markdown("**Breakdown:**")
                            for b in breakdown:
                                doc_line = f"{b['icon']} <b>{b['document']}</b>: {b['status'].capitalize()}"
                                if b['issues']:
                                    doc_line += f" <span style='color: #a80000;'>Issues: {', '.join(b['issues'])}</span>"
                                st.markdown(doc_line, unsafe_allow_html=True)
                                st.caption(b.get('summary', ''))
                        # Download full report as JSON
                        st.download_button(
                            label="📥 Download Full Verification Report (JSON)",
                            data=json.dumps(result, indent=2),
                            file_name=f"{selected_verif_applicant}_verification_report.json",
                            mime="application/json"
                        )
                    else:
                        st.error(f"❌ Verification agent error: {response.status_code} - {response.text}")
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. The verification agent may be busy.")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Could not connect to verification agent. Please ensure it's running on localhost:8000")
                except Exception as e:
                    st.error(f"❌ Failed to contact verification agent: {e}")

    with st.expander("⚖️ Compliance Agent"):
        st.markdown("<p>Checks documents against regulatory standards and internal policies based on your query.</p>", unsafe_allow_html=True)
        compliance_query = st.text_area("Compliance query:", key="compliance_query")
        if st.button("🔍 Run Compliance Check", disabled=not compliance_query, type="primary", use_container_width=True):
            with st.spinner("Running compliance check..."):
                try:
                    result = "Compliance check functionality is under development."
                    st.markdown("---")
                    st.markdown("### ⚖️ Compliance Check Results")
                    st.markdown(f'<div class="alert alert-info">{result}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ Compliance agent error: {e}")

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