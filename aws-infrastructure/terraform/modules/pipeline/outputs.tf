# infra/modules/pipeline/outputs.tf

output "lambda_function_name" {
  description = "The name of the pipeline Lambda function"
  value       = aws_lambda_function.pipeline.function_name
}

output "lambda_function_arn" {
  description = "The ARN of the pipeline Lambda function"
  value       = aws_lambda_function.pipeline.arn
}

