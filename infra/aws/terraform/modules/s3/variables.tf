variable "env_name" {
  type = string
}

variable "artifacts_kms" {
  description = "KMS key ARN for S3 encryption (optional)"
  type        = string
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
