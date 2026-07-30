locals {
  lambda_source_root = "${path.module}/../lambdas"

  adapter_function_name  = "${local.common_name_prefix}-adapter"
  worker_function_name   = "${local.common_name_prefix}-worker"
  response_function_name = "${local.common_name_prefix}-response"

  adapter_package_files = concat(
    [{ source = "${local.lambda_source_root}/__init__.py", archive = "lambdas/__init__.py" }],
    [for file in fileset("${local.lambda_source_root}/adapter", "**/*.py") : {
      source  = "${local.lambda_source_root}/adapter/${file}"
      archive = "lambdas/adapter/${file}"
    }],
    [for file in fileset("${local.lambda_source_root}/common", "**/*.py") : {
      source  = "${local.lambda_source_root}/common/${file}"
      archive = "lambdas/common/${file}"
    }]
  )

  worker_package_files = concat(
    [{ source = "${local.lambda_source_root}/__init__.py", archive = "lambdas/__init__.py" }],
    [for file in fileset("${local.lambda_source_root}/worker", "**/*.py") : {
      source  = "${local.lambda_source_root}/worker/${file}"
      archive = "lambdas/worker/${file}"
    }],
    [for file in fileset("${local.lambda_source_root}/common", "**/*.py") : {
      source  = "${local.lambda_source_root}/common/${file}"
      archive = "lambdas/common/${file}"
    }]
  )

  response_package_files = concat(
    [{ source = "${local.lambda_source_root}/__init__.py", archive = "lambdas/__init__.py" }],
    [for file in fileset("${local.lambda_source_root}/response_processor", "**/*.py") : {
      source  = "${local.lambda_source_root}/response_processor/${file}"
      archive = "lambdas/response_processor/${file}"
    }],
    [for file in fileset("${local.lambda_source_root}/common", "**/*.py") : {
      source  = "${local.lambda_source_root}/common/${file}"
      archive = "lambdas/common/${file}"
    }],
    [
      {
        source  = "${local.lambda_source_root}/adapter/__init__.py"
        archive = "lambdas/adapter/__init__.py"
      },
      {
        source  = "${local.lambda_source_root}/adapter/serializer.py"
        archive = "lambdas/adapter/serializer.py"
      },
    ]
  )
}

data "archive_file" "adapter" {
  type        = "zip"
  output_path = "${path.module}/adapter_lambda.zip"

  dynamic "source" {
    for_each = { for file in local.adapter_package_files : file.archive => file }
    content {
      content  = file(source.value.source)
      filename = source.value.archive
    }
  }
}

data "archive_file" "worker" {
  type        = "zip"
  output_path = "${path.module}/worker_lambda.zip"

  dynamic "source" {
    for_each = { for file in local.worker_package_files : file.archive => file }
    content {
      content  = file(source.value.source)
      filename = source.value.archive
    }
  }
}

data "archive_file" "response" {
  type        = "zip"
  output_path = "${path.module}/response_lambda.zip"

  dynamic "source" {
    for_each = { for file in local.response_package_files : file.archive => file }
    content {
      content  = file(source.value.source)
      filename = source.value.archive
    }
  }
}

resource "aws_lambda_function" "adapter" {
  function_name    = local.adapter_function_name
  description      = "Accepts partner shipment requests and publishes canonical events"
  role             = aws_iam_role.adapter_lambda.arn
  runtime          = "python3.13"
  handler          = "lambdas.adapter.lambda_function.lambda_handler"
  filename         = data.archive_file.adapter.output_path
  source_code_hash = data.archive_file.adapter.output_base64sha256
  memory_size      = 256
  timeout          = 30
  layers           = [var.secrets_extension_layer_arn]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_integration.id]
  }

  environment {
    variables = {
      EVENT_BUS_NAME         = aws_cloudwatch_event_bus.integration.name
      MESSAGE_STATE_TABLE    = aws_dynamodb_table.integration_message_state.name
      MESSAGE_STATE_TTL_DAYS = "30"
    }
  }

  tags = merge(local.common_tags, {
    Name = local.adapter_function_name
  })

  depends_on = [aws_cloudwatch_log_group.lambda_adapter]
}

resource "aws_lambda_function" "worker" {
  function_name    = local.worker_function_name
  description      = "Processes canonical shipment events from SQS"
  role             = aws_iam_role.worker_lambda.arn
  runtime          = "python3.13"
  handler          = "lambdas.worker.lambda_function.lambda_handler"
  filename         = data.archive_file.worker.output_path
  source_code_hash = data.archive_file.worker.output_base64sha256
  memory_size      = 256
  timeout          = 60

  environment {
    variables = {
      EVENT_BUS_NAME           = aws_cloudwatch_event_bus.integration.name
      MESSAGE_STATE_TABLE      = aws_dynamodb_table.integration_message_state.name
      PROCESSING_LEASE_SECONDS = "120"
    }
  }

  tags = merge(local.common_tags, {
    Name = local.worker_function_name
  })

  depends_on = [aws_cloudwatch_log_group.lambda_worker]
}

resource "aws_lambda_function" "response" {
  function_name    = local.response_function_name
  description      = "Delivers processing responses to configured partner endpoints"
  role             = aws_iam_role.response_lambda.arn
  runtime          = "python3.13"
  handler          = "lambdas.response_processor.lambda_function.lambda_handler"
  filename         = data.archive_file.response.output_path
  source_code_hash = data.archive_file.response.output_base64sha256
  memory_size      = 256
  timeout          = 60
  layers           = [var.secrets_extension_layer_arn]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_integration.id]
  }

  environment {
    variables = {
      PARTNER_CONFIG_TABLE              = aws_dynamodb_table.partner_configuration.name
      MAX_DELIVERY_ATTEMPTS             = "3"
      DELIVERY_LEASE_SECONDS            = "120"
      MESSAGE_STATE_TABLE               = aws_dynamodb_table.integration_message_state.name
      SECRETS_EXTENSION_TIMEOUT_SECONDS = "3"
    }
  }

  tags = merge(local.common_tags, {
    Name = local.response_function_name
  })

  depends_on = [aws_cloudwatch_log_group.lambda_response]
}

resource "aws_lambda_event_source_mapping" "shipment_processing" {
  event_source_arn                   = aws_sqs_queue.shipment_processing.arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = true
}

resource "aws_lambda_event_source_mapping" "response" {
  event_source_arn                   = aws_sqs_queue.response.arn
  function_name                      = aws_lambda_function.response.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = true
}
