# infra/environments/demo/prod/backend.tf
terraform {
  backend "s3" {
    bucket         = "localdoby-terraform-state-prod"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    use_lockfile   = true # Replaces deprecated dynamodb_table
  }
}
