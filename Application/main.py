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
from fastapi import HTTPException
from PyPDF2 import PdfReader
import io

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

class FileKey(BaseModel):
    file_key: str

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

# Retrieve images from S3
@app.get("/images", dependencies=[Depends(oauth2_scheme)])
async def get_images():
    response = s3_client.list_objects_v2(Bucket=AWS_BUCKET_NAME, Prefix="images_new/")
    image_urls = []
    for obj in response.get("Contents", []):
        image_key = obj["Key"]
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_BUCKET_NAME, "Key": image_key},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        image_urls.append({"key": image_key, "url": presigned_url})
    return image_urls

# Retrieve PDFs from S3
@app.get("/pdfs", dependencies=[Depends(oauth2_scheme)])
async def get_pdfs():
    response = s3_client.list_objects_v2(Bucket=AWS_BUCKET_NAME, Prefix="pdfs_new/")
    pdf_urls = []
    for obj in response.get("Contents", []):
        pdf_key = obj["Key"]
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_BUCKET_NAME, "Key": pdf_key},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        pdf_urls.append({"key": pdf_key.split("/")[-1], "url": presigned_url})
    return pdf_urls

# Summarize endpoint to fetch PDF, extract text, and generate summary
@app.post("/summarize")
async def summarize(file_key: FileKey, token: str = Depends(oauth2_scheme)):
    # Fetch PDF from S3
    s3_key = f"pdfs_new/{file_key.file_key}"
    try:
        response = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
        pdf_content = response['Body'].read()
        pdf_reader = PdfReader(io.BytesIO(pdf_content))
        pdf_text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])

        if not pdf_text:
            raise HTTPException(status_code=400, detail="PDF content is empty or could not be extracted.")

    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail=f"PDF file not found: {s3_key}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF from S3: {str(e)}")

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
