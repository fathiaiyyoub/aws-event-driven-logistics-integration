// Foundational project metadata; infrastructure outputs will be added later.
output "project_name" {
  description = "Name of the logistics modernization project."
  value       = var.project_name
}

output "aws_region" {
  description = "AWS Region in which project resources are deployed."
  value       = var.aws_region
}

output "data_lake_bucket_name" {
  description = "Name of the private S3 data-lake bucket."
  value       = aws_s3_bucket.data_lake.id
}

output "firehose_delivery_stream_name" {
  description = "Name of the integration analytics Firehose delivery stream."
  value       = aws_kinesis_firehose_delivery_stream.integration_analytics.name
}

output "glue_database_name" {
  description = "Name of the Glue Data Catalog analytics database."
  value       = aws_glue_catalog_database.integration_analytics.name
}

output "glue_table_name" {
  description = "Name of the Glue table containing canonical integration events."
  value       = aws_glue_catalog_table.integration_events.name
}

output "athena_workgroup_name" {
  description = "Name of the cost-controlled Athena analytics workgroup."
  value       = aws_athena_workgroup.integration_analytics.name
}
