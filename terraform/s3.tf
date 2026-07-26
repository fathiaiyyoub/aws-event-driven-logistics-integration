// Firehose buffers canonical integration events and writes aggregated Parquet
// objects beneath logical prefixes; EventBridge never writes objects directly.
resource "aws_s3_bucket" "data_lake" {
  bucket        = "${local.common_name_prefix}-data-lake-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  force_destroy = var.data_lake_force_destroy

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-data-lake"
  })
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "integration-events-retention"
    status = "Enabled"

    filter {
      prefix = "integration-events/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "conversion-errors-retention"
    status = "Enabled"

    filter {
      prefix = "firehose-errors/"
    }

    expiration {
      days = 30
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }

  rule {
    id     = "athena-results-retention"
    status = "Enabled"

    filter {
      prefix = "athena-results/"
    }

    expiration {
      days = 14
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.data_lake]
}
