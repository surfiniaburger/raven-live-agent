# Proof of Google Cloud Platform (GCP) Deployment & API Usage

This document identifies the specific locations in the RAVEN codebase that demonstrate production-ready deployment to Google Cloud and the use of Vertex AI 2.0 services.

## 1. Proof of Google Cloud Deployment
The following files demonstrate the automated build and deployment pipeline for Google Cloud Run.

- **cloudbuild.yaml**:
  - **Function**: Defines the multi-stage CI/CD pipeline using Google Cloud Build.
  - **GCP Services**: Uses `cloud-builders/docker` to build containers and `cloud-sdk` to deploy to **Cloud Run**.
  - **Anchor**: `# GCP_PROOF: Cloud Build Pipeline`

- **deploy_cloud_run.sh**:
  - **Function**: The entry-point script to trigger GCP deployments from a management environment.
  - **GCP Command**: Uses `gcloud builds submit` to send the source to Google Cloud.
  - **Anchor**: `# GCP_PROOF: GCloud Run Deployment`

## 2. Proof of Google Cloud API Usage
The following files demonstrate direct integration with Google Cloud's AI and data services.

- **backend/app/grounding/vector_store.py**:
  - **Function**: Implements **Vertex AI Vector Search 2.0** (Hybrid Search).
  - **API Proof**: Uses `VectorSearchServiceClient` and `DataObjectSearchServiceClient` for hybrid semantic/text retrieval.
  - **Anchors**: `# GCP_PROOF: Vertex AI Vector Search Config`, `# GCP_PROOF: Vertex AI Search Clients`

- **backend/app/main.py**:
  - **Function**: The core WebSocket server using the **Google ADK**.
  - **API Interaction**: Orchestrates **Gemini Live API** sessions on GCP infrastructure.
  - **Anchor**: `# GCP_PROOF: Gemini Live API Orchestration`
