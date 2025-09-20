terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
  # TODO: Configure a remote backend (S3 + DynamoDB state locking)
  # backend "s3" {}
}

provider "aws" {
  region = var.region
}

module "vpc" {
  source   = "./modules/vpc"
  env_name = var.env_name
  tags     = var.tags
}

module "s3" {
  source        = "./modules/s3"
  env_name      = var.env_name
  artifacts_kms = null # TODO: add KMS key resource if needed
  tags          = var.tags
}

module "ecr" {
  source   = "./modules/ecr"
  env_name = var.env_name
  tags     = var.tags
}

module "rds" {
  source             = "./modules/rds"
  env_name           = var.env_name
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  tags               = var.tags
}

module "ecs" {
  source                = "./modules/ecs"
  env_name              = var.env_name
  region                = var.region
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  private_subnet_ids    = module.vpc.private_subnet_ids
  mlflow_bucket_name    = module.s3.mlflow_bucket
  evidently_bucket_name = module.s3.evidently_bucket
  api_repo_url          = module.ecr.repository_urls["api"]
  mlflow_repo_url       = module.ecr.repository_urls["mlflow"]
  evidently_repo_url    = module.ecr.repository_urls["evidently"]
  rds_endpoint          = module.rds.endpoint
  rds_port              = module.rds.port
  rds_secret_arn        = module.rds.secret_arn

  # Optional HTTPS configuration
  api_domain      = var.api_domain
  hosted_zone_id  = var.hosted_zone_id
  hosted_zone_name= var.hosted_zone_name

  tags = var.tags
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "mlflow_bucket" {
  value = module.s3.mlflow_bucket
}

output "evidently_bucket" {
  value = module.s3.evidently_bucket
}

output "api_alb_dns" { value = module.ecs.api_alb_dns }
output "mlflow_alb_dns" { value = module.ecs.mlflow_alb_dns }
output "evidently_alb_dns" { value = module.ecs.evidently_alb_dns }
output "prefect_alb_dns" { value = module.ecs.prefect_alb_dns }
output "cluster_name" { value = module.ecs.cluster_name }
