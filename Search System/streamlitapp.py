# streamlitapp.py
import streamlit as st
from pinecone import Pinecone
from dotenv import load_dotenv
import os
import openai
from typing import Optional

# Load environment variables
load_dotenv()

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

class DocumentRetriever:
    def __init__(self):
        # Initialize Pinecone with new syntax
        self.pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        self.index = self.pc.Index("research-notes")
    
    def get_all_pdfs(self) -> list:
        """Get all PDFs from Pinecone index"""
        results = self.index.query(
            vector=[0]*768,  # Dimension size matches your model
            top_k=100,
            include_metadata=True
        )
        return [match['metadata'] for match in results['matches']]
    
    def get_summary(self, text: str) -> str:
        """Generate summary using OpenAI"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes research documents."},
                {"role": "user", "content": f"Please provide a concise summary of the following text:\n\n{text}"}
            ]
        )
        return response['choices'][0]['message']['content']

def main():
    st.title("Research Document Summary")
    
    # Initialize retriever
    retriever = DocumentRetriever()
    
    # Get all PDFs and create dropdown
    pdfs = retriever.get_all_pdfs()
    pdf_titles = [pdf.get('title', 'Unnamed PDF') for pdf in pdfs]
    
    # Add a "Select a PDF" option at the beginning
    pdf_titles = ["Select a PDF..."] + pdf_titles
    selected_pdf = st.selectbox("Choose a PDF to summarize:", pdf_titles)
    
    # Only show the Generate Summary button if a PDF is selected
    if selected_pdf and selected_pdf != "Select a PDF...":
        # Find the selected PDF metadata
        selected_pdf_data = next(
            (pdf for pdf in pdfs if pdf.get('title') == selected_pdf), 
            None
        )
        
        if selected_pdf_data:
            st.write(f"Selected: {selected_pdf}")
            
            # Show preview in expander
            with st.expander("Show PDF Preview"):
                st.write(selected_pdf_data.get('text_preview', 'No preview available'))
            
            # Generate Summary button
            if st.button("Generate Summary"):
                with st.spinner("Generating summary..."):
                    preview_text = selected_pdf_data.get('text_preview', '')
                    if preview_text:
                        summary = retriever.get_summary(preview_text)
                        st.subheader("Summary:")
                        st.write(summary)
                    else:
                        st.warning("No text available to summarize")
        else:
            st.error("Could not find the selected PDF data")

if __name__ == "__main__":
    main()