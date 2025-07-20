import streamlit as st
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime
import openai
from openai import AzureOpenAI
import requests
import json

# Load environment variables
load_dotenv()
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB_NAME = "LoanApplicationDB"
COSMOS_CONTAINER_NAME = "DocumentMetadata"
BLOB_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# Import RAG Pipeline functions
from rag_pipeline import get_embedding, search_vector_top_k, clean_chunks, build_context, get_answer

# Initialize Azure clients
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.get_database_client(COSMOS_DB_NAME)
container = database.get_container_client(COSMOS_CONTAINER_NAME)
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)

st.set_page_config(page_title="🧾 Loan Officer Dashboard", layout="wide")

# Initialize session state for chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# RAG Pipeline wrapper function

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

# Create main layout with columns
col1, col2 = st.columns([2, 1])

with col1:
    st.title("🧾 Loan Officer Dashboard")
    
    # Fetch all metadata from Cosmos
    @st.cache_data(ttl=60)
    def fetch_all_documents():
        query = "SELECT * FROM c"
        docs = list(container.query_items(query=query, enable_cross_partition_query=True))
        return pd.DataFrame(docs)

    df = fetch_all_documents()

    if 'status' not in df or df['status'].isnull().any():
        df['status'] = df['status'].fillna('pending_review')
    df.loc[df['status'] == '', 'status'] = 'pending_review'

    if df.empty:
        st.warning("No documents found in Cosmos DB.")
    else:
        # Applicant Overview (based on applicant status)
        st.subheader("📊 Application Overview")
        if 'applicant_status' not in df:
            df['applicant_status'] = 'In progress'  # Default if not present
        col1_1, col1_2, col1_3 = st.columns(3)
        col1_1.metric("Applicants In Progress", len(df[df['applicant_status'] == 'In progress']['applicant_id'].unique()))
        col1_2.metric("Applicants Approved", len(df[df['applicant_status'] == 'Approved']['applicant_id'].unique()))
        col1_3.metric("Applicants Rejected", len(df[df['applicant_status'] == 'Rejected']['applicant_id'].unique()))

        st.divider()

        # Filter section
        st.subheader("🔍 Filter & Review Documents")
        applicant_filter = st.selectbox("Filter by Applicant ID", ["All"] + sorted(df["applicant_id"].unique().tolist()))
        doc_types = [x for x in df["predicted_classification"].unique().tolist() if isinstance(x, str)]
        doc_type_filter = st.selectbox("Filter by Document Type", ["All"] + sorted(doc_types))
        status_filter = st.selectbox("Filter by Document Status", ["All", "pending_review", "approved", "incomplete"])

        filtered_df = df.copy()
        if applicant_filter != "All":
            filtered_df = filtered_df[filtered_df["applicant_id"] == applicant_filter]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df["status"] == status_filter]
        if doc_type_filter != "All":
            filtered_df = filtered_df[filtered_df["predicted_classification"] == doc_type_filter]

        # Add a Flagged column (True if flagged_by_ai, else False)
        filtered_df['Flagged'] = filtered_df.get('flagged_by_ai', False)

        st.subheader("📁 Applicant Documents (Filtered)")

        if not filtered_df.empty:
            # Show a table with basic info and flagged status
            display_cols = ["file_name", "predicted_classification", "status", "upload_time", "Flagged"]
            table_df = filtered_df[display_cols].reset_index(drop=True)
            st.dataframe(table_df, use_container_width=True)

            # Let user select a row by file name (or any unique field)
            doc_options = table_df["file_name"].tolist()
            selected_file = st.selectbox(
                "Select a document to review",
                options=doc_options,
                format_func=lambda x: (
                    f"{x} ({table_df.loc[table_df['file_name'] == x, 'predicted_classification'].values[0]})"
                    if not table_df.loc[table_df['file_name'] == x, 'predicted_classification'].empty
                    else f"{x} (Unknown)"
                )
            )

            # Get the full row for the selected document
            row = filtered_df[filtered_df["file_name"] == selected_file].iloc[0]

            st.markdown("---")
            st.subheader(f"📄 Details for {row['file_name']}")

            # Show AI flag status and reasoning
            flagged = row.get("flagged_by_ai", False)
            flagged_reason = row.get("flagged_reason", "")

            if flagged:
                st.warning("🚩 Flagged by AI: Flagged")
                st.error(f"Reason for flag: {flagged_reason}")
            else:
                st.success(f"Flagged by AI: Not Flagged — {flagged_reason}")

            # If the document is flagged by AI, show missing fields
            if row.get("flagged_by_ai", False):
                missing = row.get("missing_fields", [])
                if missing:
                    st.error(f"Missing fields: {', '.join(missing)}")
                else:
                    st.info("No missing fields detected.")

            # Display extracted fields for the selected document
            extracted = row.get("extracted_fields", {})
            if extracted:
                st.subheader("Extracted Fields")
                st.table(pd.DataFrame(list(extracted.items()), columns=["Field", "Value"]))
            else:
                st.warning("⚠️ No extracted data available.")

            # Display raw extracted fields for the selected document
            raw_extracted = row.get("raw_extracted_fields", {})
            if raw_extracted:
                st.subheader("Raw Extracted Fields (from Azure)")
                st.table(pd.DataFrame(list(raw_extracted.items()), columns=["Raw Field Name", "Value"]))

            view_option = st.radio(
                "View Options", ["Raw Document", "Extracted Information"], key=f"view_{row['id']}"
            )
            if view_option == "Raw Document":
                st.markdown(f"[🗂 Open Document in New Tab]({row['blob_url']})")
            else:
                extracted = row.get("extracted_fields", {})
                if extracted:
                    st.table(pd.DataFrame(list(extracted.items()), columns=["Field", "Value"]))
                else:
                    st.warning("⚠️ No extracted data available.")

            st.markdown(f"**📄 Document Type:** `{row['predicted_classification']}`")
            st.markdown(f"🤖 **AI Classification Reason:** `{row.get('reasoning', 'N/A')}`")
            # Editable fields for document status
            status_options = ["pending_review", "approved", "incomplete"]
            new_status = st.selectbox(
                "📝 Update Document Status",
                status_options,
                index=status_options.index(row.get("status", "pending_review")),
                key=f"status_{row['id']}"
            )
            new_comment = st.text_area(
                "💬 Officer Comments",
                value=row.get("officer_comments", ""),
                key=f"comment_{row['id']}"
            )
            if st.button("💾 Save Updates", key=f"save_{row['id']}"):
                updated = row.copy()
                updated["status"] = new_status
                updated["officer_comments"] = new_comment
                updated["last_updated"] = datetime.utcnow().isoformat()
                container.replace_item(item=updated["id"], body=updated, partition_key=updated["applicant_id"])
                st.success("✅ Updated successfully")
        else:
            st.info("No documents match your filter.")

        st.divider()

        # --- Add tabbing for dashboard and eligibility agent ---
        tabs = st.tabs(["Dashboard", "Eligibility Agent (GPT-4o)"])

        dashboard_tab, eligibility_tab = tabs

        with dashboard_tab:
            st.info("📊 Dashboard content is shown above in the main area.")

        with eligibility_tab:
            st.subheader("🤖 Eligibility Agent (GPT-4o)")
            with st.form("eligibility_form"):
                st.markdown("Enter applicant details to check loan eligibility using the AI agent.")
                monthly_salary = st.number_input("Monthly Salary", min_value=0.0, step=1000.0)
                credit_score = st.number_input("Credit Score", min_value=0, max_value=900, step=1)
                employment_type = st.selectbox("Employment Type", ["Salaried", "Self-Employed", "Other"])
                loan_amount = st.number_input("Loan Amount Requested", min_value=0.0, step=10000.0)
                submitted = st.form_submit_button("Check Eligibility")

            if submitted:
                api_url = os.getenv("ELIGIBILITY_AGENT_URL", "http://localhost:8000/check-eligibility")
                payload = {
                    "monthly_salary": monthly_salary,
                    "credit_score": credit_score,
                    "employment_type": employment_type,
                    "loan_amount": loan_amount
                }
                try:
                    response = requests.post(api_url, json=payload, timeout=30)
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"**Decision:** {result['decision']}")
                        st.info(f"**Reason:** {result['reason']}")
                    else:
                        st.error(f"Eligibility agent error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Failed to contact eligibility agent: {e}")

with col2:
    st.header("💬 Document Assistant")
    st.markdown("Ask questions about the loan documents and get AI-powered answers.")
    
    # Chat container with fixed height
    chat_container = st.container()
    
    with chat_container:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant" and "sources" in message:
                    if message["sources"]:
                        st.caption(f"📁 Sources: {', '.join(message['sources'])}")
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the documents..."):
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
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Custom CSS to improve layout
st.markdown("""
<style>
.main .block-container {
    padding-top: 2rem;
}
</style>
""", unsafe_allow_html=True)