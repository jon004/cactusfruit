# infra/modules/pipeline/main.tf

resource "aws_iam_role" "pipeline_role" {
  name = "${var.environment_name}-localdoby-pipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "model_invoke" {
  name = "${var.environment_name}-pipeline-model-invoke-policy"
  role = aws_iam_role.pipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = [for arn in var.model_arns : arn if can(regex("lambda", arn))]
      },
      {
        Effect   = "Allow"
        Action   = ["sagemaker:InvokeEndpoint"]
        Resource = [for arn in var.model_arns : arn if can(regex("sagemaker", arn))]
      }
    ]
  })
}

resource "aws_lambda_function" "pipeline" {
  function_name = "${var.environment_name}-localdoby-pipeline"
  package_type  = "Image"
  image_uri     = var.image_uri
  role          = aws_iam_role.pipeline_role.arn

  # Pipeline specific configuration
  timeout     = 300
  memory_size = 512

  # VPC Configuration to allow connection to the database
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
}
