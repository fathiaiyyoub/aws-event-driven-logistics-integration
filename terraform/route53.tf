resource "aws_acm_certificate" "api" {
  domain_name       = var.api_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-api-certificate"
  })
}

resource "aws_route53_record" "api_certificate_validation" {
  for_each = {
    for option in aws_acm_certificate.api.domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }
  }

  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for record in aws_route53_record.api_certificate_validation : record.fqdn]
}

resource "aws_api_gateway_domain_name" "api" {
  domain_name              = var.api_domain_name
  regional_certificate_arn = aws_acm_certificate_validation.api.certificate_arn

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  security_policy = "TLS_1_2"

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-api-domain"
  })
}

resource "aws_route53_record" "api_alias" {
  zone_id = var.route53_zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = aws_api_gateway_domain_name.api.regional_domain_name
    zone_id                = aws_api_gateway_domain_name.api.regional_zone_id
    evaluate_target_health = false
  }
}

// The API base-path mapping will be added after a deployable Adapter Lambda
// permits creation of the complete REST API deployment and stage.
