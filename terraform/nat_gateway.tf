// The NAT Gateway gives private Lambda functions outbound access to external
// partner webhook endpoints without exposing those functions to inbound traffic.
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-nat-eip"
  })
}

// This portfolio deployment uses one NAT Gateway to control cost. A production
// deployment should consider one NAT Gateway per Availability Zone for resilience.
resource "aws_nat_gateway" "integration" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-nat"
  })

  depends_on = [aws_internet_gateway.integration]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.integration.id

  tags = merge(local.common_tags, {
    Name = "${local.common_name_prefix}-private-rt"
  })
}

resource "aws_route" "private_nat" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.integration.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
