locals {
  api_stage_name = var.environment
}

resource "aws_api_gateway_rest_api" "integration" {
  name        = "${local.common_name_prefix}-api"
  description = "Partner-facing shipment integration API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-api"
  })
}

resource "aws_api_gateway_resource" "shipments" {
  rest_api_id = aws_api_gateway_rest_api.integration.id
  parent_id   = aws_api_gateway_rest_api.integration.root_resource_id
  path_part   = "shipments"
}

resource "aws_api_gateway_resource" "shipment_status" {
  rest_api_id = aws_api_gateway_rest_api.integration.id
  parent_id   = aws_api_gateway_resource.shipment.id
  path_part   = "status"
}

resource "aws_api_gateway_resource" "shipment" {
  rest_api_id = aws_api_gateway_rest_api.integration.id
  parent_id   = aws_api_gateway_resource.shipments.id
  path_part   = "{shipmentId}"
}

resource "aws_api_gateway_request_validator" "parameters" {
  name                        = "validate-request-parameters"
  rest_api_id                 = aws_api_gateway_rest_api.integration.id
  validate_request_body       = false
  validate_request_parameters = true
}

resource "aws_api_gateway_model" "create_shipment" {
  rest_api_id  = aws_api_gateway_rest_api.integration.id
  name         = "CreateShipmentRequest"
  description  = "Canonical CreateShipment contract for internal documentation"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "CreateShipmentRequest"
    type      = "object"
    required  = ["eventType", "eventSource", "payload"]
    properties = {
      eventId       = { type = "string" }
      correlationId = { type = "string" }
      eventType = {
        type = "string"
        enum = ["CreateShipment"]
      }
      eventSource = { type = "string", minLength = 1 }
      timestamp   = { type = "string" }
      payload = {
        type     = "object"
        required = ["shipmentId"]
        properties = {
          shipmentId  = { type = "string", minLength = 1 }
          customer    = { type = "string" }
          destination = { type = "string" }
        }
      }
    }
  })
}

resource "aws_api_gateway_model" "update_shipment_status" {
  rest_api_id  = aws_api_gateway_rest_api.integration.id
  name         = "UpdateShipmentStatusRequest"
  description  = "Canonical UpdateShipmentStatus contract for internal documentation"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "UpdateShipmentStatusRequest"
    type      = "object"
    required  = ["eventType", "eventSource", "payload"]
    properties = {
      eventId       = { type = "string" }
      correlationId = { type = "string" }
      eventType = {
        type = "string"
        enum = ["UpdateShipmentStatus"]
      }
      eventSource = { type = "string", minLength = 1 }
      payload = {
        type     = "object"
        required = ["shipmentId", "status"]
        properties = {
          shipmentId = { type = "string", minLength = 1 }
          status     = { type = "string", minLength = 1 }
        }
      }
    }
  })
}

resource "aws_api_gateway_model" "error" {
  rest_api_id  = aws_api_gateway_rest_api.integration.id
  name         = "IntegrationErrorResponse"
  description  = "Sanitised client-facing error response"
  content_type = "application/json"

  schema = jsonencode({
    "$schema" = "http://json-schema.org/draft-04/schema#"
    title     = "IntegrationErrorResponse"
    type      = "object"
    required  = ["message", "errorCode"]
    properties = {
      message   = { type = "string" }
      errorCode = { type = "string" }
    }
  })
}

resource "aws_api_gateway_method" "create_shipment" {
  rest_api_id          = aws_api_gateway_rest_api.integration.id
  resource_id          = aws_api_gateway_resource.shipments.id
  http_method          = "POST"
  authorization        = "NONE"
  api_key_required     = true
  request_validator_id = aws_api_gateway_request_validator.parameters.id
}

resource "aws_api_gateway_method" "update_shipment_status" {
  rest_api_id          = aws_api_gateway_rest_api.integration.id
  resource_id          = aws_api_gateway_resource.shipment_status.id
  http_method          = "PUT"
  authorization        = "NONE"
  api_key_required     = true
  request_validator_id = aws_api_gateway_request_validator.parameters.id
  request_parameters = {
    "method.request.path.shipmentId" = true
  }
}

resource "aws_api_gateway_method" "retrieve_shipment" {
  rest_api_id          = aws_api_gateway_rest_api.integration.id
  resource_id          = aws_api_gateway_resource.shipment.id
  http_method          = "GET"
  authorization        = "NONE"
  api_key_required     = true
  request_validator_id = aws_api_gateway_request_validator.parameters.id
  request_parameters = {
    "method.request.path.shipmentId"     = true
    "method.request.header.X-Partner-Id" = true
  }
}

resource "aws_api_gateway_integration" "create_shipment" {
  rest_api_id             = aws_api_gateway_rest_api.integration.id
  resource_id             = aws_api_gateway_resource.shipments.id
  http_method             = aws_api_gateway_method.create_shipment.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.adapter.invoke_arn
}

resource "aws_api_gateway_integration" "update_shipment_status" {
  rest_api_id             = aws_api_gateway_rest_api.integration.id
  resource_id             = aws_api_gateway_resource.shipment_status.id
  http_method             = aws_api_gateway_method.update_shipment_status.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.adapter.invoke_arn
}

resource "aws_api_gateway_integration" "retrieve_shipment" {
  rest_api_id             = aws_api_gateway_rest_api.integration.id
  resource_id             = aws_api_gateway_resource.shipment.id
  http_method             = aws_api_gateway_method.retrieve_shipment.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.adapter.invoke_arn
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${local.common_name_prefix}"
  retention_in_days = 30

  tags = local.common_tags
}

data "aws_partition" "current" {}

data "aws_iam_policy_document" "api_gateway_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_gateway_cloudwatch" {
  name               = "${local.common_name_prefix}-api-cloudwatch-role"
  description        = "Allows API Gateway to publish execution and access logs"
  assume_role_policy = data.aws_iam_policy_document.api_gateway_assume_role.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

resource "aws_api_gateway_account" "integration" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch.arn
}

resource "aws_api_gateway_deployment" "integration" {
  rest_api_id = aws_api_gateway_rest_api.integration.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_integration.create_shipment.id,
      aws_api_gateway_integration.create_shipment.type,
      aws_api_gateway_integration.create_shipment.integration_http_method,
      aws_api_gateway_integration.update_shipment_status.id,
      aws_api_gateway_integration.update_shipment_status.type,
      aws_api_gateway_integration.update_shipment_status.integration_http_method,
      aws_api_gateway_integration.retrieve_shipment.id,
      aws_api_gateway_integration.retrieve_shipment.type,
      aws_api_gateway_integration.retrieve_shipment.integration_http_method,
      aws_api_gateway_method.create_shipment.request_validator_id,
      aws_api_gateway_method.update_shipment_status.request_validator_id,
      aws_api_gateway_method.update_shipment_status.request_parameters,
      aws_api_gateway_method.retrieve_shipment.request_validator_id,
      aws_api_gateway_method.retrieve_shipment.request_parameters,
      aws_api_gateway_model.create_shipment.schema,
      aws_api_gateway_model.update_shipment_status.schema,
      aws_api_gateway_model.error.schema,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.create_shipment,
    aws_api_gateway_integration.update_shipment_status,
    aws_api_gateway_integration.retrieve_shipment,
  ]
}

resource "aws_api_gateway_stage" "integration" {
  deployment_id = aws_api_gateway_deployment.integration.id
  rest_api_id   = aws_api_gateway_rest_api.integration.id
  stage_name    = local.api_stage_name

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      responseLength = "$context.responseLength"
    })
  }

  tags = local.common_tags

  depends_on = [aws_api_gateway_account.integration]
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.integration.id
  stage_name  = aws_api_gateway_stage.integration.stage_name
  method_path = "*/*"

  settings {
    logging_level      = "INFO"
    metrics_enabled    = true
    data_trace_enabled = false
  }
}

resource "aws_api_gateway_api_key" "partner" {
  name        = "${local.common_name_prefix}-sample-partner-key"
  description = "Demonstration API key for the sample integration partner"
  enabled     = true

  tags = local.common_tags
}

resource "aws_api_gateway_usage_plan" "partner" {
  name        = "${local.common_name_prefix}-partner-plan"
  description = "Portfolio quota and throttling for partner API requests"

  api_stages {
    api_id = aws_api_gateway_rest_api.integration.id
    stage  = aws_api_gateway_stage.integration.stage_name
  }

  quota_settings {
    limit  = 10000
    offset = 0
    period = "MONTH"
  }

  throttle_settings {
    burst_limit = 200
    rate_limit  = 100
  }

  tags = local.common_tags
}

resource "aws_api_gateway_usage_plan_key" "partner" {
  key_id        = aws_api_gateway_api_key.partner.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.partner.id
}

resource "aws_api_gateway_base_path_mapping" "api" {
  api_id      = aws_api_gateway_rest_api.integration.id
  stage_name  = aws_api_gateway_stage.integration.stage_name
  domain_name = aws_api_gateway_domain_name.api.domain_name
}

resource "aws_lambda_permission" "api_create_shipment" {
  statement_id  = "AllowApiGatewayCreateShipment"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adapter.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.integration.execution_arn}/${local.api_stage_name}/POST/shipments"
}

resource "aws_lambda_permission" "api_update_shipment_status" {
  statement_id  = "AllowApiGatewayUpdateShipmentStatus"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adapter.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.integration.execution_arn}/${local.api_stage_name}/PUT/shipments/*/status"
}

resource "aws_lambda_permission" "api_retrieve_shipment" {
  statement_id  = "AllowApiGatewayRetrieveShipment"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adapter.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.integration.execution_arn}/${local.api_stage_name}/GET/shipments/*"
}
