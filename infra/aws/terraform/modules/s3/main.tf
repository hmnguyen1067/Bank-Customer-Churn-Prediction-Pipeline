locals {
  mlflow_bucket     = "mlflow-artifacts-${var.env_name}-${random_id.suffix.hex}"
  evidently_bucket  = "evidently-workspace-${var.env_name}-${random_id.suffix.hex}"
}

resource "random_id" "suffix" {
  byte_length = 2
}

resource "aws_s3_bucket" "mlflow" {
  bucket        = local.mlflow_bucket
  force_destroy = false
  tags          = merge(var.tags, { Name = local.mlflow_bucket })
}

resource "aws_s3_bucket_versioning" "mlflow" {
  bucket = aws_s3_bucket.mlflow.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow" {
  bucket = aws_s3_bucket.mlflow.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.artifacts_kms == null ? "AES256" : "aws:kms"
      kms_master_key_id = var.artifacts_kms
    }
  }
}

resource "aws_s3_bucket" "evidently" {
  bucket        = local.evidently_bucket
  force_destroy = false
  tags          = merge(var.tags, { Name = local.evidently_bucket })
}

resource "aws_s3_bucket_versioning" "evidently" {
  bucket = aws_s3_bucket.evidently.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidently" {
  bucket = aws_s3_bucket.evidently.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.artifacts_kms == null ? "AES256" : "aws:kms"
      kms_master_key_id = var.artifacts_kms
    }
  }
}

output "mlflow_bucket" {
  value = aws_s3_bucket.mlflow.bucket
}

output "evidently_bucket" {
  value = aws_s3_bucket.evidently.bucket
}
