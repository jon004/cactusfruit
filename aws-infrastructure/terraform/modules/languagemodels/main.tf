# infra/modules/languagemodels/main.tf

locals {
  use_lambda    = var.platform == "lambda"
  use_sagemaker = var.platform == "sagemaker"

  name_prefix = "${var.environment_name}-${var.model_name}"
}
