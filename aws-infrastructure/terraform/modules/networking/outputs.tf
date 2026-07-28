# infra/modules/networking/outputs.tf

output "vpc_id" {
  value = aws_vpc.main.id
}

output "db_subnet_group_name" {
  value = aws_db_subnet_group.db_group.name
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "private_route_table_id" {
  value = aws_route_table.private.id
}

output "migration_runner_instance_profile_name" {
  value = aws_iam_instance_profile.migration_runner.name
}

# Add these two outputs:
output "db_subnet_us_east_1a_id" {
  value = aws_subnet.db_subnet_us_east_1a.id
}

output "db_subnet_us_east_1b_id" {
  value = aws_subnet.db_subnet_us_east_1b.id
}
