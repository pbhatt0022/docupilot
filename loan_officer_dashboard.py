import streamlit as st
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime

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

st.set_page_config(page_title="🧾 Loan Officer Dashboard", layout="wide")
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
    st.stop()

# Applicant Overview (based on applicant status)
st.subheader("📊 Application Overview")
if 'applicant_status' not in df:
    df['applicant_status'] = 'In progress'  # Default if not present
col1, col2, col3 = st.columns(3)
col1.metric("Applicants In Progress", len(df[df['applicant_status'] == 'In progress']['applicant_id'].unique()))
col2.metric("Applicants Approved", len(df[df['applicant_status'] == 'Approved']['applicant_id'].unique()))
col3.metric("Applicants Rejected", len(df[df['applicant_status'] == 'Rejected']['applicant_id'].unique()))

st.divider()

# Filter section
st.subheader("🔍 Filter & Review Documents")
applicant_filter = st.selectbox("Filter by Applicant ID", ["All"] + sorted(df["applicant_id"].unique().tolist()))
doc_type_filter = st.selectbox("Filter by Document Type", ["All"] + sorted(df["predicted_classification"].unique().tolist()))
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
        format_func=lambda x: f"{x} ({table_df.loc[table_df['file_name'] == x, 'predicted_classification'].values[0]})"
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
