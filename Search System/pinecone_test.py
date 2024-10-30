import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone
pc = Pinecone(
    api_key=os.getenv('PINECONE_API_KEY')
)

# Check if the API key is valid and list existing indexes
try:
    indexes = pc.list_indexes().names()  # List existing indexes
    print("Pinecone API key is valid. Existing indexes:", indexes)
except Exception as e:
    print(f"Error: {e}")