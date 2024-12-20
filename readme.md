# IntelliDoc : A Multi-Modal RAG based QA Chatbot

## Project Overview

The application offers efficient data ingestion, secure document interaction, and multi-modal querying, making it an end-to-end solution for exploring and analyzing research publications from the CFA Institute Research Foundation. 

**Details :** Developed a comprehensive web scraping pipeline using Selenium to extract metadata and research publications from the CFA Institute website. The pipeline integrates seamlessly with Apache Airflow for automated metadata processing, AWS S3 for storing unstructured data such as PDFs and images, and Snowflake for structured metadata management.
Built a FastAPI and Streamlit-based document exploration application with JWT authentication to ensure secure client access. The application enables users to interact with and analyze research publications efficiently. Integrated NVIDIA models to implement AI-driven PDF summarization, enhancing content accessibility and understanding.
Implemented a Multi-Modal Retrieval-Augmented Generation (RAG) system, utilizing Pinecone for storing and querying vector embeddings. This system facilitates advanced document querying and the generation of Research Notes, linking relevant insights, graphs, and tables for enriched research capabilities.



[![Codelabs](https://img.shields.io/badge/Codelabs-green?style=for-the-badge)](https://codelabs-preview.appspot.com/?file_id=1ZKUCJ26fZkN3CAf_9Ul-TJlIDZqkYzMIgs5npvLNNTw/edit?tab=t.0#0) 

Video Link
----------------------
https://youtu.be/z_mVkaGA4wU

### Attestation

WE ATTEST THAT WE HAVEN'T USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK



### Table of Contents

1. [Architecture Diagram](#architecture-diagram)
2. [Components](#components)
3. [Technologies Used](#technologies-used)
4. [Install dependencies using Poetry](#install-dependencies-using-poetry)
5. [Set up environment variables](#set-up-environment-variables)
6. [Deployment](#deployment)
7. [License](#license)
8. [Support](#support)
9. [Acknowledgments](#acknowledgments)

### Architecture Diagram

![image](https://github.com/user-attachments/assets/4641f247-8830-4cb3-b3a3-3ec4a8c8bbb6)

### Components

1. **Web Scraping and Data Ingestion Pipeline**
	* Web scraping for CFA Institute publications using Selenium
	* Airflow DAGs for data pipelne
	* Data storage in S3 and Snowflake
2. **FastAPI Backend**
	* Document exploration API
	* Integration with NVIDIA services
	* Multi-modal RAG implementation
	* Q&A processing system
3. **Streamlit Frontend**
	* Document grid/list view
	* Summary generation & previewing interface
	* Q&A interaction chatbot
	* Research notes management
4. **Multi-Modal RAG and Research Notes link**
	* Pinecone vector database integration
	* Appending the research notes

### Technologies Used

| **Technology/Tool**                      | **Purpose**                                                                                       |
|------------------------------------------|---------------------------------------------------------------------------------------------------|
| **FastAPI**                              | Backend framework for user authentication, document retrieval, and summarization APIs.           |
| **Streamlit**                            | Frontend framework for document exploration and interaction.                                     |
| **CFA Institute Research Foundation Publications** | Source of data for research documents.                                                           |
| **Airflow & Selenium**                   | Tools for automating data ingestion and web scraping.                                            |
| **AWS S3**                               | Storage solution for images and PDFs associated with research documents.                         |
| **Snowflake**                            | Data warehouse for storing metadata, research notes, and user data.                              |
| **NVIDIA meta llama-3.1-8b-instruct**    | Advanced model for language understanding, reasoning, and text generation.                       |
| **NVIDIA DePlot**                        | Converts graphs and plots from documents into descriptive text for text-based search and analysis.|
| **NVIDIA NeVA 22B**                      | Transforms images within documents into text representations for comprehensive querying.          |
| **NVIDIA embedqa-v5-v6 Model**           | Generates detailed text embeddings for high-precision, contextually relevant retrieval.           |
| **NVIDIA API Key**                       | Secures and manages access to NVIDIA functionalities for summarization and querying.              |
| **Pinecone**                             | Vector database for storing and retrieving embeddings for context-based search.                   |
| **Docker**                               | Containerization tool for packaging FastAPI and Streamlit applications for streamlined deployment. |


## Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/Siddharth-Dattaram-Pawar/IntelliDoc-A_MultiModal_RAG_based_QA_Chatbot.git
cd IntelliDoc-A_MultiModal_RAG_based_QA_Chatbot
```
## Install dependencies using Poetry:
```bash
poetry install
```

## Set up environment variables:
```bash
AWS_BUCKET_NAME=your_bucket_name
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_scret_access_key
AWS_REGION=your_aws_region
PINECONE_API_KEY="your-pinecone-api-key"
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=your_index_name
SNOWFLAKE_ACCOUNT=your_snowflake_account_name
SNOWFLAKE_USER=your_snowflake_username
SNOWFLAKE_PASSWORD=your_snowflake_password
SNOWFLAKE_DATABASE=your_snowflake_database
SNOWFLAKE_SCHEMA=your_snowflake_schema
SNOWFLAKE_WAREHOUSE=your_snowflake_warehouse_name
NVIDIA_API_KEY="your-nvidia-api-key"
```

## Deployment

* **Build Docker images:**
```bash
docker-compose build
```

* **Deploy to AWS:**
```bash
* Make sure your AWS credentials are set correctly to access the S3 bucket containing the task files as well as the RDS database containing user data.
```


## Support

For support, please open an issue in the GitHub repository or contact the development team.

## Contribution

| **Contributor**       | **Contribution Percentage** |
|------------------------|-----------------------------|
| **Vaishnavi Veerkumar** | 33%                        |
| **Sriram Venkatesh**    | 33%                        |
| **Siddharth Pawar**      | 33%                        |


## License
-------

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Acknowledgments

* CFA Institute Research Foundation
* NVIDIA for AI services
* Open source community
