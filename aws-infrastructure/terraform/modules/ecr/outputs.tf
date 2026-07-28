# infra/modules/ecr/outputs.tf

output "pipeline_repository_url" {
  value = aws_ecr_repository.pipeline.repository_url
}

output "embedder_repository_url" {
  value = aws_ecr_repository.embedder.repository_url
}

output "generator_repository_url" {
  value = aws_ecr_repository.generator.repository_url
}

output "reranker_repository_url" {
  value = aws_ecr_repository.reranker.repository_url
}

output "fact_extractor_repository_url" {
  value = aws_ecr_repository.fact_extractor.repository_url
}

output "query_generator_repository_url" {
  value = aws_ecr_repository.query_generator.repository_url
}

output "fact_judge_generator_repository_url" {
  value = aws_ecr_repository.fact_judge.repository_url
}
