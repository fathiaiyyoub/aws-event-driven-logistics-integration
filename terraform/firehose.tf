data "aws_iam_policy_document" "firehose_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "firehose" {
  name               = "${local.common_name_prefix}-firehose-role"
  description        = "Allows Firehose to convert and deliver integration analytics events"
  assume_role_policy = data.aws_iam_policy_document.firehose_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-firehose-role"
  })
}

data "aws_iam_policy_document" "firehose" {
  statement {
    sid    = "InspectDataLakeLocation"
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucketMultipartUploads",
    ]
    resources = [aws_s3_bucket.data_lake.arn]
  }

  statement {
    sid       = "ListDeliveryPrefixes"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data_lake.arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        "integration-events",
        "integration-events/*",
        "firehose-errors",
        "firehose-errors/*",
      ]
    }
  }

  statement {
    sid    = "DeliverDataLakeObjects"
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetObject",
      "s3:ListMultipartUploadParts",
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.data_lake.arn}/integration-events/*",
      "${aws_s3_bucket.data_lake.arn}/firehose-errors/*",
    ]
  }

  statement {
    sid    = "ReadGlueSchema"
    effect = "Allow"
    actions = [
      "glue:GetTable",
      "glue:GetTableVersion",
      "glue:GetTableVersions",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
      aws_glue_catalog_database.integration_analytics.arn,
      aws_glue_catalog_table.integration_events.arn,
    ]
  }

  statement {
    sid       = "WriteFirehoseLogs"
    effect    = "Allow"
    actions   = ["logs:PutLogEvents"]
    resources = [aws_cloudwatch_log_stream.firehose.arn]
  }
}

resource "aws_iam_role_policy" "firehose" {
  name   = "${local.common_name_prefix}-firehose-delivery"
  role   = aws_iam_role.firehose.id
  policy = data.aws_iam_policy_document.firehose.json
}

// Firehose batches many EventBridge records into larger S3 objects, reducing
// small-file inflation. Parquet with Snappy compression and date partitions
// reduces the amount of data Athena must scan for typical time-bounded queries.
resource "aws_kinesis_firehose_delivery_stream" "integration_analytics" {
  name        = "${local.common_name_prefix}-integration-analytics"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose.arn
    bucket_arn = aws_s3_bucket.data_lake.arn

    prefix              = "integration-events/year=!{partitionKeyFromQuery:year}/month=!{partitionKeyFromQuery:month}/day=!{partitionKeyFromQuery:day}/"
    error_output_prefix = "firehose-errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"

    buffering_size     = 64
    buffering_interval = 300
    compression_format = "UNCOMPRESSED"

    dynamic_partitioning_configuration {
      enabled        = true
      retry_duration = 300
    }

    processing_configuration {
      enabled = true

      processors {
        type = "MetadataExtraction"

        parameters {
          parameter_name  = "MetadataExtractionQuery"
          parameter_value = "{year:.timestamp[0:4],month:.timestamp[5:7],day:.timestamp[8:10]}"
        }

        parameters {
          parameter_name  = "JsonParsingEngine"
          parameter_value = "JQ-1.6"
        }
      }
    }

    data_format_conversion_configuration {
      enabled = true

      input_format_configuration {
        deserializer {
          open_x_json_ser_de {
            case_insensitive                         = true
            convert_dots_in_json_keys_to_underscores = false
          }
        }
      }

      output_format_configuration {
        serializer {
          parquet_ser_de {
            compression = "SNAPPY"
          }
        }
      }

      schema_configuration {
        catalog_id    = data.aws_caller_identity.current.account_id
        database_name = aws_glue_catalog_database.integration_analytics.name
        region        = var.aws_region
        role_arn      = aws_iam_role.firehose.arn
        table_name    = aws_glue_catalog_table.integration_events.name
        version_id    = "LATEST"
      }
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose.name
      log_stream_name = aws_cloudwatch_log_stream.firehose.name
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-integration-analytics"
  })

  depends_on = [
    aws_iam_role_policy.firehose,
    aws_s3_bucket_public_access_block.data_lake,
    aws_s3_bucket_server_side_encryption_configuration.data_lake,
    aws_s3_bucket_versioning.data_lake,
  ]
}
