variable "env_name" {
  description = "Environment name (dev/stage/prod)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

variable "api_domain" {
  description = "Optional FQDN for API ALB HTTPS (e.g., api.dev.example.com)"
  type        = string
  default     = null
}

variable "hosted_zone_id" {
  description = "Optional Route53 hosted zone ID for ACM DNS validation"
  type        = string
  default     = null
}

variable "hosted_zone_name" {
  description = "Optional Route53 hosted zone name"
  type        = string
  default     = null
}
