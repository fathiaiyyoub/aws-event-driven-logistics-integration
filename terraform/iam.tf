data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    sid     = "LambdaServiceTrust"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "adapter_lambda" {
  name               = "${local.common_name_prefix}-adapter-lambda-role"
  description        = "Execution role for the Adapter Lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-adapter-lambda-role"
  })
}

resource "aws_iam_role" "worker_lambda" {
  name               = "${local.common_name_prefix}-worker-lambda-role"
  description        = "Execution role for the Worker Lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-worker-lambda-role"
  })
}

resource "aws_iam_role" "response_lambda" {
  name               = "${local.common_name_prefix}-response-lambda-role"
  description        = "Execution role for the Response Lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-response-lambda-role"
  })
}

locals {
  lambda_basic_execution_policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  lambda_vpc_access_policy_arn      = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "adapter_basic_execution" {
  role       = aws_iam_role.adapter_lambda.name
  policy_arn = local.lambda_basic_execution_policy_arn
}

resource "aws_iam_role_policy_attachment" "worker_basic_execution" {
  role       = aws_iam_role.worker_lambda.name
  policy_arn = local.lambda_basic_execution_policy_arn
}

resource "aws_iam_role_policy_attachment" "response_basic_execution" {
  role       = aws_iam_role.response_lambda.name
  policy_arn = local.lambda_basic_execution_policy_arn
}

// Adapter and Response run in private subnets and therefore require permissions
// to manage Lambda-created elastic network interfaces. Worker remains outside the VPC.
resource "aws_iam_role_policy_attachment" "adapter_vpc_access" {
  role       = aws_iam_role.adapter_lambda.name
  policy_arn = local.lambda_vpc_access_policy_arn
}

resource "aws_iam_role_policy_attachment" "response_vpc_access" {
  role       = aws_iam_role.response_lambda.name
  policy_arn = local.lambda_vpc_access_policy_arn
}

data "aws_iam_policy_document" "adapter_permissions" {
  statement {
    sid       = "CreateMessageState"
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.integration_message_state.arn]
  }

  statement {
    sid       = "PublishShipmentEvents"
    effect    = "Allow"
    actions   = ["events:PutEvents"]
    resources = [aws_cloudwatch_event_bus.integration.arn]
  }
}

resource "aws_iam_role_policy" "adapter_permissions" {
  name   = "${local.common_name_prefix}-adapter-permissions"
  role   = aws_iam_role.adapter_lambda.id
  policy = data.aws_iam_policy_document.adapter_permissions.json
}

data "aws_iam_policy_document" "worker_permissions" {
  statement {
    sid       = "UpdateProcessingState"
    effect    = "Allow"
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.integration_message_state.arn]
  }

  statement {
    sid       = "PublishProcessingResponses"
    effect    = "Allow"
    actions   = ["events:PutEvents"]
    resources = [aws_cloudwatch_event_bus.integration.arn]
  }

  // Least-privilege SQS consumption permissions are defined with the queue in sqs.tf.
}

resource "aws_iam_role_policy" "worker_permissions" {
  name   = "${local.common_name_prefix}-worker-permissions"
  role   = aws_iam_role.worker_lambda.id
  policy = data.aws_iam_policy_document.worker_permissions.json
}

data "aws_iam_policy_document" "response_permissions" {
  statement {
    sid       = "ReadPartnerConfiguration"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.partner_configuration.arn]
  }

  statement {
    sid       = "UpdateDeliveryState"
    effect    = "Allow"
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.integration_message_state.arn]
  }

  statement {
    sid       = "ReadSamplePartnerCredentials"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.sample_partner_callback_credentials.arn]
  }

  // Least-privilege SQS and EventBridge permissions will be added after those
  // resources exist and their specific ARNs are available.
}

resource "aws_iam_role_policy" "response_permissions" {
  name   = "${local.common_name_prefix}-response-permissions"
  role   = aws_iam_role.response_lambda.id
  policy = data.aws_iam_policy_document.response_permissions.json
}
