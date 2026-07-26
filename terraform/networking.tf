// Integration VPC hosting private Lambda networking and supporting resources.
resource "aws_vpc" "integration" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-vpc"
  })
}

// Public subnets host internet-facing network infrastructure such as the NAT Gateway.
resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.integration.id
  availability_zone       = var.availability_zones[count.index]
  cidr_block              = var.public_subnet_cidrs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-public-${count.index + 1}"
  })
}

// Private subnets provide isolated networking for the integration Lambda functions.
resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id                  = aws_vpc.integration.id
  availability_zone       = var.availability_zones[count.index]
  cidr_block              = var.private_subnet_cidrs[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-private-${count.index + 1}"
  })
}

resource "aws_internet_gateway" "integration" {
  vpc_id = aws_vpc.integration.id

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-igw"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.integration.id

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-public-rt"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.integration.id
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
