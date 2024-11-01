# IntelliDoc

## Project Overview

This project involves developing a FastAPI and Streamlit-based document exploration application for clients to securely access, explore, and analyze research publications from the CFA Institute Research Foundation. The application facilitates efficient data ingestion, document interaction, and multi-modal querying with capabilities for summarization and research note generation.

Codelab [Link](https://codelabs-preview.appspot.com/?file_id=1ZKUCJ26fZkN3CAf_9Ul-TJlIDZqkYzMIgs5npvLNNTw/edit?tab=t.0#0) (Includes Youtube Video)

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

Key Technologies and Roles

FastAPI: Backend framework for user authentication, document retrieval, and summarization APIs

Streamlit: Frontend application framework for document exploration and interaction

CFA Institute Research Foundation Publications: Source of data for the research documents

Airflow & Selenium: Tools for automating data ingestion and web scraping

AWS S3: Storage for images and PDFs associated with research documents

Snowflake: Data warehouse to store metadata, research notes, and user data

NVIDIA meta llama-3.1-8b-instruct : Advanced state-of-the-art model with language understanding, superior reasoning, and text generation.

NVIDIA DePlot: Converts graphs and plots from documents into descriptive text, making visual data accessible for text-based search and analysis.

NVIDIA NeVA 22B: Transforms images within documents into text representations, allowing comprehensive querying across visual data types.

NVIDIA embedqa-v5-v6 Model: Generates detailed text embeddings, supporting high-precision, contextually relevant retrieval of document content in the query system.

NVIDIA API Key: Secures and manages access to all NVIDIA functionalities, ensuring authenticated, controlled usage across summarization and querying features.

Pinecone: Vector database for storing and retrieving embeddings for context-based search

Docker: Containerization tool for packaging the FastAPI and Streamlit applications to streamline deployment on cloud platforms

## Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/BigDataIA-Fall2024-TeamA4/Assignmnet3.git
cd Assignmnet3
```
### Install dependencies using Poetry:
```bash
poetry install
```

### Set up environment variables:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
export SNOWFLAKE_ACCOUNT="your-account"
export PINECONE_API_KEY="your-api-key"
export NVIDIA_API_KEY="your-api-key"
```

### Deployment

* **Build Docker images:**
```bash
docker-compose build
```

* **Deploy to AWS:**
```bash
* Make sure your AWS credentials are set correctly to access the S3 bucket containing the task files as well as the RDS database containing user data.
```



### License

This project is licensed under the MIT License - see the LICENSE file for details.

### Support

For support, please open an issue in the GitHub repository or contact the development team.

## Contribution

Vaishnavi Veerkumar : Webscraping using selenium, Airflow automation, Snowflake integration for the scrapped elements, S3 storage for the scrapped elements, Summarization model using Nvidia services, Vector embedding of PDF and user input using Nvidia series, Streamlit UI

Sriram Venkatesh : Streamlit UI development with interactive components, FastAPI backend implementation, System architecture diagrams using Python Diagrams, Pinecone index creation, Vector embeddings of PDF documents, NVIDIA model integration for text and image processing, Logging system, JWT authentication and authorization flow

Siddharth Pawar :


### Acknowledgments

* CFA Institute Research Foundation
* NVIDIA for AI services
* Open source community
