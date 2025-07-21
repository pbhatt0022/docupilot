# Step 1: Load packages
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import AzureAISearchTool, Tool
from azure.ai.agents.models import MessageRole, ListSortOrder

# Load environment variables

# Azure AI Project config
ENDPOINT = "https://dikshap04-2930-resource.services.ai.azure.com"
RESOURCE_GROUP = "rg-dikshap04-8287_ai"
SUBSCRIPTION_ID = "42c8e906-d297-4aa8-8e25-0c092ca65899"
PROJECT_NAME = "dikshap04-7574"
INDEX_NAME = "rag-1752732624194"

# Step 2: Connect to Azure AI Project
def create_ai_client():
    project_client = AIProjectClient(
        endpoint=ENDPOINT,
        resource_group_name=RESOURCE_GROUP,
        subscription_id=SUBSCRIPTION_ID,
        project_name=PROJECT_NAME,
        credential=DefaultAzureCredential()
    )
    return project_client

# Step 3: Connect to Azure AI Search
def configure_search_tool(project_client):
    # Get all connections
    conn_list = list(project_client.connections.list())
    print("\n🔍 Searching for Azure AI Services connection...")
    
    # Debug: Print all connections and their details
    for conn in conn_list:
        print(f"Connection name: {conn.name}")
        print(f"Connection type: {getattr(conn, 'connection_type', 'N/A')}")
        print(f"Connection ID: {conn.id}")
        print("-" * 50)
    
    # Try to find the Azure AI Services connection (not the _aoai one)
    conn_id = ""
    for conn in conn_list:
        connection_type = str(getattr(conn, 'connection_type', ''))
        print(f"Debug - Checking connection: {conn.name}, Type: {connection_type}")
        
        if conn.name == "ai-dikshap043820ai056226371486":
            conn_id = conn.id
            print(f"✅ Found Azure AI Services connection: {conn_id}")
            break
    
    if not conn_id:
        raise Exception("No Azure AI Services connection found")

    # Step 4: Define the AI Search tool
    try:
        # First try with minimal configuration
        ai_search = AzureAISearchTool(
            index_connection_id=conn_id,
            index_name=INDEX_NAME
        )
        print("✅ Successfully configured Azure AI Search tool")
        return ai_search
    except Exception as e:
        print(f"⚠️ Error configuring search tool: {str(e)}")
        print("Attempting alternative configuration...")
        
        # Try alternative configuration
        ai_search = AzureAISearchTool(
            connection_id=conn_id,  # Try different parameter name
            index_name=INDEX_NAME
        )
        print("✅ Successfully configured Azure AI Search tool with alternative configuration")
        return ai_search

def verify_document(project_client, agent_id, query):
    # Create a thread for communication
    thread = project_client.agents.threads.create()
    
    # Send a message to the thread
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=query
    )
    
    # Create and process a run with the specified thread and agent
    run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
    
    if run.status == "failed":
        raise Exception(f"Run failed: {run.last_error}")
    
    # Fetch and return all messages in the thread
    messages = project_client.agents.list_messages(
        thread_id=thread.id, 
        order=ListSortOrder.ASCENDING
    )
    return [msg for msg in messages.text_messages if hasattr(msg, 'content') and isinstance(msg.content, str)]

def chat_with_agent():
    try:
        # Step 2: Connect to Azure AI Project
        project_client = create_ai_client()
        
        # Step 3 & 4: Configure search tool
        ai_search = configure_search_tool(project_client)
        
        # Step 5: Define the Agent with updated instructions
        agent = project_client.agents.create_agent(
            model="gpt-35-turbo",  # Using GPT-3.5 Turbo as it's more commonly available
            name="document-verification-agent",
            instructions="""You are a document verification agent specialized in analyzing:
            
            1. Document Authenticity:
               - Verify document signatures and stamps
               - Check for any alterations or inconsistencies
               - Validate document formats and layouts
            
            2. Content Verification:
               - Extract and validate key information
               - Compare against standard templates
               - Identify missing or incorrect information
            
            3. Compliance Check:
               - Ensure all required sections are present
               - Verify compliance with regulatory standards
               - Flag any non-compliant elements
            
            4. Risk Assessment:
               - Identify potential red flags
               - Highlight areas needing attention
               - Provide risk level assessment
            
            Be specific in your analysis, citing exact locations of findings and providing clear explanations.""",
            tools=ai_search.definitions,
            tool_resources=ai_search.resources,
        )
        print("\n✅ Document Verification Agent created successfully")
        
        # Step 6: Create a thread
        thread = project_client.agents.create_thread()
        print("\n💬 Starting document verification session...")
        print("Type 'exit' to end the conversation\n")
        
        while True:
            # Get user input
            user_input = input("\n👤 You: ")
            
            if user_input.lower() == 'exit':
                print("\n👋 Ending verification session...")
                break
            
            print("\n⏳ Processing your request...")
            
            # Step 7: Create and send message
            message = project_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=user_input
            )
            
            # Run the agent
            run = project_client.agents.create_and_process_run(
                thread_id=thread.id,
                agent_id=agent.id
            )
            
            # Display output
            if run.status == "completed":
                messages = project_client.agents.list_messages(thread_id=thread.id)
                last_msg = messages.get_last_text_message_by_role("assistant")
                
                if last_msg and hasattr(last_msg, 'text') and hasattr(last_msg.text, 'value'):
                    print("\n🤖 Analysis Result:")
                    print("=" * 50)
                    print(last_msg.text.value)
                    print("=" * 50)
                else:
                    print("\n⚠️ Unable to generate analysis. Please try again.")
            else:
                print(f"\n❌ Analysis failed with status: {run.status}")
            
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
    finally:
        try:
            # Clean up the agent
            if 'agent' in locals():
                project_client.agents.delete_agent(agent.id)
                print("\nAgent cleaned up successfully")
        except Exception as cleanup_error:
            print(f"\nError during cleanup: {str(cleanup_error)}")

if __name__ == "__main__":
    chat_with_agent()