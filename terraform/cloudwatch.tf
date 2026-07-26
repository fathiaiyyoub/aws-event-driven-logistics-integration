// Production deployments should route these alarms to a paging or incident-management
// platform. This portfolio deployment intentionally has no notification actions.
resource "aws_cloudwatch_metric_alarm" "shipment_dlq_messages" {
  alarm_name          = "${local.common_name_prefix}-shipment-dlq-messages"
  alarm_description   = "Shipment processing messages have reached the dead-letter queue."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.shipment_processing_dlq.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "response_dlq_messages" {
  alarm_name          = "${local.common_name_prefix}-response-dlq-messages"
  alarm_description   = "Response messages have reached the dead-letter queue."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.response_dlq.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "shipment_queue_backlog" {
  alarm_name          = "${local.common_name_prefix}-shipment-queue-backlog"
  alarm_description   = "Shipment processing queue has more than 100 visible messages for five minutes."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 100
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.shipment_processing.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "response_queue_backlog" {
  alarm_name          = "${local.common_name_prefix}-response-queue-backlog"
  alarm_description   = "Response queue has more than 100 visible messages for five minutes."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 100
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.response.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "firehose" {
  name              = "/aws/kinesisfirehose/${local.common_name_prefix}-integration-analytics"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_stream" "firehose" {
  name           = "S3Delivery"
  log_group_name = aws_cloudwatch_log_group.firehose.name
}

resource "aws_cloudwatch_log_group" "lambda_adapter" {
  name              = "/aws/lambda/${local.adapter_function_name}"
  retention_in_days = var.lambda_log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.adapter_function_name}-logs"
  })
}

resource "aws_cloudwatch_log_group" "lambda_worker" {
  name              = "/aws/lambda/${local.worker_function_name}"
  retention_in_days = var.lambda_log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.worker_function_name}-logs"
  })
}

resource "aws_cloudwatch_log_group" "lambda_response" {
  name              = "/aws/lambda/${local.response_function_name}"
  retention_in_days = var.lambda_log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.response_function_name}-logs"
  })
}

// Production deployments should route these alarms to an incident-management
// platform. This portfolio deployment intentionally has no notification actions.
resource "aws_cloudwatch_metric_alarm" "firehose_delivery_failure" {
  alarm_name          = "${local.common_name_prefix}-firehose-delivery-failure"
  alarm_description   = "Firehose failed to complete an S3 delivery attempt."
  namespace           = "AWS/Firehose"
  metric_name         = "DeliveryToS3.Success"
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DeliveryStreamName = aws_kinesis_firehose_delivery_stream.integration_analytics.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "firehose_data_freshness" {
  alarm_name          = "${local.common_name_prefix}-firehose-data-freshness"
  alarm_description   = "The oldest undelivered Firehose record is more than 15 minutes old."
  namespace           = "AWS/Firehose"
  metric_name         = "DeliveryToS3.DataFreshness"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 900
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DeliveryStreamName = aws_kinesis_firehose_delivery_stream.integration_analytics.name
  }

  tags = local.common_tags
}
