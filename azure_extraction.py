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
    "Offer Letter": ["EmployeeName", "EmployerName", "DateOfJoining", "Position"],
    "Cancelled Cheque": ["AccountNumber", "IFSC", "BankName"],
    "Income Tax Return": ["AssessmentYear", "PAN", "GrossIncome"],
    "Consent Form": ["ApplicantName", "ConsentType", "Date"],
    "FATCA Declaration": ["ApplicantName", "NRIStatus", "DeclarationDate"],
    "Employment Certificate": ["EmployeeName", "EmployerName", "EmploymentStatus", "IssueDate"],
    "Employee ID": ["EmployeeName", "EmployerName", "EmployeeIDNumber"],
    "Increment Letter": ["EmployeeName", "EmployerName", "IncrementDate", "NewSalary"],
    "Appraisal Letter": ["EmployeeName", "EmployerName", "AppraisalPeriod", "AppraisalResult"],
    "Proof of Residence": ["ApplicantName", "Address", "DocumentType"],
    "Photograph": ["ApplicantName", "Photo"],
    "Co-Applicant Document": ["CoApplicantName", "Relationship", "DocumentType"],
    "Credit Report": ["ApplicantName", "CreditScore", "ReportDate"],
    "Insurance Proof": ["ApplicantName", "PolicyNumber", "Insurer", "SumAssured"],
    "Digital Consent": ["ApplicantName", "ConsentType", "Date"],
    "Video KYC": ["ApplicantName", "VideoLink", "CaptureDate"],
}

# Map document types to Form Recognizer models
MODEL_MAP = {
    "Aadhaar Card": "prebuilt-idDocument",
    "PAN Card": "prebuilt-idDocument",
    "Passport": "prebuilt-idDocument",
    "VoterID": "prebuilt-idDocument",
    "Driving License": "prebuilt-idDocument",
    "Bank Statement": "prebuilt-bankStatement",
    "Salary Slip": "prebuilt-document",
    "Loan Application Form": "prebuilt-document",
    "Form 16": "prebuilt-document",
    "Offer Letter": "prebuilt-document",
    "Cancelled Cheque": "prebuilt-document",
    "Income Tax Return": "prebuilt-document",
    "Consent Form": "prebuilt-document",
    "FATCA Declaration": "prebuilt-document",
    "Employment Certificate": "prebuilt-document",
    "Employee ID": "prebuilt-document",
    "Increment Letter": "prebuilt-document",
    "Appraisal Letter": "prebuilt-document",
    "Proof of Residence": "prebuilt-document",
    "Photograph": "prebuilt-document",
    "Co-Applicant Document": "prebuilt-document",
    "Credit Report": "prebuilt-document",
    "Insurance Proof": "prebuilt-document",
    "Digital Consent": "prebuilt-document",
    "Video KYC": "prebuilt-document",
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
    "Offer Letter": {
        "Employee Name": "EmployeeName",
        "Employer Name": "EmployerName",
        "Date of Joining": "DateOfJoining",
        "Position": "Position"
    },
    "Cancelled Cheque": {
        "Account Number": "AccountNumber",
        "IFSC Code": "IFSC",
        "Bank Name": "BankName"
    },
    "Income Tax Return": {
        "Assessment Year": "AssessmentYear",
        "PAN": "PAN",
        "Gross Income": "GrossIncome"
    },
    "Consent Form": {
        "Applicant Name": "ApplicantName",
        "Consent Type": "ConsentType",
        "Date": "Date"
    },
    "FATCA Declaration": {
        "Applicant Name": "ApplicantName",
        "NRI Status": "NRIStatus",
        "Declaration Date": "DeclarationDate"
    },
    "Employment Certificate": {
        "Employee Name": "EmployeeName",
        "Employer Name": "EmployerName",
        "Employment Status": "EmploymentStatus",
        "Issue Date": "IssueDate"
    },
    "Employee ID": {
        "Employee Name": "EmployeeName",
        "Employer Name": "EmployerName",
        "Employee ID Number": "EmployeeIDNumber"
    },
    "Increment Letter": {
        "Employee Name": "EmployeeName",
        "Employer Name": "EmployerName",
        "Increment Date": "IncrementDate",
        "New Salary": "NewSalary"
    },
    "Appraisal Letter": {
        "Employee Name": "EmployeeName",
        "Employer Name": "EmployerName",
        "Appraisal Period": "AppraisalPeriod",
        "Appraisal Result": "AppraisalResult"
    },
    "Proof of Residence": {
        "Applicant Name": "ApplicantName",
        "Address": "Address",
        "Document Type": "DocumentType"
    },
    "Photograph": {
        "Applicant Name": "ApplicantName",
        "Photo": "Photo"
    },
    "Co-Applicant Document": {
        "Co-Applicant Name": "CoApplicantName",
        "Relationship": "Relationship",
        "Document Type": "DocumentType"
    },
    "Credit Report": {
        "Applicant Name": "ApplicantName",
        "Credit Score": "CreditScore",
        "CIBIL Score": "CreditScore",
        "Report Date": "ReportDate"
    },
    "Insurance Proof": {
        "Applicant Name": "ApplicantName",
        "Policy Number": "PolicyNumber",
        "Insurer": "Insurer",
        "Sum Assured": "SumAssured"
    },
    "Digital Consent": {
        "Applicant Name": "ApplicantName",
        "Consent Type": "ConsentType",
        "Date": "Date"
    },
    "Video KYC": {
        "Applicant Name": "ApplicantName",
        "Video Link": "VideoLink",
        "Capture Date": "CaptureDate"
    },
}

def normalize_field_name(name):
    return ''.join(name.lower().split())

def to_json_serializable(val):
    # Recursively convert DocumentField, date, datetime, and lists/dicts to JSON-serializable values
    try:
        from azure.ai.formrecognizer import DocumentField
    except ImportError:
        DocumentField = None
    import datetime
    if DocumentField and isinstance(val, DocumentField):
        return to_json_serializable(val.value)
    elif isinstance(val, dict):
        return {k: to_json_serializable(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [to_json_serializable(v) for v in val]
    elif isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    else:
        return val

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
    raw_extracted = {}
    missing_fields = []
    is_complete = True

    if result.documents:
        for document in result.documents:
            for name, field in document.fields.items():
                raw_extracted[name] = to_json_serializable(field.value)
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
                extracted[canonical_name] = to_json_serializable(field.value)

        # Debug print statements
        print(f"Starting extraction for {file_path}, doc_type={doc_type}")
        print("Raw extracted fields from Azure model:", raw_extracted)
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

    return extracted, is_complete, missing_fields, flagged_by_ai, flagged_reason, raw_extracted 