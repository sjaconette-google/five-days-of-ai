#!/usr/bin/env bash
set -e

PROJECT_ID="google.com:sjaconette"
REGION="us-central1"
SERVICE_NAME="gtd-ef-agent-service"
REPO_NAME="gtd-agent-repo"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:latest"

echo "============================================================"
echo " Deploying GTD & Workload Focus Agent to GCP Project: ${PROJECT_ID}"
echo "============================================================"

# Set active project
gcloud config set project "${PROJECT_ID}" --quiet

# Enable required Google Cloud APIs
echo "Enabling Cloud Run, Artifact Registry, DLP, and Secret Manager APIs..."
gcloud services enable run.googleapis.com \
                       artifactregistry.googleapis.com \
                       dlp.googleapis.com \
                       secretmanager.googleapis.com --quiet

# Create Artifact Registry Repository if not present
echo "Ensuring Artifact Registry repository exists..."
gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Docker repository for GTD Workload Focus Agent" 2>/dev/null || true

# Build and Push container image using Cloud Builds (no local Docker daemon dependency required)
echo "Building and pushing container image via Cloud Build..."
gcloud builds submit --tag "${IMAGE_URI}" . --quiet

# Deploy containerized microservice to Cloud Run
echo "Deploying containerized microservice to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_URI}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --set-env-vars="ENV=production,LOG_LEVEL=INFO,GEMINI_FLASH_MODEL=gemini-2.5-flash,GEMINI_PRO_MODEL=gemini-2.5-pro" \
    --quiet

# Fetch deployed service endpoint URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format="value(status.url)")

echo "============================================================"
echo " DEPLOYMENT SUCCESSFUL!"
echo " Cloud Run Service Endpoint: ${SERVICE_URL}"
echo " Health Probe Endpoint     : ${SERVICE_URL}/health"
echo " Turn API Endpoint         : ${SERVICE_URL}/api/v1/turn"
echo "============================================================"
