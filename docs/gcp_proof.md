# Proof of Google Cloud Platform (GCP) Deployment & API Usage

This document identifies the specific locations in the RAVEN codebase that demonstrate production-ready deployment to Google Cloud and the use of Vertex AI 2.0 services.

## 1. Proof of Google Cloud Deployment
The following files demonstrate the automated build and deployment pipeline for Google Cloud Run.

- **cloudbuild.yaml**:
  - **Function**: Defines the multi-stage CI/CD pipeline using Google Cloud Build.
  - **GCP Services**: Uses `cloud-builders/docker` to build containers and `cloud-sdk` to deploy to **Cloud Run**.
  - **Locations**: See lines 1-23 for backend deployment and lines 50-61 for frontend deployment.

- **deploy_cloud_run.sh**:
  - **Function**: The entry-point script to trigger GCP deployments from a management environment.
  - **GCP Command**: Uses `gcloud builds submit` (line 30) to send the source to Google Cloud for remote building.

## 2. Proof of Google Cloud API Usage
The following files demonstrate direct integration with Google Cloud's AI and data services.

- **backend/app/grounding/vector_store.py**:
  - **Function**: Implements **Vertex AI Vector Search 2.0** (Hybrid Search).
  - **API Calls**: 
    - `VectorSearchServiceClient` (line 150) for collection management.
    - `DataObjectSearchServiceClient` (line 152) for hybrid semantic/text retrieval.
    - `gemini-embedding-001` (line 187) for automatic text embedding within the vector store.

- **backend/app/main.py**:
  - **Function**: The core WebSocket server using the **Google ADK**.
  - **API Interaction**: Uses `google.adk` (lines 12-14) to orchestrate **Gemini Live API** sessions, managing multi-modal streaming and tool-calling loops on GCP infrastructure.
