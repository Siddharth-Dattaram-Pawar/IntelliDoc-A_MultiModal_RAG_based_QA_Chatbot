import pinecone
import boto3
from transformers import AutoTokenizer, AutoModel
import torch
import PyPDF2
import io
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        load_dotenv()
        
        # Initialize Pinecone
        self.pc = pinecone.Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        
        # Initialize S3
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Initialize the model
        self.tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-mpnet-base-v2')
        self.model = AutoModel.from_pretrained('sentence-transformers/all-mpnet-base-v2')
        
        # Create index if it doesn't exist
        self.index_name = "research-docs"
        if self.index_name not in self.pc.list_indexes():
            self.pc.create_index(
                name=self.index_name,
                dimension=768,
                metric="cosine",
                spec=pinecone.PodSpec(
                    environment=os.getenv('PINECONE_ENVIRONMENT')
                )
            )
        
        self.index = self.pc.Index(self.index_name)

    def read_pdf(self, s3_uri):
        """Read PDF content from S3"""
        try:
            # Parse S3 URI
            bucket = s3_uri.split('/')[2]
            key = '/'.join(s3_uri.split('/')[3:])
            
            # Get PDF from S3
            response = self.s3.get_object(Bucket=bucket, Key=key)
            pdf_content = io.BytesIO(response['Body'].read())
            
            # Extract text
            pdf_reader = PyPDF2.PdfReader(pdf_content)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"Error reading PDF from S3: {e}")
            return None

    def generate_embedding(self, text):
        """Generate embedding for text"""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).numpy()[0]

    def store_document(self, s3_uri, title):
        """Store document in Pinecone"""
        try:
            # Read document
            text = self.read_pdf(s3_uri)
            if not text:
                return False
            
            # Generate embedding
            embedding = self.generate_embedding(text)
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[(
                    title,
                    embedding.tolist(),
                    {
                        "title": title,
                        "source": s3_uri
                    }
                )]
            )
            logger.info(f"Stored document: {title}")
            return True
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            return False

    def search(self, query, top_k=5):
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
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