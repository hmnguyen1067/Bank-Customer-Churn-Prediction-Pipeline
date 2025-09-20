# Terraform Skeleton

This is a lightweight Terraform scaffold for the migration. It creates the core modules and wires a minimal root configuration. Extend modules as needed to match the CDK plan or choose one tool.

Included (skeleton → expanded):
- Provider + remote backend placeholders
- `vpc` module (public/private subnets)
- `s3` module (MLflow and Evidently buckets)
- `ecr` module (repositories for api/mlflow/evidently)
- `rds` module (PostgreSQL instance + admin secret)
- `ecs` module (cluster, ALBs, HTTPS/ACM for API, WAF, services for api/mlflow/evidently/prefect, DB-init tasks)

## Usage
```bash
cd infra/aws/terraform
terraform init
terraform plan -var env_name=dev -var region=us-east-1 \
  -var api_domain="api.dev.example.com" -var hosted_zone_id="Z123EXAMPLE" -var hosted_zone_name="example.com"
terraform apply -var env_name=dev -var region=us-east-1 \
  -var api_domain="api.dev.example.com" -var hosted_zone_id="Z123EXAMPLE" -var hosted_zone_name="example.com"
```

## Variables
- `env_name` (string) — dev/stage/prod
- `region` (string)
- `tags` (map(string))
 - `api_domain` (string, optional) — FQDN for API ALB HTTPS (ACM)
 - `hosted_zone_id`/`hosted_zone_name` (string, optional) — Route53 zone for DNS validation and alias

## Next Steps (TODO)
- Add VPC endpoints (S3 Gateway, and interface endpoints for ECR/ECR Docker/Logs/Secrets/SSM) to reduce NAT traffic.
- Tune IAM task policies to least privilege per service/bucket prefixes.
- Push container images to ECR repos; update task definitions to pin image tags.
- Adjust autoscaling policies and desired counts per workload.
