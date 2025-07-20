import asyncio
from agents.data.blob_utils import upload_json_blob

async def test_upload():
    dummy_data = {"hello": "world", "score": 9.0}
    url = await upload_json_blob("eligibility-reports", "test-file.json", dummy_data)
    print("Blob URL:", url)

if __name__ == "__main__":
    asyncio.run(test_upload())
