output "dataset_ids" {
  value = {
    staging      = google_bigquery_dataset.staging.dataset_id
    intermediate = google_bigquery_dataset.intermediate.dataset_id
    marts        = google_bigquery_dataset.marts.dataset_id
    snapshots    = google_bigquery_dataset.snapshots.dataset_id
  }
}
