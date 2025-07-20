import streamlit as st
from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime
import difflib
import re

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

# --- Separate document items and loan application items ---
doc_mask = ~df['id'].str.endswith('_loan_app')
loan_app_mask = df['id'].str.endswith('_loan_app')
doc_df = df[doc_mask].copy()
loan_app_df = df[loan_app_mask].copy()

if 'status' not in doc_df or doc_df['status'].isnull().any():
    doc_df['status'] = doc_df['status'].fillna('pending_review')
doc_df.loc[doc_df['status'] == '', 'status'] = 'pending_review'

if doc_df.empty and loan_app_df.empty:
    st.warning("No documents or loan applications found in Cosmos DB.")
    st.stop()

# --- Applicant Overview ---
st.subheader("📊 Application Overview")
if 'applicant_status' not in doc_df:
    doc_df['applicant_status'] = 'In progress'  # Default if not present
col1, col2, col3 = st.columns(3)
col1.metric("Applicants In Progress", len(doc_df[doc_df['applicant_status'] == 'In progress']['applicant_id'].unique()))
col2.metric("Applicants Approved", len(doc_df[doc_df['applicant_status'] == 'Approved']['applicant_id'].unique()))
col3.metric("Applicants Rejected", len(doc_df[doc_df['applicant_status'] == 'Rejected']['applicant_id'].unique()))

st.divider()

# --- Filter section ---
st.subheader("🔍 Filter & Review Documents & Applications")
all_applicants = sorted(set(doc_df["applicant_id"].unique().tolist() + loan_app_df["applicant_id"].unique().tolist()))
applicant_filter = st.selectbox("Filter by Applicant ID", ["All"] + all_applicants, key="applicant_filter_main")
doc_type_filter = st.selectbox("Filter by Document Type", ["All"] + sorted(doc_df["predicted_classification"].unique().tolist()), key="doc_type_filter_main")
status_filter = st.selectbox("Filter by Document Status", ["All", "pending_review", "approved", "incomplete"], key="status_filter_main")

filtered_doc_df = doc_df.copy()
if applicant_filter != "All":
    filtered_doc_df = filtered_doc_df[filtered_doc_df["applicant_id"] == applicant_filter]
if status_filter != "All":
    filtered_doc_df = filtered_doc_df[filtered_doc_df["status"] == status_filter]
if doc_type_filter != "All":
    filtered_doc_df = filtered_doc_df[filtered_doc_df["predicted_classification"] == doc_type_filter]

# Add a Flagged column (True if flagged_by_ai, else False)
filtered_doc_df['Flagged'] = filtered_doc_df.get('flagged_by_ai', False)

st.subheader("📁 Applicant Documents (Filtered)")

if not filtered_doc_df.empty:
    # Show a table with basic info and flagged status
    display_cols = ["applicant_id", "file_name", "predicted_classification", "status", "upload_time", "Flagged"]
    table_df = filtered_doc_df[display_cols].reset_index(drop=True)
    st.dataframe(table_df, use_container_width=True)

    # Let user select a row by file name (or any unique field)
    doc_options = table_df["file_name"].tolist()
    selected_file = st.selectbox(
        "Select a document to review",
        options=doc_options,
        format_func=lambda x: f"{x} ({table_df.loc[table_df['file_name'] == x, 'predicted_classification'].values[0]})",
        key="select_doc_main"
    )

    # Get the full row for the selected document
    row = filtered_doc_df[filtered_doc_df["file_name"] == selected_file].iloc[0]

    st.markdown("---")
    st.subheader(f"📄 Details for {row.get('file_name', 'N/A')}")

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
        extracted = row.get("extracted_fields", {})
        # Diagnostic: Show raw keys
        st.info(f"Raw missing_fields: {missing}")
        st.info(f"Raw extracted_fields keys: {list(extracted.keys())}")
        # Helper to normalize keys: strip, lower, remove special chars
        def normalize_key(k):
            return re.sub(r'[^a-zA-Z0-9]', '', k).strip().lower()
        extracted_keys_norm = {normalize_key(k): k for k in extracted.keys()}
        actually_present = []
        actually_missing = []
        fuzzy_matches = []
        for m in missing:
            m_norm = normalize_key(m)
            # Fuzzy match: look for close matches in extracted_keys_norm
            close = difflib.get_close_matches(m_norm, extracted_keys_norm.keys(), n=1, cutoff=0.8)
            if m_norm in extracted_keys_norm:
                actually_present.append(m)
            elif close:
                fuzzy_matches.append((m, extracted_keys_norm[close[0]]))
            else:
                actually_missing.append(m)
        # Diagnostic table
        if missing:
            st.markdown("**🔎 Diagnostic: Missing vs Extracted Fields**")
            diag_data = []
            for m in missing:
                m_norm = normalize_key(m)
                match = ''
                if m_norm in extracted_keys_norm:
                    match = 'Exact match'
                else:
                    close = difflib.get_close_matches(m_norm, extracted_keys_norm.keys(), n=1, cutoff=0.8)
                    if close:
                        match = f"Fuzzy match: {extracted_keys_norm[close[0]]}"
                diag_data.append({'Missing Field': m, 'Match': match})
            st.table(pd.DataFrame(diag_data))
        # Only show error/warning for truly missing fields
        if actually_missing:
            st.error(f"Missing fields: {', '.join(actually_missing)}")
        if fuzzy_matches:
            st.info(f"Fuzzy matches found: {', '.join([f'{m} ~ {e}' for m, e in fuzzy_matches])}")
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
        with st.expander("Raw Extracted Fields (from Azure)"):
            st.table(pd.DataFrame(list(raw_extracted.items()), columns=["Raw Field Name", "Value"]))

    view_option = st.radio(
        "View Options", ["Raw Document", "Extracted Information"], key=f"view_{row.get('id', '')}_main"
    )
    if view_option == "Raw Document":
        st.markdown(f"[🗂 Open Document in New Tab]({row.get('blob_url', '#')})")
    else:
        extracted = row.get("extracted_fields", {})
        if extracted:
            st.table(pd.DataFrame(list(extracted.items()), columns=["Field", "Value"]))
        else:
            st.warning("⚠️ No extracted data available.")

    st.markdown(f"**📄 Document Type:** `{row.get('predicted_classification', 'N/A')}`")
    st.markdown(f"🤖 **AI Classification Reason:** `{row.get('reasoning', 'N/A')}`")
    # Editable fields for document status
    status_options = ["pending_review", "approved", "incomplete"]
    new_status = st.selectbox(
        "📝 Update Document Status",
        status_options,
        index=status_options.index(row.get("status", "pending_review")),
        key=f"status_{row.get('id', '')}_main"
    )
    with st.expander("💬 Officer Comments"):
        new_comment = st.text_area(
            "Comments",
            value=row.get("officer_comments", ""),
            key=f"comment_{row.get('id', '')}_main"
        )
    if st.button("💾 Save Updates", key=f"save_{row.get('id', '')}_main"):
        updated = row.copy()
        updated["status"] = new_status
        updated["officer_comments"] = new_comment
        updated["last_updated"] = datetime.utcnow().isoformat()
        container.replace_item(item=updated["id"], body=updated, partition_key=updated["applicant_id"])
        st.success("✅ Updated successfully")
else:
    st.info("No documents match your filter.")

# --- Loan Applications Overview ---
st.subheader("📝 Loan Applications Overview")
if not loan_app_df.empty:
    # Prepare summary table
    def get_loan_status(row):
        la = row.get('loan_application', {})
        return la.get('status', 'under review')
    loan_app_df['loan_status'] = loan_app_df.apply(get_loan_status, axis=1)
    summary_cols = [
        'applicant_id',
        # flatten loan_application fields for summary
    ]
    summary_data = []
    for _, row in loan_app_df.iterrows():
        la = row.get('loan_application', {})
        summary_data.append({
            'applicant_id': row.get('applicant_id', ''),
            'loan_amount': la.get('loan_amount', ''),
            'tenure_months': la.get('tenure_months', ''),
            'loan_purpose': la.get('loan_purpose', ''),
            'emi': la.get('emi', ''),
            'interest_rate': la.get('interest_rate', ''),
            'status': la.get('status', 'under review'),
            'submitted_at': la.get('submitted_at', ''),
            'email': la.get('email', '')
        })
    loan_summary_df = pd.DataFrame(summary_data)
    st.dataframe(loan_summary_df, use_container_width=True)
    # Download/export button
    csv = loan_summary_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Loan Applications as CSV",
        data=csv,
        file_name='loan_applications_summary.csv',
        mime='text/csv',
        key="download_loan_applications_main"
    )
else:
    st.info("No loan applications found.")

# --- Loan Application Section ---
if applicant_filter != "All":
    loan_app_row = loan_app_df[loan_app_df["applicant_id"] == applicant_filter]
    if not loan_app_row.empty:
        loan_app_item = loan_app_row.iloc[0]
        loan_app = loan_app_item.get("loan_application", {})
        st.markdown("---")
        st.subheader(f"📝 Loan Application for Applicant {applicant_filter}")
        st.markdown(f"**Loan Amount:** ₹{loan_app.get('loan_amount', 'N/A')}")
        st.markdown(f"**Tenure:** {loan_app.get('tenure_months', 'N/A')} months")
        st.markdown(f"**Purpose:** {loan_app.get('loan_purpose', 'N/A')}")
        st.markdown(f"**EMI:** ₹{loan_app.get('emi', 'N/A'):.2f}")
        st.markdown(f"**Interest Rate:** {loan_app.get('interest_rate', 'N/A')}% p.a.")
        st.markdown(f"**Email:** {loan_app.get('email', 'N/A')}")
        st.markdown(f"**Submitted At:** {loan_app.get('submitted_at', 'N/A')}")
        # Officer can update status
        status_options = ['under review', 'approved', 'rejected']
        current_status = loan_app.get('status', 'under review')
        new_status = st.selectbox(
            "📝 Update Loan Application Status",
            status_options,
            index=status_options.index(current_status),
            key=f"loan_status_{loan_app_item.get('id', '')}_main"
        )
        if st.button("💾 Save Loan Application Status", key=f"save_loan_status_{loan_app_item.get('id', '')}_main"):
            # Update in Cosmos
            updated_item = loan_app_item.copy()
            updated_loan_app = updated_item.get('loan_application', {})
            updated_loan_app['status'] = new_status
            updated_item['loan_application'] = updated_loan_app
            container.replace_item(item=updated_item['id'], body=updated_item, partition_key=updated_item['applicant_id'])
            st.success("✅ Loan application status updated successfully")
        with st.expander("Show All Application Fields"):
            fields = loan_app.get('fields', {})
            if fields:
                st.table(pd.DataFrame(list(fields.items()), columns=["Field", "Value"]))
            else:
                st.info("No additional fields available.")
    else:
        st.info("No loan application found for this applicant.")

st.divider()

# --- Add tabbing for dashboard and eligibility agent ---
tabs = st.tabs(["Dashboard", "Eligibility Agent (GPT-4o)"])
dashboard_tab, eligibility_tab = tabs

with dashboard_tab:
    # --- Applicant Overview ---
    st.subheader("📊 Application Overview")
    if 'applicant_status' not in doc_df:
        doc_df['applicant_status'] = 'In progress'  # Default if not present
    col1, col2, col3 = st.columns(3)
    col1.metric("Applicants In Progress", len(doc_df[doc_df['applicant_status'] == 'In progress']['applicant_id'].unique()))
    col2.metric("Applicants Approved", len(doc_df[doc_df['applicant_status'] == 'Approved']['applicant_id'].unique()))
    col3.metric("Applicants Rejected", len(doc_df[doc_df['applicant_status'] == 'Rejected']['applicant_id'].unique()))

    st.divider()

    # --- Filter section ---
    st.subheader("🔍 Filter & Review Documents & Applications")
    all_applicants = sorted(set(doc_df["applicant_id"].unique().tolist() + loan_app_df["applicant_id"].unique().tolist()))
    applicant_filter = st.selectbox("Filter by Applicant ID", ["All"] + all_applicants, key="applicant_filter_dashboard")
    doc_type_filter = st.selectbox("Filter by Document Type", ["All"] + sorted(doc_df["predicted_classification"].unique().tolist()), key="doc_type_filter_dashboard")
    status_filter = st.selectbox("Filter by Document Status", ["All", "pending_review", "approved", "incomplete"], key="status_filter_dashboard")

    filtered_doc_df = doc_df.copy()
    if applicant_filter != "All":
        filtered_doc_df = filtered_doc_df[filtered_doc_df["applicant_id"] == applicant_filter]
    if status_filter != "All":
        filtered_doc_df = filtered_doc_df[filtered_doc_df["status"] == status_filter]
    if doc_type_filter != "All":
        filtered_doc_df = filtered_doc_df[filtered_doc_df["predicted_classification"] == doc_type_filter]

    # Add a Flagged column (True if flagged_by_ai, else False)
    filtered_doc_df['Flagged'] = filtered_doc_df.get('flagged_by_ai', False)

    st.subheader("📁 Applicant Documents (Filtered)")

    if not filtered_doc_df.empty:
        # Show a table with basic info and flagged status
        display_cols = ["applicant_id", "file_name", "predicted_classification", "status", "upload_time", "Flagged"]
        table_df = filtered_doc_df[display_cols].reset_index(drop=True)
        st.dataframe(table_df, use_container_width=True)

        # Let user select a row by file name (or any unique field)
        doc_options = table_df["file_name"].tolist()
        selected_file = st.selectbox(
            "Select a document to review",
            options=doc_options,
            format_func=lambda x: f"{x} ({table_df.loc[table_df['file_name'] == x, 'predicted_classification'].values[0]})",
            key="select_doc_dashboard"
        )

        # Get the full row for the selected document
        row = filtered_doc_df[filtered_doc_df["file_name"] == selected_file].iloc[0]

        st.markdown("---")
        st.subheader(f"📄 Details for {row.get('file_name', 'N/A')}")

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
            extracted = row.get("extracted_fields", {})
            # Diagnostic: Show raw keys
            st.info(f"Raw missing_fields: {missing}")
            st.info(f"Raw extracted_fields keys: {list(extracted.keys())}")
            # Helper to normalize keys: strip, lower, remove special chars
            def normalize_key(k):
                return re.sub(r'[^a-zA-Z0-9]', '', k).strip().lower()
            extracted_keys_norm = {normalize_key(k): k for k in extracted.keys()}
            actually_present = []
            actually_missing = []
            fuzzy_matches = []
            for m in missing:
                m_norm = normalize_key(m)
                # Fuzzy match: look for close matches in extracted_keys_norm
                close = difflib.get_close_matches(m_norm, extracted_keys_norm.keys(), n=1, cutoff=0.8)
                if m_norm in extracted_keys_norm:
                    actually_present.append(m)
                elif close:
                    fuzzy_matches.append((m, extracted_keys_norm[close[0]]))
                else:
                    actually_missing.append(m)
            # Diagnostic table
            if missing:
                st.markdown("**🔎 Diagnostic: Missing vs Extracted Fields**")
                diag_data = []
                for m in missing:
                    m_norm = normalize_key(m)
                    match = ''
                    if m_norm in extracted_keys_norm:
                        match = 'Exact match'
                    else:
                        close = difflib.get_close_matches(m_norm, extracted_keys_norm.keys(), n=1, cutoff=0.8)
                        if close:
                            match = f"Fuzzy match: {extracted_keys_norm[close[0]]}"
                    diag_data.append({'Missing Field': m, 'Match': match})
                st.table(pd.DataFrame(diag_data))
            # Only show error/warning for truly missing fields
            if actually_missing:
                st.error(f"Missing fields: {', '.join(actually_missing)}")
            if fuzzy_matches:
                st.info(f"Fuzzy matches found: {', '.join([f'{m} ~ {e}' for m, e in fuzzy_matches])}")
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
            with st.expander("Raw Extracted Fields (from Azure)"):
                st.table(pd.DataFrame(list(raw_extracted.items()), columns=["Raw Field Name", "Value"]))

        view_option = st.radio(
            "View Options", ["Raw Document", "Extracted Information"], key=f"view_{row.get('id', '')}_dashboard"
        )
        if view_option == "Raw Document":
            st.markdown(f"[🗂 Open Document in New Tab]({row.get('blob_url', '#')})")
        else:
            extracted = row.get("extracted_fields", {})
            if extracted:
                st.table(pd.DataFrame(list(extracted.items()), columns=["Field", "Value"]))
            else:
                st.warning("⚠️ No extracted data available.")

        st.markdown(f"**📄 Document Type:** `{row.get('predicted_classification', 'N/A')}`")
        st.markdown(f"🤖 **AI Classification Reason:** `{row.get('reasoning', 'N/A')}`")
        # Editable fields for document status
        status_options = ["pending_review", "approved", "incomplete"]
        new_status = st.selectbox(
            "📝 Update Document Status",
            status_options,
            index=status_options.index(row.get("status", "pending_review")),
            key=f"status_{row.get('id', '')}_dashboard"
        )
        with st.expander("💬 Officer Comments"):
            new_comment = st.text_area(
                "Comments",
                value=row.get("officer_comments", ""),
                key=f"comment_{row.get('id', '')}_dashboard"
            )
        if st.button("💾 Save Updates", key=f"save_{row.get('id', '')}_dashboard"):
            updated = row.copy()
            updated["status"] = new_status
            updated["officer_comments"] = new_comment
            updated["last_updated"] = datetime.utcnow().isoformat()
            container.replace_item(item=updated["id"], body=updated, partition_key=updated["applicant_id"])
            st.success("✅ Updated successfully")
    else:
        st.info("No documents match your filter.")

    # --- Loan Applications Overview ---
    st.subheader("📝 Loan Applications Overview")
    if not loan_app_df.empty:
        # Prepare summary table
        def get_loan_status(row):
            la = row.get('loan_application', {})
            return la.get('status', 'under review')
        loan_app_df['loan_status'] = loan_app_df.apply(get_loan_status, axis=1)
        summary_cols = [
            'applicant_id',
            # flatten loan_application fields for summary
        ]
        summary_data = []
        for _, row in loan_app_df.iterrows():
            la = row.get('loan_application', {})
            summary_data.append({
                'applicant_id': row.get('applicant_id', ''),
                'loan_amount': la.get('loan_amount', ''),
                'tenure_months': la.get('tenure_months', ''),
                'loan_purpose': la.get('loan_purpose', ''),
                'emi': la.get('emi', ''),
                'interest_rate': la.get('interest_rate', ''),
                'status': la.get('status', 'under review'),
                'submitted_at': la.get('submitted_at', ''),
                'email': la.get('email', '')
            })
        loan_summary_df = pd.DataFrame(summary_data)
        st.dataframe(loan_summary_df, use_container_width=True)
        # Download/export button
        csv = loan_summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Loan Applications as CSV",
            data=csv,
            file_name='loan_applications_summary.csv',
            mime='text/csv',
            key="download_loan_applications_dashboard"
        )
    else:
        st.info("No loan applications found.")

    # --- Loan Application Section ---
    if applicant_filter != "All":
        loan_app_row = loan_app_df[loan_app_df["applicant_id"] == applicant_filter]
        if not loan_app_row.empty:
            loan_app_item = loan_app_row.iloc[0]
            loan_app = loan_app_item.get("loan_application", {})
            st.markdown("---")
            st.subheader(f"📝 Loan Application for Applicant {applicant_filter}")
            st.markdown(f"**Loan Amount:** ₹{loan_app.get('loan_amount', 'N/A')}")
            st.markdown(f"**Tenure:** {loan_app.get('tenure_months', 'N/A')} months")
            st.markdown(f"**Purpose:** {loan_app.get('loan_purpose', 'N/A')}")
            st.markdown(f"**EMI:** ₹{loan_app.get('emi', 'N/A'):.2f}")
            st.markdown(f"**Interest Rate:** {loan_app.get('interest_rate', 'N/A')}% p.a.")
            st.markdown(f"**Email:** {loan_app.get('email', 'N/A')}")
            st.markdown(f"**Submitted At:** {loan_app.get('submitted_at', 'N/A')}")
            # Officer can update status
            status_options = ['under review', 'approved', 'rejected']
            current_status = loan_app.get('status', 'under review')
            new_status = st.selectbox(
                "📝 Update Loan Application Status",
                status_options,
                index=status_options.index(current_status),
                key=f"loan_status_{loan_app_item.get('id', '')}_dashboard"
            )
            if st.button("💾 Save Loan Application Status", key=f"save_loan_status_{loan_app_item.get('id', '')}_dashboard"):
                # Update in Cosmos
                updated_item = loan_app_item.copy()
                updated_loan_app = updated_item.get('loan_application', {})
                updated_loan_app['status'] = new_status
                updated_item['loan_application'] = updated_loan_app
                container.replace_item(item=updated_item['id'], body=updated_item, partition_key=updated_item['applicant_id'])
                st.success("✅ Loan application status updated successfully")
            with st.expander("Show All Application Fields"):
                fields = loan_app.get('fields', {})
                if fields:
                    st.table(pd.DataFrame(list(fields.items()), columns=["Field", "Value"]))
                else:
                    st.info("No additional fields available.")
        else:
            st.info("No loan application found for this applicant.")

with eligibility_tab:
    st.subheader("🤖 Eligibility Agent (GPT-4o)")
    applicant_id_input = st.text_input("Applicant ID for Evaluation")

    if st.button("🔍 Run Eligibility Agent"):
        if applicant_id_input:
            import requests
            try:
                response = requests.post(
                    "http://localhost:8000/check-eligibility",
                    json={"applicant_id": applicant_id_input},
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ **Decision:** {result['decision']}")
                    st.metric("Confidence Score", result["score"])
                    st.markdown(f"[📄 View Full Report]({result['report_url']})")
                else:
                    st.error(f"❌ Eligibility agent error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"❌ Failed to contact eligibility agent: {e}")
        else:
            st.warning("Please enter an Applicant ID.")