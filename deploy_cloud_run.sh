#!/bin/bash
set -e

cd "$(dirname "$0")"

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at $ENV_FILE"
  echo "Copy .env.example to .env and fill in values first."
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID is required in .env"
  exit 1
fi

REGION=${REGION:-us-central1}

echo "------------------------------------------------"
echo "Starting Cloud Build Deployment"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "------------------------------------------------"

gcloud builds submit --config cloudbuild.yaml \
  --project "$PROJECT_ID" \
  --substitutions _REGION="$REGION",_GOOGLE_GENAI_USE_VERTEXAI="$GOOGLE_GENAI_USE_VERTEXAI",_GOOGLE_API_KEY="$GOOGLE_API_KEY",_VECTOR_COLLECTION_ID="$VECTOR_COLLECTION_ID",_VECTOR_FIELD="$VECTOR_FIELD",_ENABLE_BASIC_GUARDRAILS="$ENABLE_BASIC_GUARDRAILS",_MODEL_ID="$MODEL_ID"

echo "------------------------------------------------"
echo "Deployment submitted."
echo "Frontend URL: $(gcloud run services describe raven-frontend --region "$REGION" --format 'value(status.url)' 2>/dev/null || echo 'not yet available')"
echo "------------------------------------------------"
