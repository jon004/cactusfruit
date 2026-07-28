output "db_secret_arn" { 
  value = aws_db_instance.postgres.master_user_secret[0].secret_arn 
}

output "db_security_group_id" { 
  value = aws_security_group.db_sg.id 
}

output "db_endpoint" {
  value = aws_db_instance.postgres.endpoint
}
