# infra/modules/pipeline/variables.tf

variable "environment_name" {
  type        = string
  description = "The environment name (e.g., demo, prod)"
}

variable "image_uri" {
  type        = string
  description = "The ECR URI for the localdoby-pipeline image"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for the Lambda function"
}

variable "security_group_ids" {
  type        = list(string)
  description = "List of security group IDs for the Lambda function"
}

variable "model_arns" {
  type        = list(string)
  description = "List of language model ARNs that the pipeline can invoke"
  default     = []
}
