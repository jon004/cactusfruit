# infra/environments/demo/prod/outputs.tf

output "db_endpoint" {
  value       = module.database.db_endpoint
  description = "The connection endpoint for the RDS instance."
}

output "db_secret_arn" {
  value       = module.database.db_secret_arn
  description = "The AWS Secrets Manager ARN containing DB credentials."
}

output "vpc_id" {
  value       = module.networking.vpc_id
  description = "The VPC ID for the environment."
}
