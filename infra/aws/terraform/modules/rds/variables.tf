variable "env_name" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "db_username" { type = string, default = "pgadmin" }
variable "instance_class" { type = string, default = "db.t3.micro" }
variable "multi_az" { type = bool, default = false }
variable "backup_retention_days" { type = number, default = 7 }
variable "tags" { type = map(string), default = {} }
