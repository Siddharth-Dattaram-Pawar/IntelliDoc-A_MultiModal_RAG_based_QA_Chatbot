


from diagrams import Diagram, Cluster
from diagrams.aws.storage import S3
from diagrams.onprem.workflow import Airflow
from diagrams.generic.database import SQL
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python
# from diagrams.onprem.mlops import MLflow
from diagrams.saas.chat import Slack
from diagrams.generic.blank import Blank
from diagrams.custom import Custom




with Diagram(".", filename="cfa_research_platform", show=True, direction="LR", outformat="png"):
    # Data Source
    with Cluster("Data Source"):
        cfa_source = Python("CFA Research Papers")

    # Data Processing Layer
    with Cluster("Data Processing & Storage"):
        airflow = Airflow("Airflow DAGs")
        
        with Cluster("Storage Layer"):
            with Cluster("Data Storage"):
                snowflake_db = SQL("Metadata\nSnowflake")
                s3_bucket = S3("S3 Bucket")
        
        # with Cluster("Database Layer"):
            
            
            with Cluster("Vector Storage"):
                pinecone_db = SQL("Vector Embeddings")
    
    # Application Layer
    with Cluster("Application Layer"):
        fastapi = FastAPI("FastAPI Backend")
        streamlit = Custom("Streamlit UI", "./streamlit.jpeg")

        with Cluster("AI Services"):
            nvidia = Python("NVIDIA Services")
            rag = Python("Multi-modal RAG")
    
    # Research Notes Layer
    with Cluster("Research Notes System"):
        with Cluster("Indexing"):
            vector_index = SQL("Vector Index")
            search_engine = Python("Store Inputs")
        
        with Cluster("Storage"):
            notes_db = SQL("Research Notes DB")
    
    # Define the flows
    # Data Ingestion Flow
    cfa_source >> airflow
    airflow >> s3_bucket
    airflow >> snowflake_db
    
    # Application Flow
    snowflake_db >> fastapi
    s3_bucket >> fastapi
    fastapi >> streamlit
    fastapi >> nvidia
    fastapi >> rag
    
    # Embedding Creation and Research Notes Flow
    streamlit >> fastapi >> pinecone_db
    rag >> vector_index
    vector_index >> pinecone_db
    fastapi >> notes_db
    notes_db >> search_engine
    search_engine >> streamlit
