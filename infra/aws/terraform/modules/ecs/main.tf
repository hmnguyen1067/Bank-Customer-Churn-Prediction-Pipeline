locals {
  logs_retention = 90
}

resource "aws_security_group" "services" {
  name        = "${var.env_name}-services-sg"
  description = "ECS services"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "${var.env_name}-services-sg" })
}

resource "aws_ecs_cluster" "this" {
  name = "${var.env_name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = var.tags
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "api" { name = "/ecs/${var.env_name}/api" retention_in_days = local.logs_retention }
resource "aws_cloudwatch_log_group" "mlflow" { name = "/ecs/${var.env_name}/mlflow" retention_in_days = local.logs_retention }
resource "aws_cloudwatch_log_group" "evidently" { name = "/ecs/${var.env_name}/evidently" retention_in_days = local.logs_retention }
resource "aws_cloudwatch_log_group" "prefect" { name = "/ecs/${var.env_name}/prefect" retention_in_days = local.logs_retention }

# ALBs
resource "aws_lb" "api" {
  name               = "${var.env_name}-api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = []
  subnets            = var.public_subnet_ids
  tags               = var.tags
}

resource "aws_lb" "mlflow" {
  name               = "${var.env_name}-mlflow-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = []
  subnets            = var.private_subnet_ids
  tags               = var.tags
}

resource "aws_lb" "evidently" {
  name               = "${var.env_name}-evidently-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = []
  subnets            = var.private_subnet_ids
  tags               = var.tags
}

resource "aws_lb" "prefect" {
  name               = "${var.env_name}-prefect-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = []
  subnets            = var.private_subnet_ids
  tags               = var.tags
}

# Listeners
resource "aws_lb_listener" "api_http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"
  default_action { type = "fixed-response" fixed_response { content_type = "text/plain" message_body = "HTTP" status_code = "200" } }
}

resource "aws_acm_certificate" "api" {
  count                     = var.api_domain != null && var.hosted_zone_id != null ? 1 : 0
  domain_name               = var.api_domain
  validation_method         = "DNS"
  lifecycle { create_before_destroy = true }
}

data "aws_route53_zone" "api" {
  count = var.api_domain != null && var.hosted_zone_id != null ? 1 : 0
  zone_id = var.hosted_zone_id
}

resource "aws_route53_record" "api_validation" {
  count   = var.api_domain != null && var.hosted_zone_id != null ? 1 : 0
  zone_id = data.aws_route53_zone.api[0].zone_id
  name    = aws_acm_certificate.api[0].domain_validation_options[0].resource_record_name
  type    = aws_acm_certificate.api[0].domain_validation_options[0].resource_record_type
  records = [aws_acm_certificate.api[0].domain_validation_options[0].resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "api" {
  count                   = var.api_domain != null && var.hosted_zone_id != null ? 1 : 0
  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [aws_route53_record.api_validation[0].fqdn]
}

resource "aws_lb_listener" "api_https" {
  count             = var.api_domain != null && var.hosted_zone_id != null ? 1 : 0
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate_validation.api[0].certificate_arn
  default_action { type = "fixed-response" fixed_response { content_type = "text/plain" message_body = "HTTPS" status_code = "200" } }
}

resource "aws_route53_record" "api_alias" {
  count   = var.api_domain != null && var.hosted_zone_id != null ? 1 : 0
  zone_id = data.aws_route53_zone.api[0].zone_id
  name    = var.api_domain
  type    = "A"
  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

resource "aws_wafv2_web_acl" "api" {
  name        = "${var.env_name}-api-waf"
  description = "Managed protection for API ALB"
  scope       = "REGIONAL"
  default_action { allow {} }
  visibility_config { cloudwatch_metrics_enabled = true metric_name = "${var.env_name}-api-waf" sampled_requests_enabled = true }
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1
    override_action { none {} }
    statement { managed_rule_group_statement { name = "AWSManagedRulesCommonRuleSet" vendor_name = "AWS" } }
    visibility_config { cloudwatch_metrics_enabled = true metric_name = "CommonRuleSet" sampled_requests_enabled = true }
  }
}

resource "aws_wafv2_web_acl_association" "api" {
  resource_arn = aws_lb.api.arn
  web_acl_arn  = aws_wafv2_web_acl.api.arn
}

# Target Groups
resource "aws_lb_target_group" "api" { name = "${var.env_name}-api-tg" port = 8001 protocol = "HTTP" vpc_id = var.vpc_id health_check { path = "/" } }
resource "aws_lb_target_group" "mlflow" { name = "${var.env_name}-mlflow-tg" port = 5000 protocol = "HTTP" vpc_id = var.vpc_id health_check { path = "/" } }
resource "aws_lb_target_group" "evidently" { name = "${var.env_name}-evidently-tg" port = 8000 protocol = "HTTP" vpc_id = var.vpc_id health_check { path = "/" } }
resource "aws_lb_target_group" "prefect" { name = "${var.env_name}-prefect-tg" port = 4200 protocol = "HTTP" vpc_id = var.vpc_id health_check { path = "/api/health" } }

resource "aws_lb_listener_rule" "api_forward" {
  listener_arn = coalesce(try(aws_lb_listener.api_https[0].arn, null), aws_lb_listener.api_http.arn)
  action { type = "forward" target_group_arn = aws_lb_target_group.api.arn }
  condition { path_pattern { values = ["/*"] } }
}

resource "aws_lb_listener" "mlflow_http" { load_balancer_arn = aws_lb.mlflow.arn port = 80 protocol = "HTTP" default_action { type = "forward" target_group_arn = aws_lb_target_group.mlflow.arn } }
resource "aws_lb_listener" "evidently_http" { load_balancer_arn = aws_lb.evidently.arn port = 80 protocol = "HTTP" default_action { type = "forward" target_group_arn = aws_lb_target_group.evidently.arn } }
resource "aws_lb_listener" "prefect_http" { load_balancer_arn = aws_lb.prefect.arn port = 80 protocol = "HTTP" default_action { type = "forward" target_group_arn = aws_lb_target_group.prefect.arn } }

# IAM Roles
data "aws_iam_policy_document" "task_assume" { statement { actions = ["sts:AssumeRole"] principals { type = "Service" identifiers = ["ecs-tasks.amazonaws.com"] } } }

resource "aws_iam_role" "execution" {
  name               = "${var.env_name}-ecs-exec"
  assume_role_policy = data.aws_iam_policy_document.task_assume.json
}
resource "aws_iam_role_policy_attachment" "exec_attach" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "task_policy" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.rds_secret_arn]
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [
      "arn:aws:s3:::${var.mlflow_bucket_name}",
      "arn:aws:s3:::${var.mlflow_bucket_name}/*",
      "arn:aws:s3:::${var.evidently_bucket_name}",
      "arn:aws:s3:::${var.evidently_bucket_name}/*",
    ]
  }
}
resource "aws_iam_role" "task" { name = "${var.env_name}-ecs-task" assume_role_policy = data.aws_iam_policy_document.task_assume.json }
resource "aws_iam_role_policy" "task_inline" { name = "${var.env_name}-ecs-task-inline" role = aws_iam_role.task.id policy = data.aws_iam_policy_document.task_policy.json }

# Task Definitions
locals {
  common_linux = {
    networkMode             = "awsvpc"
    requiresCompatibilities = ["FARGATE"]
    cpu                     = "512"
    memory                  = "1024"
    executionRoleArn        = aws_iam_role.execution.arn
    taskRoleArn             = aws_iam_role.task.arn
  }
}

resource "aws_ecs_task_definition" "mlflow" {
  family                   = "${var.env_name}-mlflow"
  cpu                      = local.common_linux.cpu
  memory                   = local.common_linux.memory
  network_mode             = local.common_linux.networkMode
  requires_compatibilities = local.common_linux.requiresCompatibilities
  execution_role_arn       = local.common_linux.executionRoleArn
  task_role_arn            = local.common_linux.taskRoleArn
  container_definitions    = jsonencode([
    {
      name  = "mlflow"
      image = "${var.mlflow_repo_url}:latest"
      portMappings = [{ containerPort = 5000, protocol = "tcp" }]
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.mlflow.name, awslogs-region = var.region, awslogs-stream-prefix = "ecs" } }
      environment = [
        { name = "DB_HOST", value = var.rds_endpoint },
        { name = "DB_PORT", value = var.rds_port },
        { name = "DB_NAME", value = "mlflow" },
        { name = "MLFLOW_BUCKET", value = var.mlflow_bucket_name },
      ]
      secrets = [
        { name = "DB_USER", valueFrom = "${var.rds_secret_arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${var.rds_secret_arn}:password::" },
      ]
      command = ["sh", "-lc", "mlflow server --backend-store-uri \"postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}\" --host 0.0.0.0 --serve-artifacts --artifacts-destination s3://${MLFLOW_BUCKET}" ]
      environmentFiles = []
      essential = true
    }
  ])
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.env_name}-api"
  cpu                      = local.common_linux.cpu
  memory                   = local.common_linux.memory
  network_mode             = local.common_linux.networkMode
  requires_compatibilities = local.common_linux.requiresCompatibilities
  execution_role_arn       = local.common_linux.executionRoleArn
  task_role_arn            = local.common_linux.taskRoleArn
  container_definitions    = jsonencode([
    {
      name  = "api"
      image = "${var.api_repo_url}:latest"
      portMappings = [{ containerPort = 8001, protocol = "tcp" }]
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.api.name, awslogs-region = var.region, awslogs-stream-prefix = "ecs" } }
      environment = [
        { name = "MLFLOW_TRACKING_URI", value = "http://${aws_lb.mlflow.dns_name}" }
      ]
      essential = true
    }
  ])
}

resource "aws_ecs_task_definition" "evidently" {
  family                   = "${var.env_name}-evidently"
  cpu                      = local.common_linux.cpu
  memory                   = local.common_linux.memory
  network_mode             = local.common_linux.networkMode
  requires_compatibilities = local.common_linux.requiresCompatibilities
  execution_role_arn       = local.common_linux.executionRoleArn
  task_role_arn            = local.common_linux.taskRoleArn
  container_definitions    = jsonencode([
    {
      name  = "evidently"
      image = "${var.evidently_repo_url}:latest"
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.evidently.name, awslogs-region = var.region, awslogs-stream-prefix = "ecs" } }
      command = ["--workspace", "s3://${var.evidently_bucket_name}/workspace"]
      essential = true
    }
  ])
}

resource "aws_ecs_task_definition" "prefect_server" {
  family                   = "${var.env_name}-prefect-server"
  cpu                      = local.common_linux.cpu
  memory                   = local.common_linux.memory
  network_mode             = local.common_linux.networkMode
  requires_compatibilities = local.common_linux.requiresCompatibilities
  execution_role_arn       = local.common_linux.executionRoleArn
  task_role_arn            = local.common_linux.taskRoleArn
  container_definitions    = jsonencode([
    {
      name  = "prefect-server"
      image = "prefecthq/prefect:3-latest"
      portMappings = [{ containerPort = 4200, protocol = "tcp" }]
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.prefect.name, awslogs-region = var.region, awslogs-stream-prefix = "ecs" } }
      environment = [
        { name = "PREFECT_SERVER_API_HOST", value = "0.0.0.0" },
        { name = "DB_HOST", value = var.rds_endpoint },
        { name = "DB_PORT", value = var.rds_port },
        { name = "DB_NAME", value = "prefect" },
        { name = "PREFECT_API_DATABASE_CONNECTION_URL", value = "postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}" },
      ]
      secrets = [
        { name = "DB_USER", valueFrom = "${var.rds_secret_arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${var.rds_secret_arn}:password::" },
      ]
      command = ["/bin/sh", "-lc", "prefect server start"]
      essential = true
    }
  ])
}

resource "aws_ecs_task_definition" "prefect_worker" {
  family                   = "${var.env_name}-prefect-worker"
  cpu                      = local.common_linux.cpu
  memory                   = local.common_linux.memory
  network_mode             = local.common_linux.networkMode
  requires_compatibilities = local.common_linux.requiresCompatibilities
  execution_role_arn       = local.common_linux.executionRoleArn
  task_role_arn            = local.common_linux.taskRoleArn
  container_definitions    = jsonencode([
    {
      name  = "prefect-worker"
      image = "prefecthq/prefect:3-latest"
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.prefect.name, awslogs-region = var.region, awslogs-stream-prefix = "ecs" } }
      environment = [
        { name = "PREFECT_API_URL", value = "http://${aws_lb.prefect.dns_name}/api" }
      ]
      command = ["/bin/sh", "-lc", "prefect worker start -p \"default\" --name worker-${var.env_name}"]
      essential = true
    }
  ])
}

# Services
resource "aws_ecs_service" "mlflow" {
  name                               = "${var.env_name}-mlflow"
  cluster                            = aws_ecs_cluster.this.arn
  task_definition                    = aws_ecs_task_definition.mlflow.arn
  desired_count                      = 1
  launch_type                        = "FARGATE"
  enable_execute_command             = true
  network_configuration { subnets = var.private_subnet_ids security_groups = [aws_security_group.services.id] assign_public_ip = false }
  load_balancer { target_group_arn = aws_lb_target_group.mlflow.arn container_name = "mlflow" container_port = 5000 }
}

resource "aws_ecs_service" "api" {
  name                               = "${var.env_name}-api"
  cluster                            = aws_ecs_cluster.this.arn
  task_definition                    = aws_ecs_task_definition.api.arn
  desired_count                      = 1
  launch_type                        = "FARGATE"
  enable_execute_command             = true
  network_configuration { subnets = var.private_subnet_ids security_groups = [aws_security_group.services.id] assign_public_ip = false }
  load_balancer { target_group_arn = aws_lb_target_group.api.arn container_name = "api" container_port = 8001 }
}

resource "aws_ecs_service" "evidently" {
  name                               = "${var.env_name}-evidently"
  cluster                            = aws_ecs_cluster.this.arn
  task_definition                    = aws_ecs_task_definition.evidently.arn
  desired_count                      = 1
  launch_type                        = "FARGATE"
  enable_execute_command             = true
  network_configuration { subnets = var.private_subnet_ids security_groups = [aws_security_group.services.id] assign_public_ip = false }
  load_balancer { target_group_arn = aws_lb_target_group.evidently.arn container_name = "evidently" container_port = 8000 }
}

resource "aws_ecs_service" "prefect_server" {
  name                               = "${var.env_name}-prefect-server"
  cluster                            = aws_ecs_cluster.this.arn
  task_definition                    = aws_ecs_task_definition.prefect_server.arn
  desired_count                      = 1
  launch_type                        = "FARGATE"
  enable_execute_command             = true
  network_configuration { subnets = var.private_subnet_ids security_groups = [aws_security_group.services.id] assign_public_ip = false }
  load_balancer { target_group_arn = aws_lb_target_group.prefect.arn container_name = "prefect-server" container_port = 4200 }
}

resource "aws_ecs_service" "prefect_worker" {
  name                               = "${var.env_name}-prefect-worker"
  cluster                            = aws_ecs_cluster.this.arn
  task_definition                    = aws_ecs_task_definition.prefect_worker.arn
  desired_count                      = 1
  launch_type                        = "FARGATE"
  enable_execute_command             = true
  network_configuration { subnets = var.private_subnet_ids security_groups = [aws_security_group.services.id] assign_public_ip = false }
}

# DB Init Task Definitions (one-off)
resource "aws_ecs_task_definition" "db_init_mlflow" {
  family                   = "${var.env_name}-db-init-mlflow"
  cpu                      = "256"
  memory                   = "512"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([
    {
      name  = "db-init-mlflow"
      image = "postgres:14"
      command = ["/bin/sh", "-lc", "psql postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/postgres -v ON_ERROR_STOP=1 -c 'CREATE DATABASE mlflow;' || true"]
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.mlflow.name, awslogs-region = var.region, awslogs-stream-prefix = "ecs" } }
      environment = [
        { name = "DB_HOST", value = var.rds_endpoint },
        { name = "DB_PORT", value = var.rds_port },
      ]
      secrets = [
        { name = "DB_USER", valueFrom = "${var.rds_secret_arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${var.rds_secret_arn}:password::" },
      ]
      essential = true
    }
  ])
}

resource "aws_ecs_task_definition" "db_init_prefect" {
  family                   = "${var.env_name}-db-init-prefect"
  cpu                      = "256"
  memory                   = "512"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([
    {
      name  = "db-init-prefect"
      image = "postgres:14"
      command = ["/bin/sh", "-lc", "psql postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/postgres -v ON_ERROR_STOP=1 -c 'CREATE DATABASE prefect;' || true"]
      logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.prefect.name, awslogs-region = var.region, awslogs-stream-prefix = "ecs" } }
      environment = [
        { name = "DB_HOST", value = var.rds_endpoint },
        { name = "DB_PORT", value = var.rds_port },
      ]
      secrets = [
        { name = "DB_USER", valueFrom = "${var.rds_secret_arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${var.rds_secret_arn}:password::" },
      ]
      essential = true
    }
  ])
}

output "api_alb_dns" { value = aws_lb.api.dns_name }
output "mlflow_alb_dns" { value = aws_lb.mlflow.dns_name }
output "evidently_alb_dns" { value = aws_lb.evidently.dns_name }
output "prefect_alb_dns" { value = aws_lb.prefect.dns_name }
output "cluster_name" { value = aws_ecs_cluster.this.name }
