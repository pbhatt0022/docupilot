import azure.functions as func
import logging
import os
import fitz  # PyMuPDF
import json
from io import BytesIO
from PIL import Image
import pytesseract
import tiktoken
import openai
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
load_dotenv("/Users/siddhantmahajan/Desktop/docupilot/.env")

# --------- Configuration ---------
EMBED_MODEL = "text-embedding-ada-002"
CHUNK_TOKENS = 512
CHUNK_OVERLAP = 64
encoding = tiktoken.encoding_for_model(EMBED_MODEL)

# Azure OpenAI & Search settings
EMBED_API_KEY = os.getenv("EMBED_API_KEY")
EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT")
EMBED_API_VERSION = "2023-05-15"

SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
INDEX_NAME = "rag-2"

# Create search client once
search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_API_KEY)
)

app = func.FunctionApp()

def embed_text(text: str) -> list[float]:
    openai.api_key = EMBED_API_KEY
    openai.azure_endpoint = EMBED_ENDPOINT
    openai.api_version = EMBED_API_VERSION
    response = openai.embeddings.create(input=text, model=EMBED_MODEL)
    return response.data[0].embedding

def create_metadata_prefix(applicant_id, document_type, filename):
    """Create a metadata prefix to prepend to each chunk"""
    return f"[Applicant: {applicant_id}] [Document Type: {document_type}] [File: {filename}] "

def process_and_index(text, applicant_id, document_type, filename, page_number):
    # Create metadata prefix
    metadata_prefix = create_metadata_prefix(applicant_id, document_type, filename)
    
    tokens = encoding.encode(text)
    chunk_id = 0
    docs = []
    
    for i in range(0, len(tokens), CHUNK_TOKENS - CHUNK_OVERLAP):
        chunk_tokens = tokens[i : i + CHUNK_TOKENS]
        chunk_text = encoding.decode(chunk_tokens)
        
        # Prepend metadata to chunk text
        full_chunk_text = metadata_prefix + chunk_text
        
        vector = embed_text(full_chunk_text)
        safe_filename = filename.replace(" ", "_")
        safe_filename = safe_filename.replace(".", "_")
        
        doc = {
            "chunk_id": f"{safe_filename}_p{page_number}_c{chunk_id}",
            "applicant_id": applicant_id,  # Keep as metadata field for filtering if needed
            "document_type": document_type,  # Keep as metadata field for filtering if needed
            "filename": filename,
            "page_number": page_number,
            "chunk": full_chunk_text,  # This now contains metadata + content
            "text_vector": vector
        }
        docs.append(doc)
        chunk_id += 1
    
    if docs:
        result = search_client.upload_documents(documents=docs)
        logging.info(f"Indexed {len(result)} chunks for {filename} page {page_number}")

@app.blob_trigger(
    arg_name="myblob",
    path="loan-documents/{applicant_id}/{document_type}/{filename}",
    connection="AzureWebJobsStorage"
)
def PdfBlobTrigger(myblob: func.InputStream):
    logging.info(f"Triggered by blob: {myblob.name}")
    try:
        data = myblob.read()
        
        # Extract info from blob path
        path_parts = myblob.name.split('/')
        applicant_id = path_parts[1]
        document_type = path_parts[2]
        filename = path_parts[3]
        
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if ext == ".pdf":
            doc = fitz.open(stream=BytesIO(data), filetype="pdf")
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text().strip()
                if text:
                    process_and_index(text, applicant_id, document_type, filename, page_num)
        elif ext in [".jpg", ".jpeg", ".png"]:
            img = Image.open(BytesIO(data))
            text = pytesseract.image_to_string(img).strip()
            if text:
                process_and_index(text, applicant_id, document_type, filename, 1)
        else:
            logging.warning(f"Skipped unsupported file: {myblob.name}")
        
        logging.info(f"Finished indexing: {myblob.name}")
    except Exception as e:
        logging.error(f"Error processing {myblob.name}: {e}")