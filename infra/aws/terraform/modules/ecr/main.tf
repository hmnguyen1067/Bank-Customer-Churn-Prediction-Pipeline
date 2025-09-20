locals {
  repos = ["api", "mlflow", "evidently"]
}

resource "aws_ecr_repository" "repo" {
  for_each = toset(local.repos)

  name                 = "${var.env_name}-${each.value}"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  force_delete = false

  tags = merge(var.tags, { Name = "${var.env_name}-${each.value}" })
}

output "repository_urls" {
  value = { for k, r in aws_ecr_repository.repo : k => r.repository_url }
}
