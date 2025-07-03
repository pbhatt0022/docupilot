# setup_cosmos.py
from azure.cosmos import CosmosClient, PartitionKey
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")

DATABASE_NAME = "docupilot-db"
CONTAINER_NAME = "documents"

# Initialize client
client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

# Create database and container if they don't exist
database = client.create_database_if_not_exists(id=DATABASE_NAME)
container = database.create_container_if_not_exists(
    id=CONTAINER_NAME,
    partition_key=PartitionKey(path="/applicant_id")
)

print("✅ Cosmos DB setup complete.")
