
from diagrams import Diagram, Cluster
from diagrams.aws.storage import S3
from diagrams.onprem.workflow import Airflow
from diagrams.generic.database import SQL
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python
from diagrams.custom import Custom

with Diagram("CFA Research Platform Complete Architecture", filename="cfa_research_platform", show=True, direction="LR"):
    # Data Source
    with Cluster("Data Source"):
        cfa_source = Custom("CFA Research Papers", "./cfa.jpeg")

    # Data Processing Layer
    with Cluster("Data Processing & Storage"):
        airflow = Airflow("Airflow DAGs")
        
        with Cluster("Storage Layer"):
            with Cluster("Data Storage"):
                # Snowflake metadata with "Research Notes" label
                snowflake_db = Custom("Metadata & Research Notes\nSnowflake", "./snow.png")
                s3_bucket = S3("S3 Bucket")
            
            # Vector Storage directly in Pinecone
            pinecone_db = Custom("Pinecone Vector Embeddings", "./pinecone.jpeg")
    
    # Application Layer
    with Cluster("Application Layer"):
        fastapi = FastAPI("FastAPI Backend")
        streamlit = Custom("Streamlit UI", "./streamlit.jpeg")

        with Cluster("AI Services"):
            nvidia = Custom("NVIDIA Services", "./nvidia.jpeg")
            rag = Custom("Multi-modal RAG", "./nvidia.jpeg")
    
    # Define the flows
    # Data Ingestion Flow
    cfa_source >> airflow
    airflow >> s3_bucket
    airflow >> snowflake_db
    
    # Application Flow
    snowflake_db >> fastapi
    s3_bucket >> fastapi
    pinecone_db >> fastapi  # Arrow from Pinecone to FastAPI
    fastapi >> streamlit
    fastapi >> nvidia
    fastapi >> rag
    
    # Embedding Creation Flow
    streamlit >> fastapi >> pinecone_db