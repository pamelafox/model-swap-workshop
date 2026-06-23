import json
import os

from dotenv import load_dotenv
from lunr import lunr
from openai import OpenAI

load_dotenv()

MODEL = "gpt-5.5"
# MODEL = "Kimi-K2.6"
# MODEL = "DeepSeek-V4-Flash"
# MODEL = "Mistral-Large-3"
deployment_name = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", MODEL)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]

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
user_question = "what are the key differences between how honey bees and carpenter bees build their nests?"

# Search the index for the user question
search_query = "carpenter bee nest building wood"
results = index.search(search_query)
retrieved_documents = [documents_by_id[result["ref"]] for result in results]
print(f"Question: {user_question}")
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
    input=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": f"{user_question}\nSources: {context}"},
    ],
    store=False,
    # -- Experiment with these parameters to affect the output:
    # -- temperature is not supported on gpt-5 models, but works on others
    # temperature=0.3,
    # -- reasoning is only supported on gpt-5 models, but not others
    # reasoning={"effort": "medium", "summary": "detailed"},
)

print(f"\nResponse from {deployment_name}: \n")
print(response.output_text)
