# infra/modules/languagemodels/sagemaker.tf

resource "aws_iam_role" "this" {
  count = local.use_sagemaker ? 1 : 0
  name  = "${local.name_prefix}-sagemaker-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "sagemaker.amazonaws.com"
      }
    }]
  })
}

resource "aws_sagemaker_model" "this" {
  count              = local.use_sagemaker ? 1 : 0
  execution_role_arn = aws_iam_role.this[0].arn
  name               = local.name_prefix

  primary_container {
    image = var.image_uri
  }
}

resource "aws_sagemaker_endpoint_config" "this" {
  count = local.use_sagemaker ? 1 : 0
  name  = "${local.name_prefix}-config"

  production_variant {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.this[0].name
    initial_instance_count = 1

    serverless_config {
      memory_size_in_mb = var.deployment.sagemaker.memory_size_in_mb
      max_concurrency   = var.deployment.sagemaker.max_concurrency
    }

    dynamic "vpc_config" {
      for_each = var.vpc_config != null ? [var.vpc_config] : []
      content {
        subnets            = vpc_config.value.subnet_ids
        security_group_ids = vpc_config.value.security_group_ids
      }
    }
  }
}

resource "aws_sagemaker_endpoint" "this" {
  count                = local.use_sagemaker ? 1 : 0
  name                 = local.name_prefix
  endpoint_config_name = aws_sagemaker_endpoint_config.this[0].name
}
