# Terraform IaC for Cloud Run, Cloud SQL PostgreSQL, Secret Manager, and Cloud KMS

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "postgres_instance" {
  name             = "gtd-ef-postgres-instance"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled = true
    }
  }
}

resource "google_sql_database" "database" {
  name     = "gtd_ef_db"
  instance = google_sql_database_instance.postgres_instance.name
}

# 2. Secret Manager for OAuth Client Secret
resource "google_secret_manager_secret" "oauth_client_secret" {
  secret_id = "gtd-oauth-client-secret"
  replication {
    auto {}
  }
}

# 3. Cloud KMS KeyRing and Key for Token Encryption
resource "google_kms_key_ring" "keyring" {
  name     = "gtd-token-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "crypto_key" {
  name     = "gtd-token-crypto-key"
  key_ring = google_kms_key_ring.keyring.id
}

# 4. Cloud Run Service Instance
resource "google_cloud_run_v2_service" "gtd_agent_service" {
  name     = "gtd-ef-agent-service"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.container_image

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "DATABASE_URL"
        value = "postgresql://postgres:secret@127.0.0.1:5432/gtd_ef_db"
      }
      env {
        name  = "GEMINI_FLASH_MODEL"
        value = "gemini-2.5-flash"
      }
      env {
        name  = "GEMINI_PRO_MODEL"
        value = "gemini-2.5-pro"
      }

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }
    }
  }
}

# 5. IAM Policy for Cloud Run Service
resource "google_cloud_run_v2_service_iam_member" "noauth" {
  location = google_cloud_run_v2_service.gtd_agent_service.location
  name     = google_cloud_run_v2_service.gtd_agent_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
