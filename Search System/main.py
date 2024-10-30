# main.py
from src.vector_store import VectorStore
import boto3
import logging
from tqdm import tqdm
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_s3_pdfs(bucket_name):
    """List all PDF files in the S3 bucket"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # List objects in bucket
        paginator = s3_client.get_paginator('list_objects_v2')
        pdf_files = []
        
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    if obj['Key'].lower().endswith('.pdf'):
                        pdf_files.append(obj['Key'])
        
        return pdf_files
    except Exception as e:
        logger.error(f"Error listing S3 files: {e}")
        return []

def main():
    load_dotenv()
    
    # Initialize vector store
    vs = VectorStore()
    bucket_name = os.getenv('AWS_BUCKET')
    
    try:
        # Get list of PDF files from S3
        pdf_files = list_s3_pdfs(bucket_name)
        logger.info(f"Found {len(pdf_files)} PDF files in S3 bucket")
        
        # Create progress bar
        success_count = 0
        failed_count = 0
        
        # Process each PDF
        for idx, pdf_key in tqdm(enumerate(pdf_files), total=len(pdf_files), desc="Processing documents"):
            s3_uri = f"s3://{bucket_name}/{pdf_key}"
            title = pdf_key.split('/')[-1].replace('.pdf', '')  # Use filename as title
            
            success = vs.store_document(
                s3_uri=s3_uri,
                title=title,
                metadata={
                    "document_id": str(idx),
                    "type": "research_document",
                    "s3_key": pdf_key
                }
            )
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                
            # Print status every 10 documents
            if (idx + 1) % 10 == 0:
                logger.info(f"Progress: {idx + 1}/{len(pdf_files)} documents")
                logger.info(f"Successful: {success_count}, Failed: {failed_count}")
        
        # Final summary
        logger.info("\nProcessing Complete!")
        logger.info(f"Total documents processed: {len(pdf_files)}")
        logger.info(f"Successfully stored: {success_count}")
        logger.info(f"Failed to store: {failed_count}")
        
        # Test search
        query = "economic growth"
        results = vs.search(query, top_k=3)
        
        if results:
            logger.info(f"\nTest search results for: {query}")
            for match in results['matches']:
                logger.info(f"Title: {match['metadata']['title']}")
                logger.info(f"Score: {match['score']:.4f}")
                logger.info(f"S3 URI: s3://{bucket_name}/{match['metadata']['s3_key']}")
                logger.info("---")

    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()