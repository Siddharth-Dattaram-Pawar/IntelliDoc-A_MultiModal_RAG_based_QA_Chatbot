
 
 
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import datetime, timedelta
from passlib.context import CryptContext
import boto3
import os
import snowflake.connector
from dotenv import load_dotenv
import re
import requests
from PyPDF2 import PdfReader
import io
from pinecone import Pinecone, ServerlessSpec
import nltk
from nltk.tokenize import sent_tokenize
import logging
 
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
nltk_data_path = os.path.join(os.getcwd(), 'nltk_data')
nltk.data.path.append(nltk_data_path)
 
# Check if punkt tokenizer is available, if not, download it
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('all', download_dir=nltk_data_path)
 
 
# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_API_KEY_VECTOR=os.getenv("NVIDIA_API_KEY_VECTOR")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
INDEX_NAME = os.getenv("INDEX_NAME")
 
 
pc = Pinecone(api_key=PINECONE_API_KEY)
 
# Delete the existing index if necessary
if INDEX_NAME in pc.list_indexes().names():
    pc.delete_index(name=INDEX_NAME)
 
# Create a new index with the correct dimension
pc.create_index(
    name=INDEX_NAME,
    dimension=1024,  # Update to 1024 based on NVIDIA model's output
    metric='cosine',
    spec=ServerlessSpec(
        cloud='aws',
        region=PINECONE_ENVIRONMENT
    )
)
 
# Connect to the index
index = pc.Index(INDEX_NAME)
 
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
 
# Snowflake connection
def get_snowflake_connection():
    return snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        database=SNOWFLAKE_DATABASE,
    )
 
# User model and validation
class User(BaseModel):
    username: str
    password: str
    confirm_password: str
 
class PdfLink(BaseModel):
    pdf_link: str
 
# JWT Token creation
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
 
# Password hashing and verification
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
 
def get_password_hash(password):
    return pwd_context.hash(password)
 
# Password validation
def validate_password(password: str) -> bool:
    pattern = r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    return bool(re.match(pattern, password))
 
def chunk_text(text, chunk_size=15000, overlap=500):
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = []
    current_size = 0
   
    for sentence in sentences:
        if current_size + len(sentence) > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = current_chunk[-overlap:]
            current_size = sum(len(s) for s in current_chunk)
       
        current_chunk.append(sentence)
        current_size += len(sentence)
   
    if current_chunk:
        chunks.append(" ".join(current_chunk))
   
    return chunks
 
# Fetch PDF info from Snowflake
def fetch_pdf_info_from_snowflake():
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Title, Image_Link, PDF_Link FROM CFA_NEW")
        pdf_info = cursor.fetchall()
        return [{"Title": row[0], "Image_Link": row[1], "PDF_Link": row[2]} for row in pdf_info]
    finally:
        cursor.close()
        conn.close()
 
# User registration endpoint
@app.post("/register")
async def register(user: User):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if not validate_password(user.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long, contain a digit, an uppercase letter, and a special character"
        )
 
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM Users WHERE username = %s", (user.username,))
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Username already exists")
 
        hashed_password = get_password_hash(user.password)
        cursor.execute("INSERT INTO Users (username, password) VALUES (%s, %s)", (user.username, hashed_password))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
   
    return {"message": "User registered successfully"}
 
# User login endpoint
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM Users WHERE username = %s", (form_data.username,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
 
    if not user or not verify_password(form_data.password, user[0]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
   
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}
 
# Retrieve images endpoint
@app.get("/images", dependencies=[Depends(oauth2_scheme)])
async def get_images():
    pdf_info = fetch_pdf_info_from_snowflake()
    return [{"Title": pdf['Title'], "Image_Link": pdf['Image_Link']} for pdf in pdf_info if pdf['Image_Link']]
 
# Retrieve PDFs endpoint
@app.get("/pdfs", dependencies=[Depends(oauth2_scheme)])
async def get_pdfs():
    pdf_info = fetch_pdf_info_from_snowflake()
    default_image_url = "https://as1.ftcdn.net/v2/jpg/02/17/88/52/1000_F_217885295_7a4cZ28RGP15RPzeRhFSYx49YMwk5Y53.jpg"
   
    for pdf in pdf_info:
        if pdf['PDF_Link'].startswith('s3://'):
            bucket, key = pdf['PDF_Link'][5:].split('/', 1)
            pdf['url'] = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=3600
            )
        else:
            pdf['url'] = pdf['PDF_Link']
       
        if pdf['Image_Link'] and pdf['Image_Link'] != 'N/A':
            if pdf['Image_Link'].startswith('s3://'):
                bucket, key = pdf['Image_Link'][5:].split('/', 1)
                pdf['image_url'] = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=3600
                )
            else:
                pdf['image_url'] = pdf['Image_Link']
        else:
            pdf['image_url'] = default_image_url
   
    return pdf_info
 
# Summarize endpoint
@app.post("/summarize")
async def summarize(pdf_link: PdfLink, token: str = Depends(oauth2_scheme)):
    # Fetch PDF content
    if pdf_link.pdf_link.startswith('s3://'):
        # Extract the key from the S3 URI
        bucket, key = pdf_link.pdf_link[5:].split('/', 1)
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            pdf_content = response['Body'].read()
        except s3_client.exceptions.NoSuchKey:
            raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_link.pdf_link}")
    else:
        # Fetch PDF from URL
        response = requests.get(pdf_link.pdf_link)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_link.pdf_link}")
        pdf_content = response.content
 
    # Extract text from PDF
    pdf_reader = PdfReader(io.BytesIO(pdf_content))
    pdf_text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
 
    if not pdf_text:
        raise HTTPException(status_code=400, detail="PDF content is empty or could not be extracted.")
 
    # Call NVIDIA's API for summarization
    nvidia_api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    # Limit text to the first 4000 characters for the prompt
    prompt_text = f"Summarize the following text:\n\n{pdf_text[:4000]}"
    payload = {
        "model": "nvidia/llama-3.1-nemotron-70b-instruct",
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": 400,
        "temperature": 0.5
    }
 
    try:
        nvidia_response = requests.post(nvidia_api_url, json=payload, headers=headers)
        nvidia_response.raise_for_status()  # Ensure successful HTTP response
        response_data = nvidia_response.json()
       
        # Extract summary text from response
        summary = response_data.get("choices", [{}])[0].get("message", {}).get("content", "No summary generated")
       
        # Check if summary is generic or empty
        if summary.strip().lower() in ["no summary generated", ""]:
            raise HTTPException(status_code=500, detail="Summary generation failed or returned a generic response.")
 
        return {"summary": summary}
 
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid response format from NVIDIA API")
 
 
@app.post("/embed")
async def create_embedding(pdf_link: PdfLink, token: str = Depends(oauth2_scheme)):
    logger.info(f"Starting embedding process for PDF: {pdf_link.pdf_link}")
   
    try:
        # Fetch PDF content
        if pdf_link.pdf_link.startswith('s3://'):
            logger.info("Fetching PDF from S3")
            bucket, key = pdf_link.pdf_link[5:].split('/', 1)
            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                pdf_content = response['Body'].read()
                logger.info("Successfully fetched PDF from S3")
            except s3_client.exceptions.NoSuchKey:
                logger.error(f"PDF file not found in S3: {pdf_link.pdf_link}")
                raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_link.pdf_link}")
        else:
            logger.info("Fetching PDF from URL")
            response = requests.get(pdf_link.pdf_link)
            if response.status_code != 200:
                logger.error(f"Failed to fetch PDF from URL: {pdf_link.pdf_link}")
                raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_link.pdf_link}")
            pdf_content = response.content
            logger.info("Successfully fetched PDF from URL")
 
        # Extract text from PDF
        logger.info("Extracting text from PDF")
        pdf_reader = PdfReader(io.BytesIO(pdf_content))
        pdf_text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        if not pdf_text:
            logger.error("PDF content is empty or could not be extracted")
            raise HTTPException(status_code=400, detail="PDF content is empty or could not be extracted.")
        logger.info(f"Successfully extracted {len(pdf_text)} characters from PDF")
 
        # Chunk the PDF text
        logger.info("Chunking PDF text")
        chunks = chunk_text(pdf_text)
        logger.info(f"Created {len(chunks)} chunks from PDF text")
 
        nvidia_api_url = "https://integrate.api.nvidia.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY_VECTOR}",
            "Content-Type": "application/json"
        }
        document_id = f"pdf-{hash(pdf_text)}"  # Base document ID
        chunk_embeddings = []
 
        logger.info("Generating embeddings for chunks")
        for i, chunk in enumerate(chunks):
            test_chunk = chunk[:1000]  # Use the first 1000 characters of the chunk
            payload = {
                 "model": "nvidia/nv-embedqa-e5-v5",
                 "input": [test_chunk],
                 "encoding_format": "float",
                 "input_type": "query"
                 }
            try:
                nvidia_response = requests.post(nvidia_api_url, json=payload, headers=headers)
                nvidia_response.raise_for_status()
                response_data = nvidia_response.json()
                embeddings = response_data["data"][0]["embedding"]
                if not embeddings:
                    logger.error(f"Embedding generation failed for chunk {i}")
                    raise HTTPException(status_code=500, detail=f"Embedding generation failed for chunk {i}")
                #chunk_id = f"{document_id}-chunk-{i}"
                chunk_embeddings.append({
                    "id": f"{document_id}-chunk-{i}",
                    "values": embeddings,
                    "metadata": {"text": chunk[:500]}
                    })
                logger.info(f"Successfully generated embedding for chunk {i}")
            except requests.RequestException as e:
                logger.error(f"Failed to generate embeddings for chunk {i}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to generate embeddings for chunk {i}: {str(e)}")
            except ValueError:
                logger.error(f"Invalid response format from NVIDIA API for chunk {i}")
                raise HTTPException(status_code=500, detail=f"Invalid response format from NVIDIA API for chunk {i}")
       
        # Function to upsert in batches to avoid exceeding request size
        def upsert_in_batches(embeddings, index, batch_size=50):
            for i in range(0, len(embeddings), batch_size):
                batch = embeddings[i:i + batch_size]
                try:
                    logger.info(f"Upserting batch {i // batch_size + 1} of embeddings to Pinecone")
                    index.upsert(vectors=batch)
                    logger.info(f"Successfully upserted batch {i // batch_size + 1}")
                except Exception as e:
                    logger.error(f"Failed to upsert batch {i // batch_size + 1}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to upsert embeddings batch: {str(e)}")
 
        # Upsert embeddings in batches
        logger.info("Upserting embeddings to Pinecone in batches")
        upsert_in_batches(chunk_embeddings, index, batch_size=50)
       
        return {"message": f"Embeddings created and stored in Pinecone successfully for {len(chunks)} chunks", "document_id": document_id}
 
    except Exception as e:
        logger.error(f"Unexpected error in create_embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
 
