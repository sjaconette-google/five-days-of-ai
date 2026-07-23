output "cloud_run_service_url" {
  description = "Deployed Cloud Run Service URL"
  value       = google_cloud_run_v2_service.gtd_agent_service.uri
}

output "postgres_instance_connection_name" {
  description = "Cloud SQL Connection Name"
  value       = google_sql_database_instance.postgres_instance.connection_name
}
