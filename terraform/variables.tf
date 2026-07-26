// AWS Region in which the logistics platform infrastructure will be deployed.
variable "aws_region" {
  description = "AWS Region used to deploy the project resources."
  type        = string
  default     = "ap-southeast-2"
}

// Short project identifier used in resource names and tags.
variable "project_name" {
  description = "Name of the project, used for resource naming and tagging."
  type        = string
  default     = "legacy-logistics"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "project_name must contain only lowercase letters, numbers, and hyphens."
  }
}

// Deployment stage used to distinguish isolated environments.
variable "environment" {
  description = "Deployment environment, such as dev, staging, or prod."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, or prod."
  }
}

// Address range allocated to the project VPC.
variable "vpc_cidr" {
  description = "IPv4 CIDR block assigned to the VPC."
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

// Availability Zones across which public and private subnets will be distributed.
variable "availability_zones" {
  description = "Ordered list of Availability Zones used by the project subnets."
  type        = list(string)
  default     = ["ap-southeast-2a", "ap-southeast-2b"]

  validation {
    condition     = length(var.availability_zones) >= 2 && length(distinct(var.availability_zones)) == length(var.availability_zones)
    error_message = "availability_zones must contain at least two unique Availability Zones."
  }
}

// Internet-facing subnet ranges, one for each configured Availability Zone.
variable "public_subnet_cidrs" {
  description = "Ordered list of IPv4 CIDR blocks for public subnets."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == length(var.availability_zones) && alltrue([for cidr in var.public_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "public_subnet_cidrs must contain one valid IPv4 CIDR block per Availability Zone."
  }
}

// Internal subnet ranges, one for each configured Availability Zone.
variable "private_subnet_cidrs" {
  description = "Ordered list of IPv4 CIDR blocks for private subnets."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == length(var.availability_zones) && alltrue([for cidr in var.private_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "private_subnet_cidrs must contain one valid IPv4 CIDR block per Availability Zone."
  }
}

// Safety control for deletion of the portfolio data lake and its stored objects.
variable "data_lake_force_destroy" {
  description = "Controls whether the S3 data lake bucket may be automatically deleted during Terraform destroy."
  type        = bool
  default     = false
}

// Public DNS name used by the API Gateway regional custom domain.
variable "api_domain_name" {
  description = "Fully qualified domain name for the logistics API, such as api.example.com."
  type        = string
}

// Existing public hosted zone in which certificate validation and API alias records are created.
variable "route53_zone_id" {
  description = "Route 53 hosted zone ID that contains the API domain name."
  type        = string
}

// Region-specific ARN supplied by the deployment environment rather than embedded in source code.
variable "secrets_extension_layer_arn" {
  description = "ARN of the AWS Parameters and Secrets Lambda Extension layer for the deployment Region."
  type        = string
}

// Retention period shared by Terraform-managed Lambda CloudWatch log groups.
variable "lambda_log_retention_days" {
  description = "Number of days to retain logs for each Lambda function."
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.lambda_log_retention_days)
    error_message = "lambda_log_retention_days must be a retention period supported by CloudWatch Logs."
  }
}
