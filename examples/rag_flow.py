import json
import os

from dotenv import load_dotenv
from lunr import lunr
from openai import OpenAI

load_dotenv()

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]
deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)

# Index the data from the JSON - each object has id, text, and embedding
with open("rag_ingested_chunks.json") as file:
    documents = json.load(file)
    documents_by_id = {doc["id"]: doc for doc in documents}
index = lunr(ref="id", fields=["text"], documents=documents)

# Get the user question
user_question = "where do digger bees live?"

# Rewrite the query into good search keywords
QUERY_REWRITE_SYSTEM_MESSAGE = """
You are a helpful assistant that rewrites user questions into good keyword queries
for an index of text chunks about insects.
Good keyword queries don't have any punctuation, and are all lowercase.
Respond with ONLY the suggested keyword query, no other text.
"""

rewrite_response = client.responses.create(
    model=deployment_name,
    input=[
        {"role": "system", "content": QUERY_REWRITE_SYSTEM_MESSAGE},
        {"role": "user", "content": user_question},
    ],
    store=False,
)
search_query = rewrite_response.output_text.strip()
print(f"Original question: {user_question}")
print(f"Rewritten query: {search_query}")

# Search the index for the rewritten query
results = index.search(search_query)
retrieved_documents = [documents_by_id[result["ref"]] for result in results]
print(f"Retrieved {len(retrieved_documents)} matching documents, only sending the first 5.")
context = "\n".join([f"{doc['id']}: {doc['text']}" for doc in retrieved_documents[0:5]])

# Now we can use the matches to generate a response
SYSTEM_MESSAGE = """
You are a helpful assistant that answers questions about insects.
You must use the data set to answer the questions,
you should not provide any info that is not in the provided sources.
Cite the sources you used to answer the question inside square brackets.
The sources are in the format: <id>: <text>.
"""

response = client.responses.create(
    model=deployment_name,
    #temperature=0.3,
    input=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": f"{user_question}\nSources: {context}"},
    ],
    store=False,
)

print(f"\nResponse from {deployment_name}: \n")
print(response.output_text)