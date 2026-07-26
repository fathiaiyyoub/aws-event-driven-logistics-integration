resource "aws_athena_workgroup" "integration_analytics" {
  name        = "${local.common_name_prefix}-analytics"
  description = "Cost-controlled Athena queries over integration event Parquet data"
  state       = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = 1073741824

    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_lake.id}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-analytics"
  })
}
