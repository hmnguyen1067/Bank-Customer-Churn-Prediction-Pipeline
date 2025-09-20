variable "env_name" { type = string }
variable "region" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "mlflow_bucket_name" { type = string }
variable "evidently_bucket_name" { type = string }
variable "api_repo_url" { type = string }
variable "mlflow_repo_url" { type = string }
variable "evidently_repo_url" { type = string }
variable "rds_endpoint" { type = string }
variable "rds_port" { type = string }
variable "rds_secret_arn" { type = string }
variable "api_domain" { type = string, default = null }
variable "hosted_zone_id" { type = string, default = null }
variable "hosted_zone_name" { type = string, default = null }
variable "tags" { type = map(string), default = {} }
