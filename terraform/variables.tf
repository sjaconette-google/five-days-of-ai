variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "sjaconette-experiment"
}

variable "region" {
  description = "GCP Deployment Region"
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "Artifact Registry container image URI for Cloud Run"
  type        = string
  default     = "us-central1-docker.pkg.dev/sjaconette-experiment/gtd-agent-repo/gtd-ef-agent:latest"
}


