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
python simulation/run_end_to_end.py
```

# 2. Business Scenario

ABC Warehousing and Logistics is a fictitious organisation created for this portfolio project to represent a typical enterprise operating within the logistics and supply chain industry. The organisation relies on a legacy Order Management System (OMS) to coordinate shipments with multiple external logistics providers and several internally developed business applications.

Over time, the integration landscape evolved organically as new partners and systems were introduced. Individual integrations were developed independently, resulting in tightly coupled interfaces, inconsistent message formats, duplicated integration logic, and limited visibility into message processing. Each new logistics partner required additional custom development, increasing implementation effort, operational complexity, and long-term maintenance costs.

As business volumes continued to grow, the limitations of the existing integration model became increasingly apparent. The organisation required a modern integration platform capable of supporting multiple logistics partners while providing a standardised approach to message processing, asynchronous communication, secure partner management, operational monitoring, and future scalability.

Rather than replacing the existing Order Management System, the objective was to modernise the integration layer surrounding it. This approach minimises business disruption while enabling the organisation to progressively adopt modern cloud-native integration patterns without requiring significant changes to existing business applications.

The following diagram illustrates the existing integration landscape prior to modernisation.

![AS-IS Architecture](docs/diagrams/AS-IS%20Architecture.png)

# 3. The Problem

The existing integration model created several technical and operational limitations.

## 3.1 Point-to-Point Coupling

The legacy OMS communicated directly with individual logistics partners. Each integration depended on partner-specific endpoints, message formats, authentication methods, and processing logic.

As the number of partners increased, the OMS became responsible for managing an expanding collection of custom interfaces. Changes to one partner integration could require modifications to the central business system, increasing regression risk and slowing future onboarding.

## 3.2 Inconsistent Message Formats

External partners did not use a common data format. Some exchanged JSON payloads, while others used XML or different field structures for equivalent business transactions.

Without a canonical message model, transformation logic was duplicated across integrations. This made validation inconsistent and increased the effort required to support new partners.

## 3.3 Synchronous Processing Dependencies

Direct integration encouraged synchronous communication between systems. The initiating system could become dependent on downstream processing time, partner availability, or network connectivity.

This created several risks:

- Temporary partner outages could affect internal processing.
- Long-running shipment operations could not be represented reliably through a single synchronous request.
- Retry behaviour was difficult to coordinate.
- Failures could propagate across system boundaries.

## 3.4 Limited End-to-End Visibility

The existing model did not provide a consistent mechanism for tracking a message across its complete journey.

It was difficult to answer operational questions such as:

- Was the request accepted?
- Was it transformed successfully?
- Was the business operation processed?
- Was the response delivered to the partner?
- How many delivery attempts were made?
- Did the message enter a dead-letter queue?

The absence of durable correlation and lifecycle tracking made troubleshooting slower and increased reliance on individual application logs.

## 3.5 Partner Configuration and Credential Management

Partner-specific endpoint details and authentication credentials required a secure and maintainable storage model.

Storing configuration directly in application code or environment variables would create deployment coupling, while storing the same callback information against every message would introduce duplication and unnecessary data growth.

The platform therefore needed to separate:

- non-sensitive partner configuration,
- sensitive credentials,
- per-message processing state.

## 3.6 Limited Operational Analytics

The existing environment did not provide a central analytics capability for integration events.

The organisation required a way to retain message activity for operational analysis, including:

- request volumes,
- processing outcomes,
- partner activity,
- response delivery status,
- failure trends,
- performance observations.

## 3.7 Infrastructure Consistency

A manually configured integration environment would be difficult to reproduce, review, and maintain.

The solution required Infrastructure as Code so that the AWS environment could be:

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
  "correlationId": "abc123",
  "status": "SUCCESS"
}
```

**After**

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
