import json
from openai import OpenAI
import os

# For GitHub-hosted models like gpt-4o
OPENAI_ENDPOINT = "https://models.github.ai/inference"
OPENAI_MODEL = "openai/gpt-4o"
OPENAI_TOKEN = os.getenv("GITHUB_TOKEN")

client = OpenAI(
    base_url=OPENAI_ENDPOINT,
    api_key=OPENAI_TOKEN,
)

def classify_document(text: str) -> dict:
    system_message = (
        "You are a document classification expert helping a bank process loan applications. "
        "Always respond ONLY in valid JSON using the allowed document types."
    )

    user_prompt = f"""
You must classify the following document into one of these types:
- Aadhaar Card
- PAN Card
- Passport
- VoterID
- Driving License
- Salary Slip
- Form 16
- Income Tax Return
- Bank Statement
- Offer Letter
- Employment Certificate
- Employee ID
- Increment Letter
- Appraisal Letter
- Cancelled Cheque
- Loan Application Form
- Consent Form
- FATCA Declaration
- Proof of Residence
- Photograph
- Co-Applicant Document
- Credit Report
- Insurance Proof
- Digital Consent
- Video KYC
- Others

Instructions:
- Only choose one from the above types for "document_type".
- If uncertain, choose "Others".
- Provide a concise, factual reason for your classification.
- Respond ONLY in this JSON format:
{{
  "document_type": "...",
  "reason": "..."
}}

--- FEW-SHOT EXAMPLES ---

Document:
"Unique Identification Authority of India\nName: Priya\nAadhaar No: XXXX XXXX XXXX"
Response:
{{
  "document_type": "Aadhaar Card",
  "reason": "Mentions UIDAI and Aadhaar number"
}}

Document:
"PAN: ACBPP1234D\nIncome Tax Department\nDOB: 10-11-1990"
Response:
{{
  "document_type": "PAN Card",
  "reason": "Contains PAN number and Income Tax Department details"
}}

Document:
"Passport No: N1234567\nName: Rahul\nExpiry: 2028\nGovernment of India"
Response:
{{
  "document_type": "Passport",
  "reason": "Mentions Passport number and Government of India"
}}

Document:
"Voter ID: XYZ1234567\nName: Anjali\nElection Commission of India"
Response:
{{
  "document_type": "VoterID",
  "reason": "Mentions Voter ID and Election Commission of India"
}}

Document:
"DL No: MH12 20190012345\nName: Suresh\nTransport Department"
Response:
{{
  "document_type": "Driving License",
  "reason": "Mentions Driving License number and Transport Department"
}}

Document:
"Basic: 45,000\nHRA: 15,000\nNet Salary: 75,000\nBank A/C: XXXXXXXX"
Response:
{{
  "document_type": "Salary Slip",
  "reason": "Mentions salary components and net pay"
}}

Document:
"Form 16\nAssessment Year: 2023-24\nGross Salary: 8,00,000"
Response:
{{
  "document_type": "Form 16",
  "reason": "Mentions Form 16 and salary details"
}}

Document:
"ITR Acknowledgement\nAssessment Year: 2022-23\nPAN: ABCDE1234F"
Response:
{{
  "document_type": "Income Tax Return",
  "reason": "Mentions ITR and assessment year"
}}

Document:
"Bank Statement\nAccount Number: XXXXXXXX\nPeriod: Jan-Jun 2023"
Response:
{{
  "document_type": "Bank Statement",
  "reason": "Mentions bank statement and account details"
}}

Document:
"Offer Letter\nPosition: Analyst\nSalary: 6 LPA"
Response:
{{
  "document_type": "Offer Letter",
  "reason": "Mentions offer letter and employment details"
}}

Document:
"Employment Certificate\nThis is to certify..."
Response:
{{
  "document_type": "Employment Certificate",
  "reason": "Mentions employment certificate"
}}

Document:
"Employee ID: 12345\nCompany: ABC Corp"
Response:
{{
  "document_type": "Employee ID",
  "reason": "Mentions employee ID and company"
}}

Document:
"Increment Letter\nEffective from: April 2023"
Response:
{{
  "document_type": "Increment Letter",
  "reason": "Mentions increment and effective date"
}}

Document:
"Appraisal Letter\nPerformance: Excellent"
Response:
{{
  "document_type": "Appraisal Letter",
  "reason": "Mentions appraisal and performance"
}}

Document:
"Cancelled Cheque\nAccount Number: XXXXXXXX"
Response:
{{
  "document_type": "Cancelled Cheque",
  "reason": "Mentions cancelled cheque and account number"
}}

Document:
"Loan Application Form\nApplicant: Priya\nLoan Amount: 5,00,000"
Response:
{{
  "document_type": "Loan Application Form",
  "reason": "Mentions loan application and applicant details"
}}

Document:
"Consent Form\nI authorize the bank..."
Response:
{{
  "document_type": "Consent Form",
  "reason": "Mentions consent for CIBIL check or data access"
}}

Document:
"FATCA Declaration\nNRI Status: Yes"
Response:
{{
  "document_type": "FATCA Declaration",
  "reason": "Mentions FATCA and NRI status"
}}

Document:
"Electricity Bill\nAddress: 123 Main St"
Response:
{{
  "document_type": "Proof of Residence",
  "reason": "Mentions proof of residence and address"
}}

Document:
"Photograph\nPassport-size photo"
Response:
{{
  "document_type": "Photograph",
  "reason": "Mentions passport-size photograph"
}}

Document:
"Co-Applicant: Ramesh\nAadhaar: XXXX XXXX XXXX"
Response:
{{
  "document_type": "Co-Applicant Document",
  "reason": "Mentions co-applicant and supporting document"
}}

Document:
"CIBIL Report\nScore: 750"
Response:
{{
  "document_type": "Credit Report",
  "reason": "Mentions CIBIL or credit report"
}}

Document:
"Insurance Policy\nSum Assured: 10,00,000"
Response:
{{
  "document_type": "Insurance Proof",
  "reason": "Mentions insurance policy and sum assured"
}}

Document:
"Digital Consent\nAadhaar eKYC consent given"
Response:
{{
  "document_type": "Digital Consent",
  "reason": "Mentions digital consent for eKYC"
}}

Document:
"Video KYC\nGeo-tagged selfie attached"
Response:
{{
  "document_type": "Video KYC",
  "reason": "Mentions video KYC or geo-tagged selfie"
}}

--- CLASSIFY THIS DOCUMENT ---

{text}
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )
        content = response.choices[0].message.content.strip()
        print("🔍 RAW MODEL RESPONSE:", content)

        # Parse cleanly — remove markdown fences or accidental quotes
        content = content.strip("` \n")
        if content.startswith("json"):
            content = content[4:].strip()
        return json.loads(content)

    except Exception as e:
        print("❌ Error in classification:", e)
        return {
            "document_type": "Others",
            "reason": f"Classification failed or invalid response: {str(e)}"
        }
