# infra/environments/demo/prod/main.tf

module "ecr" {
  source           = "../../../modules/ecr"
  environment_name = "demo-prod"
}

module "database" {
  source                = "../../../modules/database"
  environment_name      = "demo-prod"
  vpc_id                = module.networking.vpc_id
  db_subnet_group_name  = module.networking.db_subnet_group_name
  app_security_group_id = module.networking.app_security_group_id
}

module "networking" {
  source        = "../../../modules/networking"
  db_secret_arn = module.database.db_secret_arn
}

#module "embedder" {
#  source = "../../../modules/languagemodels"

#  environment_name = var.environment_name
#  model_name       = "embedder"
#  image_uri        = "${module.ecr.embedder_repository_url}:latest"
#  platform         = "lambda"

#  deployment = {
#    lambda = {
#      memory_size = 1024
#      timeout     = 30
#    }
#  }

#  vpc_config = {
#    subnet_ids         = [module.networking.db_subnet_us_east_1a_id, module.networking.db_subnet_us_east_1b_id]
#    security_group_ids = [module.networking.app_security_group_id]
#  }
#}

#module "generator" {
#  source = "../../../modules/languagemodels"

#  environment_name = var.environment_name
#  model_name       = "generator"
#  image_uri        = "${module.ecr.generator_repository_url}:latest"
#  platform         = "sagemaker"

#  deployment = {
#    sagemaker = {
#      memory_size_in_mb = 4096
#      max_concurrency   = 10
#    }
#  }

#  vpc_config = {
#    subnet_ids         = [module.networking.db_subnet_us_east_1a_id, module.networking.db_subnet_us_east_1b_id]
#    security_group_ids = [module.networking.app_security_group_id]
#  }
#}

#module "reranker" {
#  source = "../../../modules/languagemodels"

#  environment_name = var.environment_name
#  model_name       = "reranker"
#  image_uri        = "${module.ecr.reranker_repository_url}:latest"
#  platform         = "sagemaker"

#  deployment = {
#    sagemaker = {
#      memory_size_in_mb = 3072
#      max_concurrency   = 5
#    }
#  }

#  vpc_config = {
#    subnet_ids         = [module.networking.db_subnet_us_east_1a_id, module.networking.db_subnet_us_east_1b_id]
#    security_group_ids = [module.networking.app_security_group_id]
#  }
#}

#module "fact_extractor" {
#  source = "../../../modules/languagemodels"

#  environment_name = var.environment_name
#  model_name       = "fact-extractor"
#  image_uri        = "${module.ecr.fact_extractor_repository_url}:latest"
#  platform         = "sagemaker"

#  deployment = {
#    sagemaker = {
#      memory_size_in_mb = 3072
#      max_concurrency   = 5
#    }
#  }

#  vpc_config = {
#    subnet_ids         = [module.networking.db_subnet_us_east_1a_id, module.networking.db_subnet_us_east_1b_id]
#    security_group_ids = [module.networking.app_security_group_id]
#  }
#}

#module "query_generator" {
#  source = "../../../modules/languagemodels"

#  environment_name = var.environment_name
#  model_name       = "query-generator"
#  image_uri        = "${module.ecr.query_generator_repository_url}:latest"
#  platform         = "sagemaker"

#  deployment = {
#    sagemaker = {
#      memory_size_in_mb = 3072
#      max_concurrency   = 5
#    }
#  }

#  vpc_config = {
#    subnet_ids         = [module.networking.db_subnet_us_east_1a_id, module.networking.db_subnet_us_east_1b_id]
#    security_group_ids = [module.networking.app_security_group_id]
#  }
#}

#module "fact_judge" {
#  source = "../../../modules/languagemodels"

#  environment_name = var.environment_name
#  model_name       = "fact-judge"
#  image_uri        = "${module.ecr.fact_judge_repository_url}:latest"
#  platform         = "sagemaker"

#  deployment = {
#    sagemaker = {
#      memory_size_in_mb = 3072
#      max_concurrency   = 5
#    }
#  }

#  vpc_config = {
#    subnet_ids         = [module.networking.db_subnet_us_east_1a_id, module.networking.db_subnet_us_east_1b_id]
#    security_group_ids = [module.networking.app_security_group_id]
#  }
#}

#module "pipeline" {
#  source             = "../../../modules/pipeline"
#  environment_name   = var.environment_name
#  image_uri          = "${module.ecr.pipeline_repository_url}:latest"
#  subnet_ids         = [module.networking.db_subnet_us_east_1a_id, module.networking.db_subnet_us_east_1b_id]
#  security_group_ids = [module.networking.app_security_group_id]

#  model_arns = [
#    module.embedder.deployment.arn,
#    module.generator.deployment.arn,
#    module.reranker.deployment.arn,
#    module.fact_extractor.deployment.arn,
#    module.query_generator.deployment.arn,
#    module.fact_judge.deployment.arn
#  ]
#}
