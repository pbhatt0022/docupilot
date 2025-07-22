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
    
    if(applicant_id == "All Applicants"):
        results = client.search(
            search_text="*",
            select=["*"],
            top=20
        )
    else :
        results = client.search(
            search_text="*",
            filter=f"applicant_id eq '{applicant_id}'",
            select=["*"],
            top=20
        )


    results = clean_chunks(results)
    results = build_context(results)

    return results


def get_response(prompt, applicant_information) :
    client = AzureOpenAI(
        api_key=CHAT_API_KEY,
        api_version=CHAT_API_VERSION,
        azure_endpoint=CHAT_ENDPOINT
    )
    
    system_message = "You are an assistant answering questions about a specific applicant based only on the provided context. If the answer is not in the context, say so"

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_message
            },  
            {
                "role": "user",
                "content": f"Context:\n{applicant_information}\n\nQuestion: {prompt}"
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

    