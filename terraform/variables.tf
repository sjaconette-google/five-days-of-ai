variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "google.com:sjaconette"
}

variable "region" {
  description = "GCP Deployment Region"
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "Artifact Registry container image URI for Cloud Run"
  type        = string
  default     = "us-central1-docker.pkg.dev/google.com:sjaconette/gtd-agent-repo/gtd-ef-agent:latest"
}

