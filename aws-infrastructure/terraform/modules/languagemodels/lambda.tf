# infra/modules/languagemodels/lambda.tf

resource "aws_iam_role" "this" {
  count = local.use_lambda ? 1 : 0
  name  = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_lambda_function" "this" {
  count         = local.use_lambda ? 1 : 0
  function_name = local.name_prefix
  role          = aws_iam_role.this[0].arn
  package_type  = "Image"
  image_uri     = var.image_uri

  memory_size = var.deployment.lambda.memory_size
  timeout     = var.deployment.lambda.timeout

  image_config {
    command = []
  }

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }
}
