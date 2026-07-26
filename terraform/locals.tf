locals {
  // Consistent prefix for names of resources belonging to this environment.
  common_name_prefix = "${var.project_name}-${var.environment}"

  // Shared tags for resources that do not inherit the provider's default tags.
  common_tags = {
    Project          = var.project_name
    Environment      = var.environment
    ManagedBy        = "Terraform"
    PortfolioProject = "Modernizing a Legacy Logistics Platform"
  }
}
