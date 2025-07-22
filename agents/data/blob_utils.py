import os
import json
from azure.storage.blob.aio import BlobServiceClient

BLOB_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

async def upload_json_blob(container_name: str, file_name: str, content: dict) -> str:
    """
    Uploads a JSON-serializable Python dictionary to Azure Blob Storage.
    """
    if not BLOB_CONN_STR:
        raise ValueError("Missing Azure Blob connection string. Check your .env file.")

    async with BlobServiceClient.from_connection_string(BLOB_CONN_STR) as blob_service_client:
        async with blob_service_client.get_container_client(container_name) as container_client:
            # Create the container if it doesn't exist
            try:
                await container_client.create_container()
            except Exception:
                pass  # Container likely already exists

            blob_client = container_client.get_blob_client(file_name)
            json_str = json.dumps(content, indent=2)

            await blob_client.upload_blob(json_str, overwrite=True)

            return blob_client.url

async def download_json_blob(container_name: str, file_name: str) -> dict:
    """
    Downloads a JSON blob from Azure Blob Storage and returns it as a Python dictionary.
    """
    if not BLOB_CONN_STR:
        raise ValueError("Missing Azure Blob connection string. Check your .env file.")

    async with BlobServiceClient.from_connection_string(BLOB_CONN_STR) as blob_service_client:
        async with blob_service_client.get_container_client(container_name) as container_client:
            blob_client = container_client.get_blob_client(file_name)
            stream = await blob_client.download_blob()
            data = await stream.readall()
            return json.loads(data)
