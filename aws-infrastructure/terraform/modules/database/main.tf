# modules/database/main.tf

resource "aws_db_instance" "postgres" {
  identifier             = "${var.environment_name}-db"
  engine                 = "postgres"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  db_name                = "localdoby"
  username               = "dbadmin"

  # Enable RDS-managed master password
  manage_master_user_password = true
  
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = var.db_subnet_group_name
  skip_final_snapshot    = true
}

resource "aws_security_group" "db_sg" {
  name        = "${var.environment_name}-db-sg"
  description = "Allow inbound from pipeline lambda"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.app_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
