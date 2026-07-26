resource "aws_sqs_queue" "shipment_processing_dlq" {
  name                      = "${local.common_name_prefix}-shipment-processing-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-shipment-processing-dlq"
  })
}

resource "aws_sqs_queue" "shipment_processing" {
  name                       = "${local.common_name_prefix}-shipment-processing"
  visibility_timeout_seconds = 180
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.shipment_processing_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-shipment-processing"
  })
}

resource "aws_sqs_queue" "response_dlq" {
  name                      = "${local.common_name_prefix}-response-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-response-dlq"
  })
}

resource "aws_sqs_queue" "response" {
  name                       = "${local.common_name_prefix}-response"
  visibility_timeout_seconds = 180
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.response_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-response"
  })
}

data "aws_iam_policy_document" "shipment_processing_queue" {
  statement {
    sid     = "AllowShipmentRequestRule"
    effect  = "Allow"
    actions = ["sqs:SendMessage"]
    resources = [
      aws_sqs_queue.shipment_processing.arn,
    ]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.shipment_requests.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "shipment_processing" {
  queue_url = aws_sqs_queue.shipment_processing.id
  policy    = data.aws_iam_policy_document.shipment_processing_queue.json
}

data "aws_iam_policy_document" "response_queue" {
  statement {
    sid     = "AllowProcessingResponseRule"
    effect  = "Allow"
    actions = ["sqs:SendMessage"]
    resources = [
      aws_sqs_queue.response.arn,
    ]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.processing_responses.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "response" {
  queue_url = aws_sqs_queue.response.id
  policy    = data.aws_iam_policy_document.response_queue.json
}

data "aws_iam_policy_document" "worker_sqs_permissions" {
  statement {
    sid    = "ConsumeShipmentProcessingQueue"
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
    ]
    resources = [aws_sqs_queue.shipment_processing.arn]
  }
}

resource "aws_iam_role_policy" "worker_sqs_permissions" {
  name   = "${local.common_name_prefix}-worker-sqs-permissions"
  role   = aws_iam_role.worker_lambda.id
  policy = data.aws_iam_policy_document.worker_sqs_permissions.json
}

data "aws_iam_policy_document" "response_sqs_permissions" {
  statement {
    sid    = "ConsumeResponseQueue"
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
    ]
    resources = [aws_sqs_queue.response.arn]
  }
}

resource "aws_iam_role_policy" "response_sqs_permissions" {
  name   = "${local.common_name_prefix}-response-sqs-permissions"
  role   = aws_iam_role.response_lambda.id
  policy = data.aws_iam_policy_document.response_sqs_permissions.json
}
