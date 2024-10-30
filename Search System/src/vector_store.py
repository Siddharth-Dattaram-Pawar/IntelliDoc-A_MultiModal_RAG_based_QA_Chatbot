# src/vector_store.py
import pinecone
import boto3
from transformers import AutoTokenizer, AutoModel
import torch
import PyPDF2
import io
import os
from dotenv import load_dotenv
import logging
from tqdm import tqdm
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        load_dotenv()
        
        # Initialize Pinecone
        self.pc = pinecone.Pinecone(
            api_key=os.getenv('PINECONE_API_KEY')
        )
        
        # Initialize S3
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Initialize the model
        self.tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-mpnet-base-v2')
        self.model = AutoModel.from_pretrained('sentence-transformers/all-mpnet-base-v2')
        
        # Connect to existing index
        self.index_name = "research-notes"
        self.index = self.pc.Index(self.index_name)
        logger.info(f"Connected to index: {self.index_name}")

    def read_pdf(self, s3_uri, max_retries=3):
        """Read PDF content from S3 with retries"""
        for attempt in range(max_retries):
            try:
                parts = s3_uri.replace("s3://", "").split("/")
                bucket = parts[0]
                key = "/".join(parts[1:])
                
                response = self.s3.get_object(Bucket=bucket, Key=key)
                pdf_content = io.BytesIO(response['Body'].read())
                
                pdf_reader = PyPDF2.PdfReader(pdf_content)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to read PDF after {max_retries} attempts: {e}")
                    return None
                time.sleep(1)  # Wait before retrying


    def generate_embedding(self, text):
        """Generate embedding for text"""
        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Get embedding from the last hidden state
            embedding = outputs.last_hidden_state.mean(dim=1).numpy()[0]
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def store_document(self, s3_uri, title, metadata=None):
        """Store document in Pinecone"""
        try:
            # Read document
            text = self.read_pdf(s3_uri)
            if not text:
                return False
            
            # Generate embedding
            embedding = self.generate_embedding(text)
            if embedding is None:
                return False
            
            # Prepare metadata
            metadata = metadata or {}
            metadata.update({
                "title": title,
                "source": s3_uri,
                "text_preview": text[:1000]  # Store first 1000 chars as preview
            })
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[(
                    title,  # Using title as ID
                    embedding.tolist(),
                    metadata
                )]
            )
            logger.info(f"Successfully stored document: {title}")
            return True
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            return False

    def search(self, query, top_k=5):
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            if query_embedding is None:
                return None
            
            # Search in Pinecone
            results = self.index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                include_metadata=True
            )
            
            return results
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return None

    def delete_document(self, title):
        """Delete a document from the index"""
        try:
            self.index.delete(ids=[title])
            logger.info(f"Successfully deleted document: {title}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
        
    def store_document(self, s3_uri, title, metadata=None, timeout=300):
        """Store document in Pinecone with timeout"""
        try:
            start_time = time.time()
            
            # Read document with timeout check
            text = self.read_pdf(s3_uri)
            if not text:
                return False
            
            if time.time() - start_time > timeout:
                logger.error(f"Timeout processing document: {title}")
                return False
            
            # Generate embedding
            embedding = self.generate_embedding(text)
            if embedding is None:
                return False
            
            # Prepare metadata
            metadata = metadata or {}
            metadata.update({
                "title": title,
                "source": s3_uri,
                "text_preview": text[:500]  # Reduced preview length
            })
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[(
                    title,
                    embedding.tolist(),
                    metadata
                )]
            )
            return True
            
        except Exception as e:
            logger.error(f"Error storing document {title}: {e}")
            return False