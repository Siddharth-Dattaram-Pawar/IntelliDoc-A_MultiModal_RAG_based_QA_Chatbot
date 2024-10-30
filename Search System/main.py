from src.vector_store import VectorStore
import pandas as pd

def main():
    # Initialize vector store
    vs = VectorStore()
    
    # Read your CSV file with document info
    df = pd.read_csv('cfa_publications.csv')
    
    # Store documents in Pinecone
    for idx, row in df.iterrows():
        if row['PDF Link'].startswith('s3://'):
            success = vs.store_document(
                s3_uri=row['PDF Link'],
                title=row['Title']
            )
            if success:
                print(f"Successfully stored: {row['Title']}")
    
    # Test search
    query = "economic growth"
    results = vs.search(query)
    
    if results:
        print(f"\nSearch results for: {query}")
        for match in results['matches']:
            print(f"Title: {match['metadata']['title']}")
            print(f"Score: {match['score']}\n")

if __name__ == "__main__":
    main()