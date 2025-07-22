# PDF Chunk Indexer Azure Function

This Azure Function automatically processes and indexes new documents uploaded to Azure Blob Storage for Retrieval-Augmented Generation (RAG) Q&A. It enables instant access to the latest document context in your RAG pipeline.

## Folder Structure
- `function_app.py` — Main Azure Function code (Blob Trigger)
- `requirements.txt` — Python dependencies (Python 3.10)
- `host.json` — Azure Functions host configuration
- `local.settings.json` — Local development settings (do not commit secrets)
- `.funcignore` — Ignore rules for deployment

## Setup
1. **Python Version**: Ensure you are using Python 3.10.
2. **Install Azure Functions Core Tools**: [Install Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Environment Variables:**
   - Create a `.env` file in this folder with the following keys:
     - `EMBED_API_KEY`, `EMBED_ENDPOINT`, `SEARCH_ENDPOINT`, `SEARCH_API_KEY`
   - Or set them in your Azure Function App settings.
5. **Set up `local.settings.json`:**
   - Add your `AzureWebJobsStorage` connection string.

## Running Locally
```bash
func start
```

## Deployment
- Deploy using Azure Functions Core Tools or from the Azure Portal.
- Ensure all environment variables are set in the Azure Function App configuration.

## How it Works
- Triggered by new blobs in `loan-documents/{applicant_id}/{document_type}/{filename}`.
- Extracts and chunks text from PDFs and images, generates embeddings, and indexes them in Azure Cognitive Search.
- No manual refresh needed—new uploads are instantly available for RAG Q&A.

## Notes
- This function runs independently of the Streamlit dashboard, but keeps the RAG index up-to-date for all downstream applications.
- For production, secure your secrets and review Azure costs for embedding and search APIs. 