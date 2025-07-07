import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from typing import Tuple, Dict, List

# Initialize Form Recognizer client
endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
key = os.getenv("FORM_RECOGNIZER_KEY")
fr_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

# Define must-have fields for each doc type
MUST_HAVE_FIELDS = {
    "Aadhaar Card": ["FirstName", "LastName", "DateOfBirth", "DocumentNumber", "Address"],
    "PAN Card": ["FirstName", "LastName", "DateOfBirth", "DocumentNumber"],
    "Passport": ["FirstName", "LastName", "DateOfBirth", "DocumentNumber", "ExpiryDate"],
    "VoterID": ["FirstName", "LastName", "DocumentNumber", "Address"],
    "Driving License": ["FirstName", "LastName", "DateOfBirth", "DocumentNumber", "ExpiryDate"],
    "Bank Statement": ["AccountNumber", "IFSC", "BankName"],
    "Salary Slip": ["EmployeeName", "EmployerName", "NetSalary", "Month", "Year"],
    "Loan Application Form": ["ApplicantName", "LoanAmount", "ApplicationDate"],
    "Form 16": ["EmployeeName", "EmployerName", "AssessmentYear", "GrossSalary", "TaxDeducted"],
    # Add more as needed
}

# Map document types to Form Recognizer models
MODEL_MAP = {
    "Aadhaar Card": "prebuilt-idDocument",
    "PAN Card": "prebuilt-idDocument",
    "Passport": "prebuilt-idDocument",
    "VoterID": "prebuilt-idDocument",
    "Driving License": "prebuilt-idDocument",
    "Bank Statement": "prebuilt-bankStatement",
    # For custom models, use the model ID. For now, fallback to prebuilt-document.
    "Salary Slip": "prebuilt-document",
    "Loan Application Form": "prebuilt-document",
    # Add more as needed
}

def extract_text_from_blob_url(blob_url: str) -> str:
    """
    Extracts raw text from a document in Azure Blob Storage using the prebuilt-document model.
    """
    try:
        poller = fr_client.begin_analyze_document_from_url(
            model_id="prebuilt-document",
            document_url=blob_url
        )
        result = poller.result()

        full_text = ""
        for page in result.pages:
            for line in page.lines:
                full_text += line.content + "\n"
        return full_text.strip()
    except Exception as e:
        print(f"OCR extraction failed: {e}")
        return ""

def extract_fields_with_model(file_path: str, doc_type: str):
    """
    Extracts structured fields from a document using the appropriate model based on doc_type.
    Returns a tuple: (extracted_fields_dict, is_complete_bool, missing_fields_list, flagged_by_ai_bool, flagged_reason_str)
    """
    model = MODEL_MAP.get(doc_type, "prebuilt-document")
    must_have = MUST_HAVE_FIELDS.get(doc_type, [])

    with open(file_path, "rb") as f:
        poller = fr_client.begin_analyze_document(model, document=f)
        result = poller.result()

    extracted = {}
    missing_fields = []
    is_complete = True

    if result.documents:
        for document in result.documents:
            for name, field in document.fields.items():
                extracted[name] = field.value

        # Check must-have fields
        for must in must_have:
            if not extracted.get(must):
                missing_fields.append(must)
                is_complete = False
    else:
        # No documents found, mark all must-have fields as missing
        missing_fields = must_have
        is_complete = False

    flagged_by_ai = False
    flagged_reason = ""
    if missing_fields:
        flagged_by_ai = True
        flagged_reason = f"Missing required fields: {', '.join(missing_fields)}"
    elif not extracted and must_have:
        flagged_by_ai = True
        flagged_reason = "No fields could be extracted from the document."
    elif doc_type == "Others":
        flagged_by_ai = True
        flagged_reason = "Document type is unrecognized. Please review manually."
    elif flagged_by_ai:
        flagged_reason = "Flagged by AI for further review. Please check the document."
    else:
        flagged_by_ai = False
        flagged_reason = "All required fields are present. No issues detected by AI."

    return extracted, is_complete, missing_fields, flagged_by_ai, flagged_reason 