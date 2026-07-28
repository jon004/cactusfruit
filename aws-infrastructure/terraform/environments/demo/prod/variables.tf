# infra/environments/demo/prod/variables.tf

variable "environment_name" {
  type        = string
  description = "The environment name"
  default     = "demo-prod"
}
