# text_extraction.py
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os

FORM_RECOGNIZER_ENDPOINT = os.getenv("FORM_RECOGNIZER_ENDPOINT")
FORM_RECOGNIZER_KEY = os.getenv("FORM_RECOGNIZER_KEY")

document_analysis_client = DocumentAnalysisClient(
    endpoint=FORM_RECOGNIZER_ENDPOINT,
    credential=AzureKeyCredential(FORM_RECOGNIZER_KEY)
)

def extract_text_from_blob_url(blob_url: str) -> str:
    try:
        poller = document_analysis_client.begin_analyze_document_from_url(
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
