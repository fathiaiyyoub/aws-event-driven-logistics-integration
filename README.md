# Modernizing a Legacy Logistics Platform through AWS Integration Services

## Overview

This project demonstrates the modernization of a legacy logistics platform by designing and implementing an event-driven integration architecture on AWS.

The solution decouples legacy systems and external partners through serverless integration services, enabling scalable, resilient, and extensible message processing while supporting multiple integration patterns.

---

## Business Scenario

A logistics company operates a legacy shipment management platform that must integrate with:

- External logistics partners
- Internal on-premises systems
- Existing AWS workloads

The existing point-to-point integrations are difficult to maintain, tightly coupled, and difficult to scale.

This project redesigns the integration layer using AWS managed services and event-driven architecture.

---

## Solution Architecture

Core AWS services include:

- Amazon API Gateway
- AWS Lambda
- Amazon EventBridge
- Amazon SQS
- Amazon DynamoDB
- AWS Secrets Manager
- Amazon S3
- Amazon Data Firehose
- AWS Glue
- Amazon Athena
- Amazon QuickSight
- Amazon CloudWatch

---

## Project Structure

```
Modernizing-Legacy-Logistics-Platform/
│
├── diagrams/
├── docs/
├── lambdas/
├── payloads/
├── simulation/
├── terraform/
├── tests/
├── README.md
├── requirements.txt
└── .gitignore
```

---

## Features

- Event-driven architecture
- Bidirectional Adapter Lambda
- Long-running asynchronous processing
- Configurable outbound delivery framework
- Support for:
  - External partner callbacks
  - Internal on-premises systems
  - AWS workloads
- DynamoDB-based message state tracking
- Endpoint configuration repository
- AWS Secrets Manager integration
- Retry and DLQ support
- Cloud-native observability

---

## Local Testing

Run all tests:

```bash
python -m unittest discover -s tests -v
```

Current status:

- ✅ 31 automated tests passing

---

## Infrastructure

Infrastructure is provisioned using Terraform.

Deployment creates:

- Messaging infrastructure
- Compute resources
- Data services
- IAM
- Monitoring
- Supporting AWS resources

### Partner callback test setup

Outbound delivery uses runtime operational data in the `PartnerConfiguration`
DynamoDB table. Partner-specific records are deliberately not seeded by the
main Terraform deployment. Manual configuration is acceptable for this
portfolio proof of concept; production should use an audited configuration
workflow independent of core infrastructure deployment.

Lambda environment-variable names are consistent across code and Terraform:

- `MESSAGE_STATE_TABLE` identifies the deployed message lifecycle table for
  Adapter, Worker, and Response Lambdas.
- `PARTNER_CONFIG_TABLE` identifies the deployed partner-configuration table
  for the Response Lambda.

Deployed Terraform always supplies the environment-prefixed physical table
names. Local simulations mock state access rather than relying on unsafe
unprefixed table-name defaults.

#### Canonical event naming

Request events use `eventId`, `eventType`, `eventSource`, `timestamp`,
`correlation`, and `payload`. Correlation metadata uses `correlationId`,
`partnerId`, `sourceSystem`, `originalFormat`, and `receivedAt`. Response
events additionally use `requestEventId`, `requestEventType`, `status`, and
`message`. `partnerId` is the sole partner-configuration lookup key.

Worker-owned `processingStatus` values are `RECEIVED`, `PROCESSING`,
`SUCCESS`, `VALIDATION_FAILED`, and `PROCESSING_FAILED`. Response-owned
`deliveryStatus` values are `PENDING`, `RETRYING`, `CONFIGURATION_FAILED`,
`DELIVERED`, and `DELIVERY_FAILED`. These lifecycle fields remain independent.

The current runtime supports only `HTTPS_WEBHOOK` and `PRIVATE_HTTPS`. Delivery
handlers are selected through a central registry so future mechanisms can be
added without changing the Response Lambda orchestration. A future delivery
method is not supported until its code, configuration validation, IAM,
infrastructure, and tests have all been implemented.

#### PartnerConfiguration contract

| Field | Required | Type | Accepted values and default |
|---|---|---|---|
| `partnerId` | Yes | String | Non-empty DynamoDB partition key |
| `enabled` | Yes | Boolean | Missing defaults to disabled |
| `deliveryMethod` | Yes | String | `HTTPS_WEBHOOK` or `PRIVATE_HTTPS` |
| `endpointUrl` | Yes | String | Valid `https://` URL |
| `messageFormat` | No | String | `JSON` (default) or `XML` |
| `secretId` | No | String | Non-empty Secrets Manager identifier |
| `timeoutSeconds` | No | Integer | 1–60 seconds; default 10 |

An unauthenticated callback omits `secretId`:

```json
{
  "partnerId": "partner-001",
  "enabled": true,
  "deliveryMethod": "HTTPS_WEBHOOK",
  "endpointUrl": "https://webhook.site/REPLACE-WITH-UNIQUE-TOKEN",
  "messageFormat": "JSON",
  "timeoutSeconds": 10
}
```

An authenticated callback references a secret but never embeds credentials:

```json
{
  "partnerId": "partner-001",
  "enabled": true,
  "deliveryMethod": "PRIVATE_HTTPS",
  "endpointUrl": "https://partner.example/callback",
  "messageFormat": "XML",
  "secretId": "legacy-logistics-dev/sample-partner/callback-credentials",
  "timeoutSeconds": 10
}
```

The secret `SecretString` must be a JSON object. Both supported credential
properties are optional:

```json
{
  "authorizationHeader": "Bearer example-token",
  "apiKey": "example-api-key"
}
```

Never store real credential values in this repository or Terraform variable
files. The AWS Parameters and Secrets Lambda Extension retrieves credentials at
runtime. The typed AWS CLI example in `examples/partner-001.json` can be copied,
reviewed, and loaded manually after replacing the placeholder with a unique
test webhook URL:

```powershell
aws dynamodb put-item `
  --table-name legacy-logistics-dev-PartnerConfiguration `
  --item file://examples/partner-001.json `
  --region ap-southeast-2
```

---

## Documentation

Detailed architecture documentation is available in the `docs/` folder, including:

- Business requirements
- Architecture Decision Log
- Solution Architecture Document (SAD)
- Implementation guide
- Testing evidence
- Production considerations

---

## Status

Current phase:

✅ Lambda implementation complete

✅ Local testing complete

⬜ Terraform deployment

⬜ AWS deployment

⬜ End-to-end cloud validation

---

## License

This repository is provided for portfolio and educational purposes.
