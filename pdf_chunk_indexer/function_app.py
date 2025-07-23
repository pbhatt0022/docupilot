import logging
import os
import azure.functions as func
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import fitz  # PyMuPDF
import tempfile

# Environment variables (set in local.settings.json or Azure portal)
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
SEARCH_INDEX = os.getenv("SEARCH_INDEX")

# Initialize SearchClient
search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=AzureKeyCredential(SEARCH_API_KEY)
)

def extract_text_from_pdf(pdf_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        doc = fitz.open(tmp.name)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
    os.unlink(tmp.name)
    return text

def chunk_text(text, chunk_size=1000):
    # Simple chunking logic
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def index_chunks(applicant_id, document_type, file_name, chunks):
    docs = []
    for i, chunk in enumerate(chunks):
        docs.append({
            "id": f"{applicant_id}_{document_type}_{file_name}_{i}",
            "applicant_id": applicant_id,
            "document_type": document_type,
            "file_name": file_name,
            "content": chunk
        })
    result = search_client.upload_documents(documents=docs)
    return result

def main(blob: func.InputStream):
    """
    Azure Function Blob Trigger
    Triggered when a new blob is uploaded to the 'loan-documents' container.
    Blob path: loan-documents/{applicant_id}/{document_type}/{filename}
    """
    logging.info(f"Processing blob: {blob.name}, Size: {blob.length} bytes")
    # Parse blob path: loan-documents/{applicant_id}/{document_type}/{filename}
    parts = blob.name.split('/')
    if len(parts) < 3:
        logging.error("Blob path does not match expected format.")
        return

    applicant_id, document_type, file_name = parts[-3], parts[-2], parts[-1]
    pdf_bytes = blob.read()
    text = extract_text_from_pdf(pdf_bytes)
    chunks = chunk_text(text)
    index_chunks(applicant_id, document_type, file_name, chunks)
    logging.info(f"Indexed {len(chunks)} chunks for {file_name}")
