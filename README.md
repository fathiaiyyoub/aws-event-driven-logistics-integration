# Modernizing a Legacy Logistics Platform through AWS Integration Services

> **Enterprise AWS Solution Architecture Portfolio Project**

| Item | Details |
|------|---------|
| **Architecture Style** | Event-Driven Serverless Integration Platform |
| **Cloud Platform** | Amazon Web Services (AWS) |
| **Infrastructure as Code** | Terraform |
| **Primary Language** | Python |
| **Project Status** | Completed |
| **Author** | Fathi Aiyyoub |

---

## Overview

This project demonstrates the modernization of a legacy logistics and shipment-tracking platform by designing and implementing a scalable, event-driven integration architecture on Amazon Web Services (AWS).

The solution addresses the challenges of integrating legacy business systems with multiple external logistics partners that use different communication protocols and data formats. Rather than relying on tightly coupled point-to-point integrations, the platform adopts an event-driven architecture that improves scalability, resilience, maintainability, and operational visibility.

The implementation leverages Amazon EventBridge, Amazon SQS, AWS Lambda, Amazon API Gateway, Amazon DynamoDB, AWS Secrets Manager, Amazon Kinesis Data Firehose, Amazon S3, AWS Glue, Amazon Athena, Amazon QuickSight, and Terraform to deliver a fully automated cloud-native integration platform.

This repository contains the complete Infrastructure as Code (IaC), Lambda source code, testing artefacts, architecture diagrams, and supporting resources used to design, implement, deploy, test, and validate the solution.

> **Note:** This README provides a high-level overview of the project. The complete design rationale, architectural decisions, implementation details, testing evidence, and production recommendations are documented in the accompanying **Solution Architecture Document (SAD)**.

## Business Scenario

ABC Warehousing and Logistics relies on a legacy Order Management System (OMS) to coordinate shipments with multiple external logistics partners. As the business expanded, the existing integration approach became increasingly difficult to maintain due to tightly coupled interfaces, inconsistent message formats, and limited visibility into message processing.

The organisation required a modern integration platform capable of supporting multiple partner communication methods while improving scalability, reliability, and operational monitoring. The solution also needed to provide end-to-end message tracking, secure partner configuration management, asynchronous processing, and a foundation for future partner onboarding with minimal architectural change.

To address these requirements, this project modernises the integration layer by implementing an event-driven, serverless architecture on AWS. The platform decouples business systems from integration logic, enabling reliable message processing, standardised data exchange, and enhanced operational analytics while remaining extensible for future business growth.

## Solution Overview

The proposed solution replaces tightly coupled integrations with an event-driven architecture built on AWS managed services. Incoming requests from internal business systems and external logistics partners are standardised by an inbound adapter before being published to Amazon EventBridge. Events are then routed asynchronously through Amazon SQS to specialised AWS Lambda functions responsible for business processing and outbound partner communication.

Partner-specific configuration is stored in Amazon DynamoDB, while sensitive credentials are securely managed using AWS Secrets Manager with the AWS Parameters and Secrets Lambda Extension to reduce latency and API calls. Every integration message is tracked throughout its lifecycle, enabling end-to-end observability, retry management, and delivery status reporting.

Operational analytics are provided through Amazon Kinesis Data Firehose, Amazon S3, AWS Glue, Amazon Athena, and Amazon QuickSight, allowing business users to analyse historical integration events without impacting the operational workload.

The entire solution is provisioned using Terraform, providing a repeatable and version-controlled Infrastructure as Code (IaC) deployment.

### High-Level Solution Architecture
![High-Level AWS Architecture](docs/diagrams/AWS%20Solution%20Architecture%20Diagram%20(high-level).png)

## Key Features

- **Event-Driven Architecture** – Decouples systems using Amazon EventBridge and Amazon SQS for scalable, asynchronous message processing.

- **Serverless Compute** – AWS Lambda processes inbound requests, business logic, and outbound partner responses without server management.

- **Multi-Partner Integration** – Supports multiple logistics partners through a common canonical message model while allowing partner-specific processing.

- **End-to-End Message Tracking** – Tracks each integration message throughout its lifecycle using Amazon DynamoDB, enabling correlation, retry management, and delivery status reporting.

- **Secure Partner Configuration** – Stores sensitive partner credentials in AWS Secrets Manager with the AWS Parameters and Secrets Lambda Extension for improved performance.

- **Analytics and Reporting** – Streams integration events to Amazon S3 via Amazon Kinesis Data Firehose for analysis using AWS Glue, Amazon Athena, and Amazon QuickSight.

- **Infrastructure as Code** – Entire AWS environment is provisioned and managed using Terraform, ensuring consistent and repeatable deployments.

- **Resilient Message Processing** – Uses Amazon SQS dead-letter queues (DLQs) and retry mechanisms to improve reliability and support operational recovery.

## Technology Stack

| Category | Technologies |
|----------|--------------|
| **Cloud Platform** | Amazon Web Services (AWS) |
| **Compute** | AWS Lambda |
| **API & Integration** | Amazon API Gateway, Amazon EventBridge |
| **Messaging** | Amazon SQS, Amazon SQS Dead-Letter Queues |
| **Data Storage** | Amazon DynamoDB |
| **Secrets Management** | AWS Secrets Manager, AWS Parameters and Secrets Lambda Extension |
| **Analytics** | Amazon Kinesis Data Firehose, Amazon S3, AWS Glue, Amazon Athena, Amazon QuickSight |
| **Networking** | Amazon VPC, NAT Gateway, Route 53 |
| **Monitoring** | Amazon CloudWatch, AWS CloudTrail |
| **Infrastructure as Code** | Terraform |
| **Programming Language** | Python 3.13 |
| **Version Control** | Git, GitHub |

## Repository Structure

```text
.
├── docs/
│   ├── diagrams/          # Architecture diagrams
│   └── testing/           # Load testing results and evidence
├── examples/              # Sample partner payloads
├── lambdas/               # AWS Lambda source code
│   ├── adapter/
│   ├── common/
│   ├── response_processor/
│   └── worker/
├── payloads/              # API request payloads
├── screenshots/           # Project screenshots
├── simulation/            # Testing and simulation resources
├── terraform/             # Terraform Infrastructure as Code
├── tests/                 # Test scripts
├── controlled_load_test.py
├── requirements.txt
└── README.md
```

### Repository Contents

| Folder / File | Description |
|---------------|-------------|
| **docs/** | Project documentation, architecture diagrams, and testing artefacts. |
| **examples/** | Example partner request payloads. |
| **lambdas/** | Source code for all AWS Lambda functions used by the solution. |
| **payloads/** | Sample API payloads used during testing. |
| **screenshots/** | Deployment and validation screenshots. |
| **simulation/** | Resources used to simulate partner integrations. |
| **terraform/** | Complete Infrastructure as Code (IaC) for deploying the AWS environment. |
| **tests/** | Supporting test resources and scripts. |
| **controlled_load_test.py** | Script used for controlled performance testing. |
| **requirements.txt** | Python dependencies required for local execution. |

## Deployment

The infrastructure for this project is fully defined using **Terraform**, enabling consistent and repeatable deployments into an AWS account.

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform 1.6 or later
- Python 3.13
- An AWS account with permissions to provision the required services

### Deploy the Infrastructure

```bash
git clone https://github.com/fathiaiyyoub/aws-event-driven-logistics-integration.git

cd aws-event-driven-logistics-integration/terraform

terraform init

terraform plan

terraform apply
```

### Clean Up

To remove all deployed AWS resources and avoid ongoing charges:

```bash
terraform destroy
```

> **Note:** This repository is intended as a portfolio project. Certain configuration values (for example, AWS account IDs, domain names, API keys, and secrets) should be replaced with your own before deployment. Refer to `terraform.tfvars.example` when configuring your environment.

## Testing and Validation

The solution was validated through functional, integration, and performance testing to ensure that the event-driven architecture operated reliably under normal and burst workloads.

### Functional Testing

The following capabilities were successfully validated:

- API Gateway accepted inbound shipment requests.
- EventBridge routed events to the appropriate processing queues.
- AWS Lambda functions processed shipment events asynchronously.
- Amazon DynamoDB tracked message lifecycle and delivery status.
- Response processing successfully delivered outbound webhook notifications.
- Dead-letter queue (DLQ) handling and retry behaviour were verified.
- Analytics data was successfully delivered to Amazon S3 for querying with Amazon Athena.

### Performance Testing

A controlled load test was executed to evaluate the scalability of the serverless architecture.

| Metric | Result |
|---------|-------:|
| Total Requests | 150 |
| Concurrent Users | 10 |
| Successful Requests | 150 (100%) |
| Total Test Duration | 3.86 seconds |
| Average Throughput | 38.83 requests/sec |
| Average Response Time | 241.49 ms |
| Maximum Response Time | 1758.97 ms |

Detailed test artefacts and load-test reports are available in the `docs/testing/` directory.

### Validation Outcome

The completed testing demonstrated that the architecture successfully supports asynchronous event processing, resilient message delivery, end-to-end message tracking, and analytics integration while maintaining a fully serverless and Infrastructure-as-Code deployment model.

## Project Outcomes

This project demonstrates the design, implementation, and validation of a modern event-driven integration platform using AWS managed services and Infrastructure as Code.

Key outcomes include:

- Modernised a legacy logistics integration platform using a scalable event-driven architecture.
- Eliminated tightly coupled point-to-point integrations through asynchronous event processing.
- Implemented a secure, serverless solution using AWS managed services.
- Delivered complete Infrastructure as Code (IaC) using Terraform for repeatable deployments.
- Established end-to-end message tracking, retry handling, and delivery status monitoring.
- Integrated an analytics pipeline for operational reporting and historical event analysis.
- Successfully validated the solution through functional, integration, and controlled load testing.

The project demonstrates practical experience across solution architecture, cloud integration, Infrastructure as Code, serverless application development, security, observability, and system validation while following AWS architectural best practices.

## Acknowledgements

This project was developed as part of my AWS cloud architecture portfolio to demonstrate practical solution design, Infrastructure as Code (IaC), serverless integration patterns, and event-driven architectures using Amazon Web Services.

## Responsible Use of AI

Artificial Intelligence (AI) tools were used during the development of this project to assist with brainstorming, architecture discussions, code review, troubleshooting, documentation, and technical writing.

All architectural decisions, implementation choices, infrastructure deployments, testing, and validation were critically reviewed and verified before being incorporated into the solution. AI was used as a collaborative engineering assistant to accelerate learning and improve productivity, while responsibility for the final design and implementation remained with the author.

This approach reflects modern software engineering practices, where AI complements—not replaces—technical understanding, critical thinking, and professional judgement.
