variable "project_id" {
  description = "GCP project id (a BigQuery Sandbox project with no billing account is fine)"
  type        = string
}

variable "location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

variable "dataset_prefix" {
  description = "prefix applied to every dataset this project creates, to avoid collisions in a shared project"
  type        = string
  default     = "gharchive"
}
