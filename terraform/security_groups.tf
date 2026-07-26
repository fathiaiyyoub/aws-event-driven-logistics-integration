// Shared by the Adapter and Response Lambda functions when VPC integration is added.
// No ingress rules are defined because these functions initiate connections only.
resource "aws_security_group" "lambda_integration" {
  name        = "${local.common_name_prefix}-lambda-integration-sg"
  description = "Allows integration Lambda functions to call HTTPS endpoints"
  vpc_id      = aws_vpc.integration.id

  egress {
    description = "HTTPS to external partner webhook endpoints"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-lambda-integration-sg"
  })
}
