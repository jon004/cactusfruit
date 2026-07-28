# infra/modules/ecr/main.tf

resource "aws_ecr_repository" "pipeline" {
  name = "pipeline"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "embedder" {
  name = "embedder"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "generator" {
  name = "generator"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "reranker" {
  name = "reranker"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "fact_extractor" {
  name = "fact-extractor"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "query_generator" {
  name = "query-generator"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "fact_judge" {
  name = "fact-judge"

  image_scanning_configuration {
    scan_on_push = true
  }
}
