import os
import openai
from openai import AzureOpenAI
import requests
import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
load_dotenv()
from rag_pipeline import clean_chunks, build_context


SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
INDEX_NAME = "rag-2"

CHAT_ENDPOINT = os.getenv("CHAT_ENDPOINT")
CHAT_DEPLOYMENT = "gpt-4.1"
CHAT_API_VERSION = "2024-12-01-preview"
CHAT_API_KEY = os.getenv("CHAT_API_KEY")


def get_applicant_information(applicant_id: str):
    """Fetch applicant information from Azure Cognitive Search."""
    client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_API_KEY)
    )

    results = client.search(
        search_text="*",
        filter=f"applicant_id eq '{applicant_id}'",
        select=["*"],
        top=100
    )

    results = clean_chunks(results)
    results = build_context(results)

    return results


def get_response(loan_amount_requested, applicant_information) :
    client = AzureOpenAI(
        api_key=CHAT_API_KEY,
        api_version=CHAT_API_VERSION,
        azure_endpoint=CHAT_ENDPOINT
    )

    system_message = '''You are a highly accurate personal loan eligibility agent. You will be provided with the loan amount requested and the applicant's information. Based on this, you will determine if the applicant is eligible for the loan. Base you decision on
     -> Credit score (ideally ≥ 670; excellent ≥ 720)
     -> Debt-to-income (DTI ≤ 36-40%; lenders may allow up to 50%)
     -> Employment/income stability (steady income/employment status)
     -> Collateral if credit is weak
     Your task:
        - **Calculate** the applicant's DTI ratio as `(debt_monthly ÷ income_monthly) x 100%`
        - **Evaluate eligibility**:
        - Approve if: credit score good/excellent, DTI within acceptable range, stable income/employment, requested loan amount reasonable relative to income.
        - Otherwise, reject.
        - If rejected, list the **top 2-3 reasons** (e.g., high DTI, low credit score, unstable employment).
        - **Optionally**, suggest a single actionable step to improve eligibility (e.g., reduce debt, improve credit score).
        '''
    

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_message
            },  
            {
                "role": "user",
                "content": f"requested_loan_amount:\n{loan_amount_requested}\n\napplicant_information:\n{applicant_information}"
            }
        ],
        max_tokens=800,
        temperature=0.2,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        model=CHAT_DEPLOYMENT
    )

    return response.choices[0].message.content.strip()


def eligibility_agent(applicant_id: str, loan_amount_requested: float):
    try:
        applicant_information = get_applicant_information(applicant_id)
        if not applicant_information:
            return "No applicant information found."

        response = get_response(loan_amount_requested, applicant_information)
        return response

    except Exception as e:
        return f"An error occurred: {str(e)}"
    


result = eligibility_agent("eabbe441", 15000) 
print(result)
    

    
