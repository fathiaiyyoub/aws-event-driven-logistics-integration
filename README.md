# Modernizing a Legacy Logistics Platform through AWS Integration Services

> **An end-to-end AWS Solution Architecture case study demonstrating the design, implementation, testing, and evolution of a serverless event-driven integration platform for a legacy logistics environment.**

---

## Table of Contents

1. Introduction
2. Business Scenario
3. The Problem
4. Solution Objectives
5. Architecture Journey
6. Final Solution Architecture
7. Engineering Challenges
8. Deployment
9. Testing and Validation
10. Lessons Learned
11. Production Considerations
12. Repository Structure
13. Acknowledgements
14. Responsible Use of AI

---

# 1. Introduction

Modernising enterprise integration platforms is rarely about replacing existing business systems. More often, it involves reducing complexity while allowing those systems to continue operating with minimal disruption.

This project demonstrates the design and implementation of a modern event-driven integration platform on Amazon Web Services (AWS) for a legacy logistics environment. Instead of replacing the existing Order Management System (OMS), the solution introduces a cloud-native integration layer that decouples internal applications from external logistics partners through asynchronous messaging, serverless computing, and managed AWS services.

The platform standardises communication between systems using a canonical data model, enabling multiple logistics partners to exchange information regardless of their individual message formats or integration requirements. The solution also provides end-to-end message tracking, secure partner configuration management, operational analytics, and fully automated infrastructure deployment using Terraform.

Unlike many portfolio projects that present only the final solution, this repository documents the complete engineering journey. It captures the architectural decisions, technical challenges, implementation refinements, and lessons learned while designing, deploying, testing, and validating the solution. The objective is not only to demonstrate the final architecture, but also to illustrate the reasoning behind the decisions that shaped it.

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

- version controlled,
- reviewed,
- deployed consistently,
- tested,
- destroyed after validation,
- recreated when required.

# 4. Solution Objectives

The primary objective of this project was to modernise the organisation's integration layer without replacing the existing Order Management System. The solution focuses on introducing cloud-native integration capabilities while preserving existing business applications and minimising operational disruption.

The architecture was designed to achieve the following objectives:

- Decouple internal business systems from external logistics partners through an event-driven architecture.
- Standardise message exchange using a canonical data model regardless of partner-specific formats.
- Support multiple partner integrations while minimising the effort required to onboard additional partners.
- Enable asynchronous processing for long-running business operations without blocking client requests.
- Provide durable end-to-end message tracking across the entire processing lifecycle.
- Securely manage partner credentials and configuration using managed AWS services.
- Improve resilience through managed messaging, retry mechanisms, and dead-letter queues.
- Capture integration events for operational reporting and analytical workloads.
- Deploy the complete AWS environment using Infrastructure as Code (Terraform) to ensure consistency, repeatability, and version control.
- Demonstrate the solution using AWS Well-Architected design principles while remaining appropriate for a portfolio-scale implementation.

These objectives guided every architectural decision throughout the project. Rather than selecting AWS services first, the architecture evolved by addressing specific business and technical challenges encountered during implementation.

# 5. Architecture Journey

One of the objectives of this repository is to document not only the final solution, but also how the architecture evolved throughout the implementation.

The initial design addressed the business requirements at a high level, however several implementation challenges emerged during deployment, testing, and validation. Rather than treating these as isolated issues, each became an opportunity to refine the architecture and adopt a more robust solution.

The final platform is therefore the result of multiple architectural iterations, each improving scalability, maintainability, security, or operational visibility.

The following sections describe the most significant design decisions and the reasoning behind them.

---

## 5.1 Moving from Point-to-Point Integration to Event-Driven Processing

The first architectural decision was to eliminate direct dependencies between the Order Management System and downstream processing components.

Instead of invoking processing logic directly, incoming business requests are published as events. This allows producers and consumers to evolve independently while enabling additional services to subscribe to the same business events without modifying the originating application.

Amazon EventBridge became the central event router responsible for distributing business events throughout the integration platform.

This approach significantly reduced coupling, improved extensibility, and established a foundation for asynchronous processing.

![High-Level Solution Architecture](docs/diagrams/AWS%20Solution%20Architecture%20Diagram%20(high-level).png)

## 5.2 Designing a Canonical Data Model

A key design objective was to isolate internal business processing from partner-specific message formats.

External logistics providers were expected to exchange information using different payload structures and serialization formats, primarily JSON and XML. Allowing these differences to propagate throughout the platform would tightly couple business logic to individual partner implementations and significantly increase the effort required to support new integrations.

To address this, the solution adopts a canonical JSON data model as the internal representation of all business transactions. The inbound Adapter Lambda is responsible for validating incoming requests, detecting the source format, and transforming the payload into the canonical model before publishing it to Amazon EventBridge.

From this point onwards, every downstream component—including the Worker Lambda, operational analytics pipeline, and response processing logic—operates exclusively on the canonical representation. Partner-specific transformations occur only at the integration boundaries, where the outbound Adapter converts the canonical message into the format required by the destination partner.

This approach centralises transformation logic, simplifies downstream processing, reduces duplication, and allows additional partners to be onboarded with minimal impact on the core integration platform.

## 5.3 Supporting Long-Running Business Processes

Creating a shipment is only the beginning of its lifecycle. As a shipment progresses through fulfilment, transport, and delivery, multiple business events may occur long after the original API request has completed.

A synchronous request-response model is therefore unsuitable for representing the complete business process. Once the initial request is accepted, subsequent status updates must be delivered independently of the originating client request.

To support this requirement, the platform separates request processing from response delivery. After completing the required business logic, the Worker Lambda publishes a business event to Amazon EventBridge rather than communicating directly with external partners. EventBridge routes the event to a dedicated response queue, where the Response Lambda retrieves the appropriate partner configuration and delivers the status update using an HTTPS webhook.

This event-driven callback model enables shipment updates to originate from any authorised business process rather than only from the original API request. It also removes direct dependencies between processing and outbound delivery, allowing each stage to scale, retry, and recover independently while maintaining a complete audit trail of the transaction lifecycle.

![End-to-End Request and Callback Flow](docs/diagrams/End-to-End%20Request%20and%20Callback%20Flow.png)

## 5.4 Managing Partner Configuration Securely

Integrating with multiple external partners requires more than message transformation. Each partner may expose different endpoints, authentication methods, certificates, API keys, or webhook URLs that must be managed securely and independently of application code.

To achieve this, the solution separates partner configuration into two distinct categories:

- **Non-sensitive configuration**, such as endpoint URLs and integration settings, is stored in a dedicated DynamoDB PartnerConfiguration table.
- **Sensitive credentials**, including API keys and authentication secrets, are stored in AWS Secrets Manager.

Rather than retrieving secrets directly from AWS Secrets Manager during every invocation, the Response Lambda uses the AWS Parameters and Secrets Lambda Extension. This extension caches secrets within warm Lambda execution environments, significantly reducing latency, API calls, and operational costs while maintaining secure access to partner credentials.

This separation of responsibilities provides a scalable configuration model that simplifies partner onboarding, supports credential rotation, and keeps sensitive information isolated from application logic.

## 5.5 Providing End-to-End Message Visibility

Enterprise integration platforms require more than reliable message processing—they also need comprehensive operational visibility. Every business transaction should be traceable from initial acceptance through processing and final delivery.

To support this requirement, the platform maintains a durable integration message record for every transaction using Amazon DynamoDB. Each message is assigned a unique correlation identifier that enables all processing stages to be linked together regardless of where they occur within the architecture.

During implementation, it became apparent that a single status field was insufficient to accurately represent the lifecycle of a message. A shipment could be processed successfully while the subsequent webhook delivery failed due to a temporary partner outage. Recording both outcomes under a single status introduced ambiguity.

The final design therefore separates the message lifecycle into two independent dimensions:

- **Processing Status**, representing the outcome of business processing performed by the Worker Lambda.
- **Delivery Status**, representing the outcome of outbound webhook delivery performed by the Response Lambda.

This distinction provides a more accurate operational view of the integration platform, simplifies troubleshooting, supports retry logic, and enables independent monitoring of processing and delivery activities.

![DynamoDB Message Lifecycle](docs/diagrams/DynamoDB%20Message%20Lifecycle.png)
![Screenshot #08 – DynamoDB Integration Message Lifecycle State](screenshots/Screenshot%20%2308%20%E2%80%93%20DynamoDB%20Integration%20Message%20Lifecycle%20State.png)

# 6. Final Solution Architecture

The completed solution implements a fully serverless, event-driven integration platform using managed AWS services. Each component has a clearly defined responsibility, allowing the platform to scale independently, reduce operational overhead, and simplify future partner onboarding.

At a high level, incoming requests are accepted through Amazon API Gateway and processed by an Adapter Lambda responsible for request validation, format detection, and transformation into the canonical data model. Business events are then published to Amazon EventBridge, which routes them to downstream consumers without introducing direct dependencies between services.

Amazon SQS provides durable buffering between processing stages, enabling asynchronous execution, retry handling, and failure isolation. The Worker Lambda performs business processing before publishing a completion event back to EventBridge, allowing subsequent response delivery to remain fully decoupled from the original request.

Outbound partner notifications are handled by the Response Lambda, which retrieves the appropriate partner configuration, securely accesses credentials from AWS Secrets Manager using the Parameters and Secrets Lambda Extension cache, and delivers business updates via HTTPS webhooks.

Operational visibility is provided through a combination of DynamoDB, Amazon CloudWatch, Amazon S3, AWS Glue, Amazon Athena, and Amazon QuickSight. Together, these services provide durable message tracking, centralised logging, historical event storage, interactive querying, and business reporting.

The following diagram illustrates the completed solution architecture.

![AWS Solution Architecture](docs/diagrams/AWS%20Solution%20Architecture%20Diagram%20(high-level).png)

# 7. Engineering Challenges

Following the successful deployment of the solution, implementation and end-to-end testing confirmed that the overall architecture met its original design objectives. At the same time, practical experience highlighted several opportunities to refine specific implementation decisions and strengthen the solution.

These refinements did not alter the overall architecture or its event-driven design. Instead, they improved areas such as component responsibilities, operational efficiency, message tracking, security, and performance based on observations made during deployment and validation.

The following sections describe the most significant architectural enhancements introduced after deployment and explain the reasoning behind each refinement.

## 7.1 Restoring the Intended API Gateway Boundary

The original architecture assigned responsibility for request parsing, content-type handling, validation, and canonical transformation to the Inbound Adapter Lambda. During implementation, however, the API Gateway was still configured with non-proxy (`AWS`) Lambda integrations and Velocity Template Language (VTL) mapping templates. These templates parsed incoming requests, reshaped payloads into the canonical structure, and used `passthrough_behavior = "NEVER"` before invoking the Adapter Lambda.

Although the solution functioned correctly, this implementation conflicted with the original architectural intent by placing part of the integration logic in the API layer rather than the Adapter.

To restore the intended separation of responsibilities, the Terraform configuration was updated to replace the custom Lambda integrations with Lambda proxy (`AWS_PROXY`) integrations for the Create Shipment, Update Shipment Status, and Retrieve Shipment endpoints. The VTL mapping templates were removed, and the Adapter Lambda was enhanced to receive and process the complete API Gateway request, including content-type detection, JSON/XML parsing, request validation, and canonical event construction. :contentReference[oaicite:0]{index=0}

This refinement simplified the API Gateway configuration while ensuring that all integration-specific logic remained within a single component. API Gateway now focuses solely on transport concerns such as authentication, throttling, routing, and request forwarding, while the Adapter Lambda owns all protocol and message transformation responsibilities.

## 7.2 Improving Long-Running Response Delivery

The original response mechanism assumed that the information required to deliver a processing result would always be available when the Response Lambda was invoked. During implementation, it became apparent that this assumption was insufficient for long-running business processes.

Shipment status updates may occur hours or even days after the original request has been accepted. By that time, the original HTTP request no longer exists, meaning the platform must independently determine where and how the response should be delivered.

The solution was refined by separating partner configuration from message state. A dedicated **PartnerConfiguration** table was introduced to store non-sensitive partner information, including callback endpoints and references to partner credentials stored in AWS Secrets Manager. The Response Lambda now identifies the originating partner using the stored `partnerId`, retrieves the corresponding configuration from DynamoDB, securely obtains the required credentials through the AWS Parameters and Secrets Lambda Extension, and delivers the response to the appropriate webhook.

This refinement removed any dependency on the original client connection and enabled the platform to support long-running asynchronous business processes while maintaining a consistent delivery mechanism for every partner. It also established a reusable pattern for onboarding additional integration partners without requiring changes to the application logic.
![Screenshot #15 – Internal Event Successfully Published to EventBridge](screenshots/Screenshot%20%2315%20%E2%80%93%20Internal%20Event%20Successfully%20Published%20to%20EventBridge.png)

![Screenshot #16 – External Webhook Callback from Internal Event](screenshots/Screenshot%20%2316%20%E2%80%93%20External%20Webhook%20Callback%20from%20Internal%20Event.png)

## 7.3 Refining Message State Management

The platform was originally designed to maintain the lifecycle of every integration request in a dedicated DynamoDB table. As implementation progressed, additional testing highlighted that a single message status was not sufficient to accurately represent asynchronous processing.

In particular, a shipment could be processed successfully by the Worker Lambda while the subsequent webhook delivery failed or required multiple retry attempts. Recording both outcomes under a single status made it difficult to determine whether a transaction had failed during business processing or during response delivery.

The data model was therefore refined by separating message state into two independent attributes: **processingStatus** and **deliveryStatus**. The Worker Lambda became responsible for updating the processing status, while the Response Lambda independently managed delivery status together with delivery attempts and related metadata.

This refinement provided a more accurate representation of each transaction throughout its lifecycle, enabling operational teams to distinguish processing outcomes from delivery outcomes and simplifying monitoring, troubleshooting, and retry management without changing the overall architecture.

**Before**

```json
{
  "correlationId": "abc123",
  "status": "SUCCESS"
}
```

**After**

```json
{
  "correlationId": "abc123",
  "processingStatus": "COMPLETED",
  "deliveryStatus": "FAILED",
  "deliveryAttempts": 3
}
```

## 7.4 Optimising Partner Credential Retrieval

Supporting webhook-based response delivery required the platform to securely manage partner credentials without embedding sensitive information in the application code or configuration.

AWS Secrets Manager was selected to store sensitive partner credentials, while the **PartnerConfiguration** table maintained references to the appropriate secret for each integration partner. During implementation, consideration was given to the long-term operational behaviour of the solution, particularly the impact of repeatedly retrieving the same secret for every outbound response.

To reduce latency, lower the number of Secrets Manager API calls, and minimise operational costs, the solution was refined to use the **AWS Parameters and Secrets Lambda Extension**. The extension caches retrieved secrets within the Lambda execution environment, allowing subsequent invocations to reuse cached credentials while automatically refreshing them after the configured cache period.

The Response Lambda was updated to retrieve partner credentials through the local extension endpoint rather than calling the Secrets Manager service directly. This change was transparent to the business logic while improving performance and reducing the number of external API requests during periods of sustained message processing.

```python
secret = get_secret(secret_name)
```

By introducing local secret caching, the solution retained the security benefits of AWS Secrets Manager while improving the efficiency of outbound response processing.

## 7.5 Validating Platform Behaviour Under Load

After functional testing was completed, a controlled end-to-end load test was performed using 150 requests with a concurrency level of 10.

The first test produced numerous HTTP `429 Too Many Requests` responses. Investigation confirmed that API Gateway was rejecting requests before they entered the event-driven processing pipeline because the Usage Plan was configured with a burst limit of 20 requests and a steady-state rate limit of 10 requests per second.

![Screenshot #12 – Controlled End-to-End Load Test Execution and API Gateway Throttling Results](screenshots/Screenshot%20%2312%20%E2%80%93%20Controlled%20End-to-End%20Load%20Test%20Execution%20and%20API%20Gateway%20Throttling%20Results.png)

The throttling configuration in Terraform was then adjusted by increasing the burst limit from 20 to 200 and the rate limit from 10 to 100 requests per second.

```hcl
throttle_settings {
  burst_limit = 200
  rate_limit  = 100
}
```

The same controlled test was repeated after applying the updated configuration. All 150 requests were accepted with HTTP `202 Accepted` responses, completing in approximately 3.86 seconds with an average response time of approximately 241 milliseconds.

![Screenshot #13 – Controlled Load Test Results (150 Requests, Concurrency 10)](screenshots/Screenshot%20%2313%20%E2%80%93%20Controlled%20Load%20Test%20Results%20%28150%20Requests%2C%20Concurrency%2010%29.png)

This test demonstrated that API Gateway throttling must be configured in line with the expected traffic profile. It also confirmed that the asynchronous processing architecture could accept the planned request volume without introducing additional components or changing the wider solution design.

# 8. Solution Validation

The completed solution was validated through a series of functional, integration, and performance tests designed to verify both the implementation and the architectural objectives of the project.

Rather than testing individual AWS services in isolation, the validation process followed complete business transactions as they progressed through the event-driven workflow—from the initial API request to asynchronous processing, response delivery, and operational reporting.

The following sections summarise the key validation activities and demonstrate that the implemented solution performs as expected under normal operating conditions.

## 8.1 Functional Validation

Functional testing confirmed that each API endpoint performed its intended business function and that requests were successfully processed throughout the event-driven workflow.

The tests verified request acceptance, payload validation, asynchronous processing, data persistence, and response generation for the primary business operations supported by the platform.

### Create Shipment

A shipment creation request was submitted through Amazon API Gateway and successfully accepted for asynchronous processing.

![Screenshot #01 – Create Shipment Request Accepted](screenshots/Screenshot%20%2301%20%E2%80%93%20Create%20Shipment%20Request%20Accepted.png)

The request was transformed into the canonical event model and published to Amazon EventBridge, enabling asynchronous processing by downstream services while decoupling the API layer from backend processing.

![Screenshot #15 – Internal Event Successfully Published to EventBridge](screenshots/Screenshot%20%2315%20%E2%80%93%20Internal%20Event%20Successfully%20Published%20to%20EventBridge.png)

The Worker Lambda processed the event successfully and recorded the transaction state in the `IntegrationMessageState` DynamoDB table, providing durable lifecycle tracking and operational visibility.

![Screenshot #03 – Successful Message State in DynamoDB](screenshots/Screenshot%20%2303%20%E2%80%93%20Successful%20Message%20State%20in%20DynamoDB.png)

### Retrieve Shipment

The Retrieve Shipment endpoint successfully returned the requested shipment details using the stored shipment identifier.

> **No matching screenshot currently exists in the repository.**

### Update Shipment Status

Shipment status updates were accepted through the API and processed successfully, demonstrating support for long-running business operations beyond the initial shipment creation.

> **No matching screenshot currently exists in the repository.**

The updated shipment status was successfully processed by the Worker Lambda.

> **No matching screenshot currently exists in the repository.**

The `IntegrationMessageState` table recorded the updated processing information, confirming successful tracking of the transaction lifecycle.

![Screenshot #08 – DynamoDB Integration Message Lifecycle State](screenshots/Screenshot%20%2308%20%E2%80%93%20DynamoDB%20Integration%20Message%20Lifecycle%20State.png)

## 8.2 End-to-End Event Processing

Beyond validating individual API operations, end-to-end testing verified that business events were successfully propagated through the complete event-driven architecture.

After the Worker Lambda completed business processing, a shipment status event was published to Amazon EventBridge. The event was then routed to the outbound processing pipeline, where the Response Lambda retrieved the appropriate partner configuration and delivered the business response to the originating partner using an HTTPS webhook.

This validation confirmed that the platform correctly supports asynchronous business processes, allowing responses to be delivered independently of the original client request while maintaining message correlation throughout the transaction lifecycle.

![Screenshot #15 – Internal Event Successfully Published to EventBridge](screenshots/Screenshot%20%2315%20%E2%80%93%20Internal%20Event%20Successfully%20Published%20to%20EventBridge.png)

---

The corresponding webhook callback was successfully received by the external endpoint, confirming completion of the end-to-end processing workflow.

![Screenshot #16 – External Webhook Callback from Internal Event](screenshots/Screenshot%20%2316%20%E2%80%93%20External%20Webhook%20Callback%20from%20Internal%20Event.png)

## 8.3 Analytics Validation

In addition to processing business transactions, the platform was validated to ensure that operational events were successfully captured for reporting and analysis.

Processed integration events were streamed to Amazon S3 using Amazon Data Firehose, catalogued by AWS Glue, and queried through Amazon Athena. This pipeline provides a historical record of integration activity that can support operational reporting, troubleshooting, auditing, and business analytics.

The following screenshots demonstrate the successful ingestion, cataloguing, and querying of integration data.

The processed integration events were successfully delivered to the Amazon S3 data lake.

![Screenshot #09 – Integration Events Stored in Amazon S3](screenshots/Screenshot%20%2309%20%E2%80%93%20Integration%20Events%20Stored%20in%20Amazon%20S3.png)

---

AWS Glue successfully catalogued the dataset, making it available for analytical queries.

![Screenshot #10 – AWS Glue Data Catalog](screenshots/Screenshot%20%2310%20%E2%80%93%20AWS%20Glue%20Data%20Catalog.png)

---

Amazon Athena successfully queried the stored integration events, confirming that the analytics pipeline was operating correctly from data ingestion through to query execution.

![Screenshot #11 – Amazon Athena Query Results](screenshots/Screenshot%20%2311%20%E2%80%93%20Amazon%20Athena%20Query%20Results.png)

## 8.4 Performance Validation

Following the refinement of the API Gateway throttling configuration described in Section 7.5, the platform was subjected to a final controlled load test to confirm its behaviour under concurrent requests.

The validation consisted of 150 requests with a concurrency level of 10. All requests were accepted with HTTP `202 Accepted` responses and entered the asynchronous processing pipeline successfully. The test completed in approximately 3.86 seconds with an average response time of approximately 241 milliseconds.

These results confirmed that the deployed configuration was capable of supporting the planned workload while preserving the responsiveness of the API and the scalability benefits of the event-driven architecture.

![Screenshot #13 – Controlled Load Test Results (150 Requests, Concurrency 10)](screenshots/Screenshot%20%2313%20%E2%80%93%20Controlled%20Load%20Test%20Results%20%28150%20Requests%2C%20Concurrency%2010%29.png)

# 9. Lessons Learned

This project provided valuable practical experience in designing, implementing, and validating an enterprise integration platform using AWS managed services. While the original architecture met its intended objectives, the implementation process reinforced several important architectural principles that will influence future solution designs.

## 9.1 Clearly Define Component Responsibilities

One of the most important lessons was the value of maintaining clear boundaries between architectural components. Although the initial implementation was functional, reviewing the deployed solution revealed that API Gateway was performing part of the request transformation through VTL mapping templates. Moving this responsibility entirely into the Adapter Lambda restored the intended separation of concerns and produced a cleaner, more maintainable solution.

## 9.2 Design for Long-Running Business Processes

Enterprise integrations rarely end when an API request returns a response. Supporting asynchronous business processes required the platform to maintain sufficient information to deliver business outcomes long after the original request had completed. Separating partner configuration from message state and using webhook callbacks provided a flexible approach that can accommodate additional partners and extended business workflows.

## 9.3 Operational Visibility Is Part of the Architecture

Tracking the lifecycle of integration messages proved to be just as important as processing them. Refining the message model to distinguish processing outcomes from delivery outcomes provided greater operational clarity and simplified monitoring, troubleshooting, and retry management.

## 9.4 Infrastructure Configuration Requires Validation

Load testing demonstrated that infrastructure configuration can significantly influence application behaviour. The initial HTTP 429 responses were caused by API Gateway throttling rather than limitations in the event-driven architecture itself. Validating the deployed infrastructure under realistic workloads was therefore as important as validating the application logic.

## 9.5 Security and Performance Must Be Considered Together

Protecting sensitive partner credentials was essential, but security should not unnecessarily reduce operational efficiency. Combining AWS Secrets Manager with the AWS Parameters and Secrets Lambda Extension allowed the platform to maintain strong security while reducing repeated secret retrievals, improving response times, and lowering operational overhead.

These lessons reinforced that successful solution architecture extends beyond selecting AWS services. Careful allocation of responsibilities, continuous validation, and iterative refinement are equally important in delivering solutions that remain scalable, maintainable, and operationally effective.

# 10. Production Considerations

The solution presented in this repository demonstrates a production-oriented architecture implemented within the scope of a portfolio project. While the core design principles are suitable for enterprise integration workloads, a production deployment would typically introduce additional operational, security, and governance capabilities based on organisational requirements.

The following enhancements would be considered for a production implementation.

## High Availability and Disaster Recovery

- Deploy the solution across multiple AWS Regions to provide business continuity for regional outages.
- Replicate DynamoDB tables using Global Tables where cross-region resilience is required.
- Implement regional failover for API endpoints using Amazon Route 53 health checks and routing policies.

## Security

- Enable AWS WAF to protect public API endpoints against common web exploits.
- Apply AWS Shield Advanced where additional DDoS protection is required.
- Introduce fine-grained IAM policies and regular credential rotation.
- Encrypt all data using customer-managed AWS KMS keys where organisational policies require additional control.

## Observability

- Expand CloudWatch dashboards and alarms for business and operational metrics.
- Configure Amazon EventBridge rules for operational notifications.
- Integrate with incident management platforms such as AWS Systems Manager Incident Manager, PagerDuty, or ServiceNow where appropriate.

## Operational Excellence

- Implement CI/CD pipelines to automate infrastructure deployment and application releases.
- Introduce automated integration and regression testing as part of the deployment pipeline.
- Apply Infrastructure as Code validation, security scanning, and policy compliance checks before deployment.

## Analytics

- Extend the analytics platform by connecting Amazon QuickSight to Athena datasets to provide operational dashboards for business users and support teams.
- Introduce long-term trend analysis, KPI reporting, and executive dashboards using the historical integration data stored in Amazon S3.

Although these capabilities were outside the scope of this project, the implemented architecture provides a solid foundation on which they can be incorporated without requiring significant structural changes.

# 10. Production Considerations

The solution presented in this repository demonstrates an enterprise-oriented integration platform implemented within the scope of a portfolio project. While the architecture successfully satisfies the defined business and technical requirements, a production deployment would typically incorporate additional capabilities to meet organisational standards for availability, security, operations, and governance.

The following enhancements would be recommended for a production implementation.

## High Availability and Disaster Recovery

- Deploy the solution across multiple AWS Regions to improve resilience against regional failures.
- Replicate DynamoDB tables using Amazon DynamoDB Global Tables where business continuity requirements justify cross-region data replication.
- Configure Amazon Route 53 health checks and failover routing to automatically redirect traffic during regional outages.

## Security

- Protect public API endpoints using AWS WAF to mitigate common web attacks.
- Enable AWS Shield Advanced where enhanced DDoS protection is required.
- Apply least-privilege IAM policies and implement regular credential rotation.
- Use customer-managed AWS KMS keys where organisational security policies require additional control over encryption.

## Observability

- Expand Amazon CloudWatch dashboards and alarms to monitor application health and business metrics.
- Configure automated operational notifications using Amazon EventBridge.
- Integrate with enterprise incident management platforms such as AWS Systems Manager Incident Manager, ServiceNow, or PagerDuty where required.

## DevOps and Governance

- Implement CI/CD pipelines to automate infrastructure deployment and application releases.
- Introduce automated testing, infrastructure validation, and security scanning as part of the deployment pipeline.
- Apply governance controls to ensure Infrastructure as Code complies with organisational standards before deployment.

## Analytics

- Extend the analytics capability by integrating Amazon QuickSight with Amazon Athena to provide operational dashboards and business reporting.
- Develop dashboards for integration throughput, processing performance, delivery success rates, and long-term operational trends.

Although these capabilities were outside the scope of this project, the implemented architecture provides a solid foundation on which they can be introduced without significant architectural changes.

# 11. Deployment

The solution was deployed entirely using **Terraform**, providing a repeatable and consistent deployment process for all AWS resources. Infrastructure as Code (IaC) ensured that networking, security, compute, integration services, analytics, monitoring, and supporting resources were provisioned from a single source of truth.

Terraform also simplified iterative development throughout the project. As architectural refinements were introduced, infrastructure changes could be applied consistently without manual reconfiguration, reducing deployment errors and maintaining alignment between the implementation and the intended architecture.

## Infrastructure as Code

The infrastructure was organised into logical Terraform configuration files, each responsible for a specific area of the solution.

| Terraform Configuration | Purpose |
|--------------------------|---------|
| `network.tf` | VPC, subnets, routing, NAT Gateway and VPC networking |
| `security.tf` | Security Groups and networking controls |
| `iam.tf` | IAM roles and permissions for AWS services |
| `lambda.tf` | Deployment of Lambda functions and execution roles |
| `apigateway.tf` | REST API, resources, methods, integrations and API keys |
| `eventbridge.tf` | EventBridge event bus, rules and targets |
| `sqs.tf` | Processing queues and dead-letter queues |
| `dynamodb.tf` | Partner configuration and message state tables |
| `firehose.tf` | Event delivery into Amazon S3 |
| `glue.tf` | Glue database, crawler and Data Catalog |
| `athena.tf` | Athena workgroup and analytics configuration |
| `cloudwatch.tf` | Log groups and monitoring resources |
| `cloudtrail.tf` | API auditing and account activity logging |
| `outputs.tf` | Deployment outputs including API endpoints and resource identifiers |

## Deployment Workflow

The infrastructure followed a standard Terraform deployment lifecycle.

1. Initialise the working directory and required providers.
2. Validate the Terraform configuration.
3. Review the execution plan.
4. Deploy the infrastructure to AWS.
5. Validate the deployed resources through functional and end-to-end testing.
6. Destroy the environment when testing was complete to minimise ongoing AWS costs.

```bash
terraform init
terraform validate
terraform plan
terraform apply
```

After successful testing, the entire environment could be removed using:

```bash
terraform destroy
```

## Deployment Validation

Following deployment, each component was verified before end-to-end testing commenced. Validation included confirming successful resource creation, API Gateway availability, Lambda execution, EventBridge routing, SQS message flow, DynamoDB persistence, outbound webhook delivery, and the analytics pipeline from Amazon S3 through AWS Glue to Amazon Athena.

This deployment approach ensured that the complete platform could be recreated consistently while supporting iterative improvements throughout the implementation lifecycle.

# 12. Conclusion

This project demonstrates the design, implementation, and validation of a modern event-driven integration platform that transforms a tightly coupled legacy environment into a scalable, serverless architecture using AWS managed services.

The solution applies cloud-native design principles to support heterogeneous partner integrations, asynchronous business processes, secure partner communication, operational analytics, and Infrastructure as Code. Throughout the implementation, architectural decisions were continuously validated through deployment, testing, and targeted refinements to ensure that the final solution aligned with its original design objectives.

Beyond delivering a working implementation, this project provided valuable experience in translating business requirements into technical architecture, balancing functional and non-functional requirements, and applying iterative improvements based on practical implementation outcomes.

The repository contains the complete Terraform configuration, Lambda source code, architecture diagrams, validation artefacts, and supporting documentation, providing a comprehensive reference for the design and implementation of the solution.

# Responsible Use of AI

This project was developed using a combination of hands-on engineering and responsible use of generative AI as a technical assistant.

AI tools were used to explore architectural alternatives, review implementation approaches, refine Infrastructure as Code, improve technical documentation, and challenge design decisions throughout the project. All architectural decisions, implementation changes, infrastructure deployment, testing, troubleshooting, validation, and final documentation were personally reviewed, verified, and completed by the author.

The project reflects my practical understanding of AWS cloud architecture, serverless integration, Infrastructure as Code, and event-driven system design. AI accelerated research and documentation activities, while responsibility for the final solution, technical accuracy, and engineering outcomes remained entirely my own.
