resource "random_password" "db" {
  length  = 20
  special = true
}

resource "aws_security_group" "db" {
  name        = "${var.env_name}-rds-sg"
  description = "RDS SG"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "${var.env_name}-rds-sg" })
}

resource "aws_db_subnet_group" "db" {
  name       = "${var.env_name}-db-subnets"
  subnet_ids = var.private_subnet_ids
  tags       = merge(var.tags, { Name = "${var.env_name}-db-subnets" })
}

resource "aws_db_instance" "postgres" {
  identifier              = "${var.env_name}-postgres"
  engine                  = "postgres"
  engine_version          = "14"
  instance_class          = var.instance_class
  username                = var.db_username
  password                = random_password.db.result
  allocated_storage       = 20
  max_allocated_storage   = 100
  storage_encrypted       = true
  backup_retention_period = var.backup_retention_days
  multi_az                = var.multi_az
  db_subnet_group_name    = aws_db_subnet_group.db.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  publicly_accessible     = false
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true
  # parameter_group_name  = "default.postgres14"
  tags = merge(var.tags, { Name = "${var.env_name}-postgres" })
}

resource "aws_secretsmanager_secret" "db" {
  name = "${var.env_name}-rds-admin"
  tags = merge(var.tags, { Name = "${var.env_name}-rds-admin" })
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id     = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db.result
    host     = aws_db_instance.postgres.address
    port     = aws_db_instance.postgres.port
  })
}

output "endpoint" { value = aws_db_instance.postgres.address }
output "port" { value = aws_db_instance.postgres.port }
output "security_group_id" { value = aws_security_group.db.id }
output "secret_arn" { value = aws_secretsmanager_secret.db.arn }
