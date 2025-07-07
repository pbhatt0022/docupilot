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
- Salary Slip
- Bank Statement
- Offer Letter
- Cancelled Cheque
- ITR (Income Tax Return)
- Consent Form
- FATCA
- Loan Application Form
- Form 16
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
"Basic: 45,000\nHRA: 15,000\nNet Salary: 75,000\nBank A/C: XXXXXXXX"
Response:
{{
  "document_type": "Salary Slip",
  "reason": "Mentions salary components and net pay"
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
