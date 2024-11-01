# IntelliDoc

A comprehensive research platform for analyzing CFA Institute Research Foundation Publications using AI-powered search and analysis capabilities.

## Architecture Overview

The platform consists of three main components:
- Data Ingestion Pipeline
- Client-Facing Application 
- Research Notes System

## Infrastructure

- **Cloud Platform**: Google Cloud Platform (GCP)
- **Storage**: 
  - Google Cloud Storage (PDFs and Images)
  - Snowflake (Document metadata and Q&A pairs)
  - Pinecone (Vector embeddings)
- **Compute**: Google Kubernetes Engine (GKE)
- **CI/CD**: Cloud Build

## Prerequisites

- Python 3.9+
- Docker
- Google Cloud SDK
- Poetry
- Access to:
  - GCP Project with required APIs enabled
  - Snowflake account
  - Pinecone account
  - NVIDIA API credentials

### Table of Contents

1. [Architecture Diagram](#architecture-diagram)
2. [Install dependencies using Poetry](#install-dependencies-using-poetry)
3. [Set up environment variables](#set-up-environment-variables)
4. [Components](#components)
5. [Deployment](#deployment)
6. [Access the application](#access-the-application)
7. [Monitoring](#monitoring)
8. [Security](#security)
9. [Contributing](#contributing)
10. [License](#license)
11. [Support](#support)
12. [Authors](#authors)
13. [Acknowledgments](#acknowledgments)

## Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/cfa-research-platform.git
cd cfa-research-platform
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

### Components

1. **Data Ingestion Pipeline**
	* Web scraper for CFA Institute publications
	* Airflow DAGs for automated data processing
	* Data storage in GCS and Snowflake
2. **FastAPI Backend**
	* Document exploration API
	* Integration with NVIDIA services
	* Multi-modal RAG implementation
	* Q&A processing system
3. **Streamlit Frontend**
	* Document grid/list view
	* Summary generation interface
	* Q&A interaction portal
	* Research notes management
4. **Vector Search System**
	* Pinecone vector database integration
	* Incremental indexing system
	* Hybrid search functionality

### Deployment

* **Build Docker images:**
```bash
docker-compose build
```

* **Deploy to Google Cloud:**
```bash
* Make sure your GCP credentials are set correctly to access the GCS bucket containing the task files as well as the SQL Database containing user Data.
```

### Access the application:

* **Frontend:** https://your-domain.com
* **API:** https://api.your-domain.com

### Monitoring

* **Application metrics:** Google Cloud Monitoring
* **Logs:** Google Cloud Logging
* **Tracing:** Cloud Trace

### Security

* **GCP IAM for access control**
* **API authentication using JWT**
* **Data encryption at rest and in transit**
* **Regular security audits**

### Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

### License

This project is licensed under the MIT License - see the LICENSE file for details.

### Support

For support, please open an issue in the GitHub repository or contact the development team.

### Authors

* Member 1
* Member 2
* Member 3

### Acknowledgments

* CFA Institute Research Foundation
* NVIDIA for AI services
* Open source community