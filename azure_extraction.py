import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from typing import Tuple, Dict, List
from difflib import get_close_matches
from dotenv import load_dotenv
load_dotenv()

# Initialize Form Recognizer client
endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
key = os.getenv("FORM_RECOGNIZER_KEY")
fr_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

# Define must-have fields for each doc type
MUST_HAVE_FIELDS = {
    # "Aadhaar Card": ["FirstName", "LastName", "DateOfBirth", "DocumentNumber", "Address"],  # commented out
    "PAN Card": ["FirstName", "LastName", "DateOfBirth", "DocumentNumber"],
    "Passport": ["FirstName", "LastName", "DateOfBirth", "DocumentNumber", "ExpiryDate"],
    # "VoterID": ["FirstName", "LastName", "DocumentNumber", "Address"],  # commented out
    # "Driving License": ["FirstName", "LastName", "DateOfBirth", "DocumentNumber", "ExpiryDate"],  # commented out
    "Bank Statement": ["AccountNumber", "IFSC", "BankName"],
    # "Salary Slip": ["EmployeeName", "EmployerName", "NetSalary", "Month", "Year"],  # commented out
    # "Loan Application Form": ["ApplicantName", "LoanAmount", "ApplicationDate"],  # commented out
    # "Form 16": ["EmployeeName", "EmployerName", "AssessmentYear", "GrossSalary", "TaxDeducted"],  # commented out
    # "Offer Letter": ["EmployeeName", "EmployerName", "DateOfJoining", "Position"],  # commented out
    # "Cancelled Cheque": ["AccountNumber", "IFSC", "BankName"],  # commented out
    "Income Tax Return": ["AssessmentYear", "PAN", "GrossIncome"],
    # "Consent Form": ["ApplicantName", "ConsentType", "Date"],  # commented out
    # "FATCA Declaration": ["ApplicantName", "NRIStatus", "DeclarationDate"],  # commented out
    # "Employment Certificate": ["EmployeeName", "EmployerName", "EmploymentStatus", "IssueDate"],  # commented out
    # "Employee ID": ["EmployeeName", "EmployerName", "EmployeeIDNumber"],  # commented out
    # "Increment Letter": ["EmployeeName", "EmployerName", "IncrementDate", "NewSalary"],  # commented out
    # "Appraisal Letter": ["EmployeeName", "EmployerName", "AppraisalPeriod", "AppraisalResult"],  # commented out
    # "Proof of Residence": ["ApplicantName", "Address", "DocumentType"],  # commented out
    # "Photograph": ["ApplicantName", "Photo"],  # commented out
    # "Co-Applicant Document": ["CoApplicantName", "Relationship", "DocumentType"],  # commented out
    "Credit Report": ["ApplicantName", "CreditScore", "ReportDate"],
    # "Insurance Proof": ["ApplicantName", "PolicyNumber", "Insurer", "SumAssured"],  # commented out
    # "Digital Consent": ["ApplicantName", "ConsentType", "Date"],  # commented out
    # "Video KYC": ["ApplicantName", "VideoLink", "CaptureDate"],  # commented out
}

# Map document types to Form Recognizer models
MODEL_MAP = {
    # "Aadhaar Card": "prebuilt-idDocument",  # commented out
    "PAN Card": "prebuilt-idDocument",
    "Passport": "prebuilt-idDocument",
    # "VoterID": "prebuilt-idDocument",  # commented out
    # "Driving License": "prebuilt-idDocument",  # commented out
    "Bank Statement": "prebuilt-document",
    # "Salary Slip": "prebuilt-document",  # commented out
    # "Loan Application Form": "prebuilt-document",  # commented out
    # "Form 16": "prebuilt-document",  # commented out
    # "Offer Letter": "prebuilt-document",  # commented out
    # "Cancelled Cheque": "prebuilt-document",  # commented out
    "Income Tax Return": "prebuilt-document",
    # "Consent Form": "prebuilt-document",  # commented out
    # "FATCA Declaration": "prebuilt-document",  # commented out
    # "Employment Certificate": "prebuilt-document",  # commented out
    # "Employee ID": "prebuilt-document",  # commented out
    # "Increment Letter": "prebuilt-document",  # commented out
    # "Appraisal Letter": "prebuilt-document",  # commented out
    # "Proof of Residence": "prebuilt-document",  # commented out
    # "Photograph": "prebuilt-document",  # commented out
    # "Co-Applicant Document": "prebuilt-document",  # commented out
    "Credit Report": "prebuilt-document",
    # "Insurance Proof": "prebuilt-document",  # commented out
    # "Digital Consent": "prebuilt-document",  # commented out
    # "Video KYC": "prebuilt-document",  # commented out
}

# Add a mapping for common field name variations for all document types
FIELD_NAME_MAP = {
    # "Aadhaar Card": {
    #     "First Name": "FirstName",
    #     "Last Name": "LastName",
    #     "DOB": "DateOfBirth",
    #     "Aadhaar Number": "DocumentNumber",
    #     "Address": "Address"
    # },  # commented out
    "PAN Card": {
        "First Name": "FirstName",
        "Last Name": "LastName",
        "Date of Birth": "DateOfBirth",
        "DOB": "DateOfBirth",
        "P A N": "PAN",
        "Permanent Account Number": "PAN"
    },
    "Passport": {
        "First Name": "FirstName",
        "Given Name": "FirstName",
        "Given name": "FirstName",
        "GivenNames": "FirstName",
        "Name": "FirstName",
        "Last Name": "LastName",
        "Surname": "LastName",
        "Date of Birth": "DateOfBirth",
        "DOB": "DateOfBirth",
        "Passport Number": "DocumentNumber",
        "Expiry": "ExpiryDate",
        "DateOfExpiration": "ExpiryDate"
    },
    # "VoterID": {
    #     "First Name": "FirstName",
    #     "Last Name": "LastName",
    #     "Voter ID": "DocumentNumber",
    #     "Address": "Address"
    # },  # commented out
    # "Driving License": {
    #     "First Name": "FirstName",
    #     "Last Name": "LastName",
    #     "DOB": "DateOfBirth",
    #     "License Number": "DocumentNumber",
    #     "Expiry": "ExpiryDate"
    # },  # commented out
    "Bank Statement": {
        "Account Number": "AccountNumber",
        "IFSC Code": "IFSC",
        "Bank Name": "BankName"
    },
    # "Salary Slip": {
    #     "Employee Name": "EmployeeName",
    #     "Employer Name": "EmployerName",
    #     "Net Salary": "NetSalary",
    #     "Month": "Month",
    #     "Year": "Year"
    # },  # commented out
    # "Loan Application Form": {
    #     "Applicant Name": "ApplicantName",
    #     "Loan Amount": "LoanAmount",
    #     "Application Date": "ApplicationDate"
    # },  # commented out
    # "Form 16": {
    #     "Employee Name": "EmployeeName",
    #     "Employer Name": "EmployerName",
    #     "Assessment Year": "AssessmentYear",
    #     "Gross Salary": "GrossSalary",
    #     "Tax Deducted": "TaxDeducted"
    # },  # commented out
    # "Offer Letter": {
    #     "Employee Name": "EmployeeName",
    #     "Employer Name": "EmployerName",
    #     "Date of Joining": "DateOfJoining",
    #     "Position": "Position"
    # },  # commented out
    # "Cancelled Cheque": {
    #     "Account Number": "AccountNumber",
    #     "IFSC Code": "IFSC",
    #     "Bank Name": "BankName"
    # },  # commented out
    "Income Tax Return": {
        "Assessment Year": "AssessmentYear",
        "PAN": "PAN",
        "Gross Income": "GrossIncome",
        "Gross Total Income": "GrossIncome"        
    },
    # "Consent Form": {
    #     "Applicant Name": "ApplicantName",
    #     "Consent Type": "ConsentType",
    #     "Date": "Date"
    # },  # commented out
    # "FATCA Declaration": {
    #     "Applicant Name": "ApplicantName",
    #     "NRI Status": "NRIStatus",
    #     "Declaration Date": "DeclarationDate"
    # },  # commented out
    # "Employment Certificate": {
    #     "Employee Name": "EmployeeName",
    #     "Employer Name": "EmployerName",
    #     "Employment Status": "EmploymentStatus",
    #     "Issue Date": "IssueDate"
    # },  # commented out
    # "Employee ID": {
    #     "Employee Name": "EmployeeName",
    #     "Employer Name": "EmployerName",
    #     "Employee ID Number": "EmployeeIDNumber"
    # },  # commented out
    # "Increment Letter": {
    #     "Employee Name": "EmployeeName",
    #     "Employer Name": "EmployerName",
    #     "Increment Date": "IncrementDate",
    #     "New Salary": "NewSalary"
    # },  # commented out
    # "Appraisal Letter": {
    #     "Employee Name": "EmployeeName",
    #     "Employer Name": "EmployerName",
    #     "Appraisal Period": "AppraisalPeriod",
    #     "Appraisal Result": "AppraisalResult"
    # },  # commented out
    # "Proof of Residence": {
    #     "Applicant Name": "ApplicantName",
    #     "Address": "Address",
    #     "Document Type": "DocumentType"
    # },  # commented out
    # "Photograph": {
    #     "Applicant Name": "ApplicantName",
    #     "Photo": "Photo"
    # },  # commented out
    # "Co-Applicant Document": {
    #     "Co-Applicant Name": "CoApplicantName",
    #     "Relationship": "Relationship",
    #     "Document Type": "DocumentType"
    # },  # commented out
    "Credit Report": {
        "Applicant Name": "ApplicantName",
        "Credit Score": "CreditScore",
        "CIBIL Score": "CreditScore",
        "Report Date": "ReportDate"
    },
    # "Insurance Proof": {
    #     "Applicant Name": "ApplicantName",
    #     "Policy Number": "PolicyNumber",
    #     "Insurer": "Insurer",
    #     "Sum Assured": "SumAssured"
    # },  # commented out
    # "Digital Consent": {
    #     "Applicant Name": "ApplicantName",
    #     "Consent Type": "ConsentType",
    #     "Date": "Date"
    # },  # commented out
    # "Video KYC": {
    #     "Applicant Name": "ApplicantName",
    #     "Video Link": "VideoLink",
    #     "Capture Date": "CaptureDate"
    # },  # commented out
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

def extract_bank_fields_from_document(result):
    import re
    account_number = None
    ifsc = None
    bank_name = None

    # 1. Search key-value pairs
    for kv in getattr(result, "key_value_pairs", []):
        key = kv.key.content.lower().replace(" ", "")
        value = kv.value.content if kv.value else ""
        if "accountnumber" in key or "a/cno" in key or "acno" in key:
            account_number = value
        elif "ifsc" in key:
            ifsc = value
        elif "bankname" in key:
            bank_name = value

    # 2. Search tables
    for table in getattr(result, "tables", []):
        for cell in table.cells:
            cell_text = cell.content.lower()
            if "account number" in cell_text or "a/c no" in cell_text:
                row = cell.row_index
                col = cell.column_index
                for c in table.cells:
                    if c.row_index == row and c.column_index == col + 1:
                        account_number = c.content
            if "ifsc" in cell_text:
                row = cell.row_index
                col = cell.column_index
                for c in table.cells:
                    if c.row_index == row and c.column_index == col + 1:
                        ifsc = c.content
            if "bank name" in cell_text:
                row = cell.row_index
                col = cell.column_index
                for c in table.cells:
                    if c.row_index == row and c.column_index == col + 1:
                        bank_name = c.content

    # 3. Fallback: Search raw text with regex
    full_text = ""
    for page in getattr(result, "pages", []):
        for line in page.lines:
            full_text += line.content + "\n"

    if not account_number:
        match = re.search(r"(Account Number|A/C No\.?|A\/C No\.?):?\s*([A-Za-z0-9\-]+)", full_text, re.IGNORECASE)
        if match:
            account_number = match.group(2)
    if not ifsc:
        match = re.search(r"IFSC\s*[:\-]?\s*([A-Za-z0-9]+)", full_text, re.IGNORECASE)
        if match:
            ifsc = match.group(1)
    if not bank_name:
        match = re.search(r"Bank Name\s*[:\-]?\s*([A-Za-z0-9\s]+)", full_text, re.IGNORECASE)
        if match:
            bank_name = match.group(1).strip()

    return {
        "AccountNumber": account_number,
        "IFSC": ifsc,
        "BankName": bank_name
    }

def extract_itr_fields_from_document(result):
    import re
    assessment_year = None
    pan = None
    gross_income = None
    full_text = ""
    for page in getattr(result, "pages", []):
        for line in page.lines:
            full_text += line.content + "\n"
    match = re.search(r"Assessment Year\s*[:\-]?\s*([0-9\-]+)", full_text, re.IGNORECASE)
    if match:
        assessment_year = match.group(1)
    match = re.search(r"PAN\s*[:\-]?\s*([A-Z0-9]+)", full_text, re.IGNORECASE)
    if match:
        pan = match.group(1)
    match = re.search(r"Gross Income\s*[:\-]?\s*([0-9,]+)", full_text, re.IGNORECASE)
    if match:
        gross_income = match.group(1)
    return {
        "AssessmentYear": assessment_year,
        "PAN": pan,
        "GrossIncome": gross_income
    }

def extract_credit_report_fields_from_document(result):
    import re
    applicant_name = None
    credit_score = None
    report_date = None
    full_text = ""
    for page in getattr(result, "pages", []):
        for line in page.lines:
            full_text += line.content + "\n"
    # For Name
    match = re.search(r"(Applicant Name|Name)\s*[:-]?\s*([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if match:
        applicant_name = match.group(2).strip()

    # For CIBIL Score and date
    match = re.search(r"(Credit Score|CIBIL Score)\s*[:-]?\s*([0-9]+)(?:\s*\(As of ([^)]+)\))?", full_text, re.IGNORECASE)
    if match:
        credit_score = match.group(2)
        report_date = match.group(3) if match.group(3) else None
    return {
        "ApplicantName": applicant_name,
        "CreditScore": credit_score,
        "ReportDate": report_date
    }

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

        print(f"Starting extraction for {file_path}, doc_type={doc_type}")
        print("Raw extracted fields from Azure model:", raw_extracted)
        print("Final mapped/normalized extracted fields (before post-processing):", extracted)

        # If Bank Statement, enhance extraction with heuristics
        if doc_type == "Bank Statement":
            bank_fields = extract_bank_fields_from_document(result)
            for k, v in bank_fields.items():
                if v:
                    extracted[k] = v
        # If Income Tax Return, enhance extraction with heuristics
        if doc_type == "Income Tax Return":
            itr_fields = extract_itr_fields_from_document(result)
            for k, v in itr_fields.items():
                if v:
                    extracted[k] = v
        # If Credit Report, enhance extraction with heuristics
        if doc_type == "Credit Report":
            cr_fields = extract_credit_report_fields_from_document(result)
            for k, v in cr_fields.items():
                if v:
                    extracted[k] = v

        print("Final mapped/normalized extracted fields (after post-processing):", extracted)

        # Generalized fallback: regex search for missing must-have fields
        full_text = ""
        for page in getattr(result, "pages", []):
            for line in page.lines:
                full_text += line.content + "\n"
        lines = [l.strip() for l in full_text.splitlines()]
        for must in must_have:
            if not extracted.get(must):
                label_variations = [k for k, v in field_map.items() if v == must]
                found = False
                # Try regex first
                for label in label_variations:
                    import re
                    pattern = rf"{label}\s*[:\-]?\s*([A-Za-z0-9 ,./]+)"
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        extracted[must] = match.group(1).strip()
                        found = True
                        break
                # If not found, try line-based extraction
                if not found:
                    for i, line in enumerate(lines):
                        for label in label_variations:
                            if label.lower() in line.lower():
                                # Return the next non-empty line as the value
                                for j in range(i+1, len(lines)):
                                    value = lines[j].strip()
                                    if value:
                                        extracted[must] = value
                                        found = True
                                        break
                        if found:
                            break

        # Check must-have fields (using normalization)
        for must in must_have:
            if not extracted.get(must):
                missing_fields.append(must)
                is_complete = False
    else:
        # No documents found, mark all must-have fields as missing
        missing_fields = must_have
        is_complete = False

        # Always run post-processing for these types
        if doc_type == "Bank Statement":
            bank_fields = extract_bank_fields_from_document(result)
            for k, v in bank_fields.items():
                if v:
                    extracted[k] = v
        if doc_type == "Income Tax Return":
            itr_fields = extract_itr_fields_from_document(result)
            for k, v in itr_fields.items():
                if v:
                    extracted[k] = v
        if doc_type == "Credit Report":
            cr_fields = extract_credit_report_fields_from_document(result)
            for k, v in cr_fields.items():
                if v:
                    extracted[k] = v

        # Optionally, store the full raw text for debugging
        full_text = ""
        for page in getattr(result, "pages", []):
            for line in page.lines:
                full_text += line.content + "\n"
        if full_text:
            raw_extracted["full_text"] = full_text
        lines = [l.strip() for l in full_text.splitlines()]
        # Generalized fallback: regex search for missing must-have fields
        for must in must_have:
            if not extracted.get(must):
                label_variations = [k for k, v in field_map.items() if v == must]
                found = False
                for label in label_variations:
                    import re
                    pattern = rf"{label}\s*[:\-]?\s*([A-Za-z0-9 ,./]+)"
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        extracted[must] = match.group(1).strip()
                        found = True
                        break
                if not found:
                    for i, line in enumerate(lines):
                        for label in label_variations:
                            if label.lower() in line.lower():
                                for j in range(i+1, len(lines)):
                                    value = lines[j].strip()
                                    if value:
                                        extracted[must] = value
                                        found = True
                                        break
                        if found:
                            break

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

def is_probable_name(line):
    # Heuristic: two or more uppercase words, not a known label
    import re
    known_labels = {"INDIAN", "Nationality", "Sex", "Date of expiry", "Place of birth", "Place of issue"}
    if line.strip() in known_labels:
        return False
    # Match two or more uppercase words (allowing spaces)
    return bool(re.match(r"^[A-Z]+( [A-Z]+)+$", line.strip()))

def extract_field_from_lines(label_variations, lines):
    for i, line in enumerate(lines):
        for label in label_variations:
            if label.lower() in line.lower():
                # Search next few lines for a probable name
                for j in range(i+1, min(i+5, len(lines))):
                    value = lines[j].strip()
                    if is_probable_name(value):
                        return value
    return None 