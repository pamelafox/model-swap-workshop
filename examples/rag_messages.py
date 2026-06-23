import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv
from lunr import lunr

load_dotenv()

endpoint = os.environ["FOUNDRY_ANTHROPIC_MODELS_ENDPOINT"] + "/anthropic"
api_key = os.environ["FOUNDRY_ANTHROPIC_API_KEY"]

# === Choose a model (comment/uncomment) ===
# MODEL = "claude-opus-4-5"
MODEL = "claude-sonnet-4-5"
# MODEL = "claude-haiku-4-5"

# Env var override for batch testing (manual_test.sh sets this)
deployment_name = os.environ.get("FOUNDRY_ANTHROPIC_DEPLOYMENT", MODEL)

client = Anthropic(
    api_key=api_key,
    base_url=endpoint,
)

# Index the data from the JSON - each object has id, text, and embedding
with open("rag_ingested_chunks.json") as file:
    documents = json.load(file)
    documents_by_id = {doc["id"]: doc for doc in documents}
index = lunr(ref="id", fields=["text"], documents=documents)

# Get the user question
user_question = "what are the key differences between how honey bees and carpenter bees build their nests?"

# Search the index for the user question
search_query = "carpenter bee nest building wood"
results = index.search(search_query)
retrieved_documents = [documents_by_id[result["ref"]] for result in results]
print(f"Question: {user_question}")
print(f"Retrieved {len(retrieved_documents)} matching documents, only sending the first 5.")

# Use Anthropic citations: each chunk becomes a plain text document
SYSTEM_MESSAGE = """
You are a helpful assistant that answers questions about insects.
You must use the provided documents to answer the questions,
you should not provide any info that is not in the provided sources.
"""

# Build content blocks: one document per chunk + the user question
content_blocks = []
for doc in retrieved_documents[0:5]:
    content_blocks.append(
        {
            "type": "document",
            "source": {
                "type": "text",
                "media_type": "text/plain",
                "data": doc["text"],
            },
            "title": doc["id"],
            "citations": {"enabled": True},
        }
    )
content_blocks.append({"type": "text", "text": user_question})

response = client.messages.create(
    model=deployment_name,
    max_tokens=1024,
    system=SYSTEM_MESSAGE,
    messages=[{"role": "user", "content": content_blocks}],
)

print(f"\nResponse from {deployment_name}: \n")
# Print text with inline citation markers
for block in response.content:
    if block.type == "text":
        text = block.text
        if block.citations:
            sources = {c.document_title for c in block.citations}
            text += f" [{', '.join(sorted(sources))}]"
        print(text, end="")
print()
