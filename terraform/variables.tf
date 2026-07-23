variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "gtd-ef-agent-gcp-project"
}

variable "region" {
  description = "GCP Deployment Region"
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "Artifact Registry container image URI for Cloud Run"
  type        = string
  default     = "us-central1-docker.pkg.dev/gtd-ef-agent-gcp-project/gtd-agent-repo/gtd-ef-agent:latest"
}
