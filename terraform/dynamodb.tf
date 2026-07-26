// One logical record exists per partner. This table contains non-secret partner
// configuration: callback endpoint, outbound format, timeout and retry settings,
// enabled status, and a reference to the related Secrets Manager secret.
// Message-specific data must not be stored in this table.
resource "aws_dynamodb_table" "partner_configuration" {
  name         = "${local.common_name_prefix}-PartnerConfiguration"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "partnerId"

  attribute {
    name = "partnerId"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-PartnerConfiguration"
  })
}

// Stores durable message lifecycle, retry, correlation, and idempotency state.
// processingStatus and deliveryStatus are independent, non-key properties on
// each item so processing progress is not conflated with callback delivery.
resource "aws_dynamodb_table" "integration_message_state" {
  name         = "${local.common_name_prefix}-IntegrationMessageState"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "correlationId"

  attribute {
    name = "correlationId"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-IntegrationMessageState"
  })
}
