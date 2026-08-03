terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
}

# one dataset per dbt schema (staging/intermediate/marts/snapshots), matching
# the +schema config in dbt_project.yml. dbt creates and owns the tables
# within these; terraform only owns dataset existence and location.
resource "google_bigquery_dataset" "staging" {
  dataset_id = "${var.dataset_prefix}_staging"
  location   = var.location
}

resource "google_bigquery_dataset" "intermediate" {
  dataset_id = "${var.dataset_prefix}_intermediate"
  location   = var.location
}

resource "google_bigquery_dataset" "marts" {
  dataset_id = "${var.dataset_prefix}_marts"
  location   = var.location
}

resource "google_bigquery_dataset" "snapshots" {
  dataset_id = "${var.dataset_prefix}_snapshots"
  location   = var.location
}
