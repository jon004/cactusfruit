# infra/modules/languagemodels/outputs.tf

output "deployment" {
  description = "Normalized deployment details for the language model."
  value = {
    platform = var.platform
    name = local.use_lambda ? try(aws_lambda_function.this[0].function_name, null) : (
      local.use_sagemaker ? try(aws_sagemaker_endpoint.this[0].name, null) : null
    )
    arn = local.use_lambda ? try(aws_lambda_function.this[0].arn, null) : (
      local.use_sagemaker ? try(aws_sagemaker_endpoint.this[0].arn, null) : null
    )
  }
}
