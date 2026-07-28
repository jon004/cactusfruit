resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "localdoby-vpc"
  }
}

# Internet Gateway for outbound internet access (pip installs, SSM connectivity, etc.)
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "localdoby-igw"
  }
}

resource "aws_subnet" "db_subnet_us_east_1a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "localdoby-db-subnet-1a"
  }
}

resource "aws_subnet" "db_subnet_us_east_1b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"

  tags = {
    Name = "localdoby-db-subnet-1b"
  }
}

# Route Table for the subnets to use the Internet Gateway
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "localdoby-private-rt"
  }
}

resource "aws_route" "internet_access" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.gw.id
}

resource "aws_route_table_association" "private_1a" {
  subnet_id      = aws_subnet.db_subnet_us_east_1a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_1b" {
  subnet_id      = aws_subnet.db_subnet_us_east_1b.id
  route_table_id = aws_route_table.private.id
}

resource "aws_db_subnet_group" "db_group" {
  name       = "localdoby-db-subnet-group"
  subnet_ids = [
    aws_subnet.db_subnet_us_east_1a.id,
    aws_subnet.db_subnet_us_east_1b.id
  ]

  tags = {
    Name = "localdoby-db-subnet-group"
  }
}

resource "aws_security_group" "app" {
  name        = "localdoby-app-sg"
  description = "Security group for localdoby application"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "localdoby-app-sg"
  }
}

# IAM Role and Instance Profile for Ephemeral Migration Runner
resource "aws_iam_role" "migration_runner" {
  name = "localdoby-migration-runner-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_server" {
  role       = aws_iam_role.migration_runner.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# IAM Policy to allow the migration runner to read the database secret
resource "aws_iam_role_policy" "migration_runner_secrets" {
  name = "localdoby-migration-runner-secrets-policy"
  role = aws_iam_role.migration_runner.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = var.db_secret_arn
      }
    ]
  })
}

resource "aws_iam_instance_profile" "migration_runner" {
  name = "localdoby-migration-runner-profile"
  role = aws_iam_role.migration_runner.name
}
