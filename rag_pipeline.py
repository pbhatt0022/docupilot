import os
import openai
from openai import AzureOpenAI
import requests
import json
from dotenv import load_dotenv
load_dotenv()

# ----------- CONFIGURATION ----------- #

# Azure OpenAI embedding
EMBED_DEPLOYMENT = "text-embedding-ada-002"
EMBED_API_KEY = os.getenv("EMBED_API_KEY")
EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT")
EMBED_API_VERSION = "2023-05-15"

# Azure Cognitive Search
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
INDEX_NAME = "rag-2"
VECTOR_FIELD = "text_vector"

# Azure OpenAI chat completion
CHAT_ENDPOINT = os.getenv("CHAT_ENDPOINT")
CHAT_DEPLOYMENT = "gpt-4.1"
CHAT_API_VERSION = "2024-12-01-preview"
CHAT_API_KEY = os.getenv("CHAT_API_KEY")



# ----------- FUNCTIONS ----------- #

def get_embedding(prompt: str):
    openai.api_key = EMBED_API_KEY
    openai.azure_endpoint = EMBED_ENDPOINT
    openai.api_version = EMBED_API_VERSION

    response = openai.embeddings.create(
        input=prompt,
        model=EMBED_DEPLOYMENT
    )
    return response.data[0].embedding


def search_vector_top_k(embedding, k=5):
    url = f"{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs/search?api-version=2023-10-01-Preview"

    headers = {
        "Content-Type": "application/json",
        "api-key": SEARCH_API_KEY
    }

    body = {
        "count": True,
        "select": "*",
        "vectorQueries": [
            {
                "kind": "vector",
                "vector": embedding,
                "fields": VECTOR_FIELD,
                "k": k,
                "exhaustive": True
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code != 200:
        raise Exception(f"Search failed: {response.status_code}, {response.text}")

    return response.json()["value"]


def clean_chunks(docs, vector_field=VECTOR_FIELD):
    return [ {k: v for k, v in doc.items() if k != vector_field} for doc in docs ]


def build_context(docs):
    formatted_chunks = []
    file_set = set()
    for doc in docs:
        filename = doc.get("filename", "<unknown>")
        file_set.add(filename)
        text = doc.get("chunk", "").replace("\n", " ").strip()
        if not text:
            continue
        formatted_chunks.append(f"filename : [{filename}]\n text : {text}")
    return "\n\n".join(formatted_chunks), file_set



def get_answer(prompt, context):
    client = AzureOpenAI(
        api_key=CHAT_API_KEY,
        api_version=CHAT_API_VERSION,
        azure_endpoint=CHAT_ENDPOINT
    )

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an assistant that answers questions based only on the provided context. If the answer is not in the context, say so."
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {prompt}"
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


# ----------- MAIN LOOP ----------- #

def main():
    print("🔍 Ask questions about your documents (type 'exit' to quit):\n")

    while True:
        prompt = input("🧠 Your Question: ").strip()
        if prompt.lower() in {"exit", "quit"}:
            print("👋 Exiting. Goodbye!")
            break

        try:
            embedding = get_embedding(prompt)
            raw_chunks = search_vector_top_k(embedding)
            cleaned_chunks = clean_chunks(raw_chunks)
            context, file_set = build_context(cleaned_chunks)
            print(file_set)
            answer = get_answer(prompt, context)

            print("\n🤖 Answer:")
            print(answer)
            print("\n" + "-" * 60 + "\n")

        except Exception as e:
            print(f"⚠️ Error: {e}\n")


if __name__ == "__main__":
    main()
