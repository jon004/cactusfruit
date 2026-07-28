# infra/environments/demo/prod/providers.tf
provider "aws" {
  region = "us-east-1" # Set to your preferred region
  allowed_account_ids = ["750907156216"]
}
