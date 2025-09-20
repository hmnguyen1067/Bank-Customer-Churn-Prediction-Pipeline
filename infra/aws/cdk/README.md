# AWS CDK (Python) Skeleton

This CDK app provides a minimal, production-leaning scaffold for the AWS migration (no Kubernetes). It creates the core building blocks and leaves clear TODOs to wire application-specific details.

Included (scaffold):
- VPC with public/private subnets (3 AZs)
- S3 buckets for MLflow artifacts and Evidently workspace (encrypted, versioned)
- RDS PostgreSQL instance (credentials in Secrets Manager)
- ECS cluster (Fargate-capable)
- Public and internal ALBs (HTTP by default; HTTPS optional with ACM)
- CloudWatch log groups for services (placeholders)
- Baseline IAM roles/policies for ECS tasks (examples/TODOs)
- ECR repositories for `api`, `mlflow`, `evidently`
- WAF v2 (regional) attached to API ALB (managed rule set)
- VPC endpoints: S3 Gateway; interface endpoints for ECR/ECR Docker/CloudWatch Logs/Secrets/SSM
- ECS Services: API (public), MLflow (internal), Evidently (internal), Prefect server (internal), Prefect worker
- DB init Fargate task defs to create `mlflow` and `prefect` databases

## Prerequisites
- Python 3.11+
- Node.js (for CDK CLI)
- AWS CLI configured; account bootstrapped for CDK: `cdk bootstrap aws://<account>/<region>`

## Setup
```bash
cd infra/aws/cdk
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Synthesize
cdk synth --context envName=dev --context region=us-east-1 --context account=123456789012

# Optional: if you want HTTPS on the public API ALB, add domain context
#   --context apiDomain=api.dev.example.com --context hostedZoneName=example.com --context hostedZoneId=Z123EXAMPLE

# Deploy (creates/updates stacks)
cdk deploy "*" --require-approval never \
  --context envName=dev \
  --context region=us-east-1 \
  --context account=123456789012 \
  --context apiDomain=api.dev.example.com \
  --context hostedZoneName=example.com \
  --context hostedZoneId=Z123EXAMPLE
```

## Context Parameters
- `envName`: Environment name (e.g., dev, stage, prod)
- `region`: AWS region
- `account`: AWS account ID
- `apiDomain` (optional): FQDN for the public API ALB certificate (e.g., api.dev.example.com)
- `hostedZoneName`/`hostedZoneId` (optional): Route53 hosted zone for DNS validation

## Next Steps (TODO)
- Push Docker images to the created ECR repos (`api`, `mlflow`, `evidently`) and update tags if not using `latest`.
- Attach ACM cert and update DNS (if using HTTPS) as shown above; add Route53 A/AAAA alias if needed.
- Add VPC Interface Endpoints (ECR, Logs, Secrets, SSM) for private egress minimization.
- Tighten IAM policies to least-privilege per-service.
- (Optional) Tune WAF rules beyond the default managed CommonRuleSet.

## ECR: Build and Push
```bash
AWS_ACCOUNT=123456789012
AWS_REGION=us-east-1
ENV=dev

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

# API
docker build -t $ENV-api -f infra/Dockerfile.api .
docker tag $ENV-api:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ENV-api:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ENV-api:latest

# MLflow (build from infra/Dockerfile.mlflow)
docker build -t $ENV-mlflow -f infra/Dockerfile.mlflow infra
docker tag $ENV-mlflow:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ENV-mlflow:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ENV-mlflow:latest

# Evidently (build from infra/Dockerfile.evidently)
docker build -t $ENV-evidently -f infra/Dockerfile.evidently infra
docker tag $ENV-evidently:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ENV-evidently:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$ENV-evidently:latest
```

Note: Repositories are created by CDK as `<env>-api`, `<env>-mlflow`, `<env>-evidently`.

## Run the DB Init Tasks (one-off)
These create the `mlflow` and `prefect` databases in RDS. Replace placeholders accordingly.

```bash
CLUSTER_ARN=$(aws ecs list-clusters --query 'clusterArns[0]' --output text)
SUBNETS=$(aws ec2 describe-subnets --filters 'Name=tag:Name,Values=*private*' --query 'Subnets[*].SubnetId' --output text)
SECURITY_GROUP=$(aws ec2 describe-security-groups --filters 'Name=group-name,Values=*ServicesSg*' --query 'SecurityGroups[0].GroupId' --output text)

# Mlflow
aws ecs run-task \
  --cluster $CLUSTER_ARN \
  --launch-type FARGATE \
  --task-definition dev-ecs-DbInitMlflowTask \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}"

# Prefect
aws ecs run-task \
  --cluster $CLUSTER_ARN \
  --launch-type FARGATE \
  --task-definition dev-ecs-DbInitPrefectTask \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}"
```

Alternatively, run via the AWS Console → ECS → Tasks → Run new task.
