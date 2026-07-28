# infra/modules/languagemodels/variables.tf

variable "environment_name" {
  type        = string
  description = "Name of the deployment environment (e.g., dev, staging, prod)."
}

variable "model_name" {
  type        = string
  description = "Logical name of the language model (e.g., embedder, generator)."
}

variable "image_uri" {
  type        = string
  description = "The ECR image URI containing the model artifacts and serving code."
}

variable "platform" {
  type        = string
  description = "The target deployment platform for the model."

  validation {
    condition = contains([
      "lambda",
      "sagemaker"
    ], var.platform)
    error_message = "Platform must be either 'lambda' or 'sagemaker'."
  }
}

variable "deployment" {
  type = object({
    lambda = optional(object({
      memory_size = optional(number, 1024)
      timeout     = optional(number, 30)
    }), {})
    sagemaker = optional(object({
      memory_size_in_mb = optional(number, 3072)
      max_concurrency   = optional(number, 8)
    }), {})
  })
  description = "Platform-specific configuration parameters."
  default     = {}
}

variable "vpc_config" {
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  description = "VPC subnet and security group IDs for network isolation."
  default     = null
}
