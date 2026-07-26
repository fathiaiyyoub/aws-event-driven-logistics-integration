// This secret stores only sensitive callback credentials for a demonstration
// partner. Its value is populated manually or through a secure deployment process;
// webhook URLs and other non-sensitive configuration remain in DynamoDB.
resource "aws_secretsmanager_secret" "sample_partner_callback_credentials" {
  name        = "${local.common_name_prefix}/sample-partner/callback-credentials"
  description = "Sensitive callback credentials for the sample integration partner; non-secret configuration is stored in DynamoDB."

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-sample-partner-callback-credentials"
  })
}
