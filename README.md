# Modernizing a Legacy Logistics Platform through AWS Integration Services

> **Enterprise AWS Solution Architecture Portfolio Project**

| Item | Details |
|------|---------|
| **Architecture Style** | Event-Driven Serverless Integration Platform |
| **Cloud Platform** | Amazon Web Services (AWS) |
| **Infrastructure as Code** | Terraform |
| **Primary Language** | Python |
| **Project Status** | Completed |
| **Author** | Fathi Ayyoub |

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
