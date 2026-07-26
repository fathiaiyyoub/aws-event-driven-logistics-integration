resource "aws_cloudwatch_event_bus" "integration" {
  name = "${local.common_name_prefix}-integration-bus"

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-integration-bus"
  })
}

resource "aws_cloudwatch_event_rule" "shipment_requests" {
  name           = "${local.common_name_prefix}-shipment-requests"
  description    = "Routes shipment request events to the processing queue"
  event_bus_name = aws_cloudwatch_event_bus.integration.name

  event_pattern = jsonencode({
    source = ["legacy.logistics.adapter"]
    detail-type = [
      "CreateShipment",
      "UpdateShipmentStatus",
      "RetrieveShipment",
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-shipment-requests"
  })
}

resource "aws_cloudwatch_event_rule" "processing_responses" {
  name           = "${local.common_name_prefix}-processing-responses"
  description    = "Routes shipment processing responses to the response queue"
  event_bus_name = aws_cloudwatch_event_bus.integration.name

  event_pattern = jsonencode({
    source      = ["legacy.logistics.worker"]
    detail-type = ["ProcessingResponse"]
  })

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-processing-responses"
  })
}

resource "aws_cloudwatch_event_rule" "analytics_events" {
  name           = "${local.common_name_prefix}-analytics-events"
  description    = "Matches integration analytics events for the future Firehose target"
  event_bus_name = aws_cloudwatch_event_bus.integration.name

  // Mirror the two exact canonical application contracts to analytics. Using
  // $or avoids creating unintended source/detail-type combinations.
  event_pattern = jsonencode({
    "$or" = [
      {
        source = ["legacy.logistics.adapter"]
        detail-type = [
          "CreateShipment",
          "UpdateShipmentStatus",
          "RetrieveShipment",
        ]
      },
      {
        source      = ["legacy.logistics.worker"]
        detail-type = ["ProcessingResponse"]
      },
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-analytics-events"
  })
}

data "aws_iam_policy_document" "eventbridge_assume_role" {
  statement {
    sid     = "EventBridgeServiceTrust"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbridge_sqs" {
  name               = "${local.common_name_prefix}-eventbridge-sqs-role"
  description        = "Allows integration EventBridge rules to deliver events to SQS"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-eventbridge-sqs-role"
  })
}

data "aws_iam_policy_document" "eventbridge_sqs" {
  statement {
    sid     = "SendToIntegrationQueues"
    effect  = "Allow"
    actions = ["sqs:SendMessage"]
    resources = [
      aws_sqs_queue.shipment_processing.arn,
      aws_sqs_queue.response.arn,
    ]
  }
}

resource "aws_iam_role_policy" "eventbridge_sqs" {
  name   = "${local.common_name_prefix}-eventbridge-sqs"
  role   = aws_iam_role.eventbridge_sqs.id
  policy = data.aws_iam_policy_document.eventbridge_sqs.json
}

resource "aws_cloudwatch_event_target" "shipment_processing_queue" {
  event_bus_name = aws_cloudwatch_event_bus.integration.name
  rule           = aws_cloudwatch_event_rule.shipment_requests.name
  target_id      = "ShipmentProcessingQueue"
  arn            = aws_sqs_queue.shipment_processing.arn
  role_arn       = aws_iam_role.eventbridge_sqs.arn
}

resource "aws_cloudwatch_event_target" "response_queue" {
  event_bus_name = aws_cloudwatch_event_bus.integration.name
  rule           = aws_cloudwatch_event_rule.processing_responses.name
  target_id      = "ResponseQueue"
  arn            = aws_sqs_queue.response.arn
  role_arn       = aws_iam_role.eventbridge_sqs.arn
}

resource "aws_iam_role" "eventbridge_firehose" {
  name               = "${local.common_name_prefix}-eventbridge-firehose-role"
  description        = "Allows the analytics EventBridge rule to publish to Firehose"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-eventbridge-firehose-role"
  })
}

data "aws_iam_policy_document" "eventbridge_firehose" {
  statement {
    sid    = "PublishAnalyticsRecords"
    effect = "Allow"
    actions = [
      "firehose:PutRecord",
      "firehose:PutRecordBatch",
    ]
    resources = [aws_kinesis_firehose_delivery_stream.integration_analytics.arn]
  }
}

resource "aws_iam_role_policy" "eventbridge_firehose" {
  name   = "${local.common_name_prefix}-eventbridge-firehose"
  role   = aws_iam_role.eventbridge_firehose.id
  policy = data.aws_iam_policy_document.eventbridge_firehose.json
}

resource "aws_cloudwatch_event_target" "analytics_firehose" {
  event_bus_name = aws_cloudwatch_event_bus.integration.name
  rule           = aws_cloudwatch_event_rule.analytics_events.name
  target_id      = "IntegrationAnalyticsFirehose"
  arn            = aws_kinesis_firehose_delivery_stream.integration_analytics.arn
  role_arn       = aws_iam_role.eventbridge_firehose.arn

  // Strip the outer EventBridge envelope so Firehose conversion receives the
  // canonical event object described by the Glue schema.
  input_path = "$.detail"
}
