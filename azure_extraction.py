import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from typing import Tuple, Dict, List
from difflib import get_close_matches

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
    "Form 16": "prebuilt-document",
    # Add more as needed
}

# Add a mapping for common field name variations for all document types
FIELD_NAME_MAP = {
    "Aadhaar Card": {
        "First Name": "FirstName",
        "Last Name": "LastName",
        "DOB": "DateOfBirth",
        "Aadhaar Number": "DocumentNumber",
        "Address": "Address"
    },
    "PAN Card": {
        "First Name": "FirstName",
        "Last Name": "LastName",
        "Date of Birth": "DateOfBirth",
        "PAN": "DocumentNumber"
    },
    "Passport": {
        "First Name": "FirstName",
        "Last Name": "LastName",
        "Date of Birth": "DateOfBirth",
        "Passport Number": "DocumentNumber",
        "Expiry": "ExpiryDate"
    },
    "VoterID": {
        "First Name": "FirstName",
        "Last Name": "LastName",
        "Voter ID": "DocumentNumber",
        "Address": "Address"
    },
    "Driving License": {
        "First Name": "FirstName",
        "Last Name": "LastName",
        "DOB": "DateOfBirth",
        "License Number": "DocumentNumber",
        "Expiry": "ExpiryDate"
    },
    "Bank Statement": {
        "Account Number": "AccountNumber",
        "IFSC Code": "IFSC",
        "Bank Name": "BankName"
    },
    "Salary Slip": {
        "Employee Name": "EmployeeName",
        "Employer Name": "EmployerName",
        "Net Salary": "NetSalary",
        "Month": "Month",
        "Year": "Year"
    },
    "Loan Application Form": {
        "Applicant Name": "ApplicantName",
        "Loan Amount": "LoanAmount",
        "Application Date": "ApplicationDate"
    },
    "Form 16": {
        "Employee Name": "EmployeeName",
        "Employer Name": "EmployerName",
        "Assessment Year": "AssessmentYear",
        "Gross Salary": "GrossSalary",
        "Tax Deducted": "TaxDeducted"
    },
    # Add more as needed
}

def normalize_field_name(name):
    return ''.join(name.lower().split())

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
    field_map = FIELD_NAME_MAP.get(doc_type, {})
    must_have_normalized = [normalize_field_name(f) for f in must_have]

    with open(file_path, "rb") as f:
        poller = fr_client.begin_analyze_document(model, document=f)
        result = poller.result()

    extracted = {}
    missing_fields = []
    is_complete = True

    if result.documents:
        for document in result.documents:
            for name, field in document.fields.items():
                # Normalize and map field names
                norm_name = normalize_field_name(name)
                # Try direct mapping from model output
                canonical_name = field_map.get(name)
                if not canonical_name:
                    # Try normalized mapping
                    for k, v in field_map.items():
                        if normalize_field_name(k) == norm_name:
                            canonical_name = v
                            break
                if not canonical_name:
                    # Try fuzzy match with must_have fields
                    match = get_close_matches(norm_name, must_have_normalized, n=1, cutoff=0.8)
                    if match:
                        idx = must_have_normalized.index(match[0])
                        canonical_name = must_have[idx]
                if not canonical_name:
                    # Fallback to normalized name if nothing matches
                    canonical_name = name.replace(" ", "")
                extracted[canonical_name] = field.value

        # Debug print statements
        print("Raw extracted fields from Azure model:", [(name, field.value) for document in result.documents for name, field in document.fields.items()])
        print("Final mapped/normalized extracted fields:", extracted)

        # Check must-have fields (using normalization)
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