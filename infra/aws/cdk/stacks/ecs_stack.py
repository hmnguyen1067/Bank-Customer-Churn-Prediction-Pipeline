from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct


class EcsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_name: str,
        vpc: ec2.IVpc,
        rds_instance=None,
        mlflow_bucket=None,
        evidently_bucket=None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECS Cluster
        self.cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights=True)

        # Security group for ECS services
        self.services_sg = ec2.SecurityGroup(self, "ServicesSg", vpc=vpc, allow_all_outbound=True)

        # CloudWatch log groups (placeholders for services)
        self.api_logs = logs.LogGroup(self, "ApiLogs", log_group_name=f"/ecs/{env_name}/api", retention=logs.RetentionDays.THREE_MONTHS)
        self.mlflow_logs = logs.LogGroup(self, "MlflowLogs", log_group_name=f"/ecs/{env_name}/mlflow", retention=logs.RetentionDays.THREE_MONTHS)
        self.evidently_logs = logs.LogGroup(self, "EvidentlyLogs", log_group_name=f"/ecs/{env_name}/evidently", retention=logs.RetentionDays.THREE_MONTHS)
        self.prefect_logs = logs.LogGroup(self, "PrefectLogs", log_group_name=f"/ecs/{env_name}/prefect", retention=logs.RetentionDays.THREE_MONTHS)

        # Public ALB for API
        self.api_alb = elbv2.ApplicationLoadBalancer(
            self, "ApiAlb", vpc=vpc, internet_facing=True, load_balancer_name=f"{env_name}-api-alb"
        )
        # Try to enable HTTPS if context provides domain + hosted zone
        domain = self.node.try_get_context("apiDomain")
        hosted_zone_name = self.node.try_get_context("hostedZoneName")
        hosted_zone_id = self.node.try_get_context("hostedZoneId")

        self.api_http_listener = self.api_alb.add_listener("Http", port=80, open=True)
        self.api_https_listener = None
        if domain and hosted_zone_name and hosted_zone_id:
            zone = route53.HostedZone.from_hosted_zone_attributes(
                self, "ApiHz", hosted_zone_id=hosted_zone_id, zone_name=hosted_zone_name
            )
            cert = acm.DnsValidatedCertificate(self, "ApiCert", domain_name=domain, hosted_zone=zone)
            self.api_https_listener = self.api_alb.add_listener(
                "Https",
                port=443,
                certificates=[elbv2.ListenerCertificate(cert.certificate_arn)],
                default_action=elbv2.ListenerAction.fixed_response(status_code="200", message_body="API ALB ready"),
            )
            # Redirect HTTP to HTTPS
            self.api_http_listener.add_action(
                "RedirectToHttps",
                action=elbv2.ListenerAction.redirect(protocol="HTTPS", port="443", permanent=True),
            )

        # Internal ALB for MLflow
        self.mlflow_alb = elbv2.ApplicationLoadBalancer(
            self, "MlflowAlb", vpc=vpc, internet_facing=False, load_balancer_name=f"{env_name}-mlflow-alb"
        )
        self.mlflow_http_listener = self.mlflow_alb.add_listener(
            "Http", port=80, default_action=elbv2.ListenerAction.fixed_response(status_code="200", message_body="MLflow ALB ready")
        )

        # Internal ALB for Evidently (optional/private)
        self.evidently_alb = elbv2.ApplicationLoadBalancer(
            self, "EvidentlyAlb", vpc=vpc, internet_facing=False, load_balancer_name=f"{env_name}-evidently-alb"
        )
        self.evidently_http_listener = self.evidently_alb.add_listener(
            "Http", port=80, default_action=elbv2.ListenerAction.fixed_response(status_code="200", message_body="Evidently ALB ready")
        )

        # Internal ALB for Prefect server
        self.prefect_alb = elbv2.ApplicationLoadBalancer(
            self, "PrefectAlb", vpc=vpc, internet_facing=False, load_balancer_name=f"{env_name}-prefect-alb"
        )
        self.prefect_http_listener = self.prefect_alb.add_listener(
            "Http", port=80, default_action=elbv2.ListenerAction.fixed_response(status_code="200", message_body="Prefect ALB ready")
        )

        # WAF for API ALB (basic managed ruleset)
        web_acl = wafv2.CfnWebACL(
            self,
            "ApiWaf",
            name=f"{env_name}-api-waf",
            scope="REGIONAL",
            default_action={"allow": {}},
            visibility_config={
                "cloudWatchMetricsEnabled": True,
                "metricName": f"{env_name}-api-waf",
                "sampledRequestsEnabled": True,
            },
            rules=[
                {
                    "name": "AWSManagedRulesCommonRuleSet",
                    "priority": 0,
                    "overrideAction": {"none": {}},
                    "visibilityConfig": {
                        "sampledRequestsEnabled": True,
                        "cloudWatchMetricsEnabled": True,
                        "metricName": "AWSManagedRulesCommonRuleSet",
                    },
                    "statement": {
                        "managedRuleGroupStatement": {
                            "vendorName": "AWS",
                            "name": "AWSManagedRulesCommonRuleSet",
                        }
                    },
                }
            ],
        )
        wafv2.CfnWebACLAssociation(self, "ApiWafAssoc", resource_arn=self.api_alb.load_balancer_arn, web_acl_arn=web_acl.attr_arn)

        # ECR repositories for service images
        self.repo_api = ecr.Repository(self, "ApiRepo", repository_name=f"{env_name}-api")
        self.repo_mlflow = ecr.Repository(self, "MlflowRepo", repository_name=f"{env_name}-mlflow")
        self.repo_evidently = ecr.Repository(self, "EvidentlyRepo", repository_name=f"{env_name}-evidently")

        # ========== MLflow Service ==========
        mlflow_task = ecs.FargateTaskDefinition(
            self,
            "MlflowTask",
            cpu=512,
            memory_limit_mib=1024,
        )
        mlflow_container = mlflow_task.add_container(
            "mlflow",
            image=ecs.ContainerImage.from_ecr_repository(self.repo_mlflow, tag="latest"),
            logging=ecs.LogDriver.aws_logs(stream_prefix="mlflow", log_group=self.mlflow_logs),
            environment={
                # Artifacts destination handled by command arg; not using MinIO flags
            },
        )
        mlflow_container.add_port_mappings(ecs.PortMapping(container_port=5000))
        # Command builds backend-store-uri from env/secrets
        mlflow_container.command = [
            "sh",
            "-lc",
            'mlflow server --backend-store-uri "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}" '
            "--host 0.0.0.0 --serve-artifacts --artifacts-destination s3://" + (mlflow_bucket.bucket_name if mlflow_bucket else "mlflow-bucket")
        ]
        if rds_instance and rds_instance.secret is not None:
            # Map RDS secret fields to env for building URI
            mlflow_container.add_secrets(
                {
                    "DB_USER": ecs.Secret.from_secrets_manager(rds_instance.secret, field="username"),
                    "DB_PASSWORD": ecs.Secret.from_secrets_manager(rds_instance.secret, field="password"),
                }
            )
            mlflow_container.add_environment("DB_HOST", rds_instance.db_instance_endpoint_address)
            mlflow_container.add_environment("DB_PORT", rds_instance.db_instance_endpoint_port)
            mlflow_container.add_environment("DB_NAME", "mlflow")  # TODO: ensure DB exists
        if mlflow_bucket is not None:
            mlflow_bucket.grant_read_write(mlflow_task.task_role)
        if rds_instance and rds_instance.secret is not None:
            rds_instance.secret.grant_read(mlflow_task.task_role)

        mlflow_service = ecs.FargateService(
            self,
            "MlflowService",
            cluster=self.cluster,
            task_definition=mlflow_task,
            desired_count=1,
            assign_public_ip=False,
            security_groups=[self.services_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )
        # Allow ECS tasks to reach RDS
        if rds_instance is not None:
            rds_instance.connections.allow_from(self.services_sg, ec2.Port.tcp(5432), "ECS services to RDS")

        # Attach MLflow service to internal ALB
        self.mlflow_http_listener.add_targets(
            "MlflowTg",
            port=80,
            targets=[
                mlflow_service.load_balancer_target(
                    container_name="mlflow",
                    container_port=5000,
                )
            ],
            health_check=elbv2.HealthCheck(path="/", interval=Duration.seconds(30)),
        )

        # ========== API Service ==========
        api_task = ecs.FargateTaskDefinition(self, "ApiTask", cpu=512, memory_limit_mib=1024)
        api_container = api_task.add_container(
            "api",
            image=ecs.ContainerImage.from_ecr_repository(self.repo_api, tag="latest"),
            logging=ecs.LogDriver.aws_logs(stream_prefix="api", log_group=self.api_logs),
            environment={
                # Point API to MLflow through internal ALB (HTTP port 80)
                "MLFLOW_TRACKING_URI": f"http://{self.mlflow_alb.load_balancer_dns_name}",
            },
        )
        api_container.add_port_mappings(ecs.PortMapping(container_port=8001))

        api_service = ecs.FargateService(
            self,
            "ApiService",
            cluster=self.cluster,
            task_definition=api_task,
            desired_count=1,
            assign_public_ip=False,
            security_groups=[self.services_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )
        listener_for_api = self.api_https_listener or self.api_http_listener
        listener_for_api.add_targets(
            "ApiTg",
            port=80,
            targets=[
                api_service.load_balancer_target(container_name="api", container_port=8001),
            ],
            health_check=elbv2.HealthCheck(path="/", interval=Duration.seconds(30)),
        )

        # ========== Evidently Service ==========
        evidently_task = ecs.FargateTaskDefinition(self, "EvidentlyTask", cpu=512, memory_limit_mib=1024)
        evidently_container = evidently_task.add_container(
            "evidently",
            image=ecs.ContainerImage.from_ecr_repository(self.repo_evidently, tag="latest"),
            logging=ecs.LogDriver.aws_logs(stream_prefix="evidently", log_group=self.evidently_logs),
            command=["--workspace", f"s3://{evidently_bucket.bucket_name if evidently_bucket else 'evidently-bucket'}/workspace"],
        )
        evidently_container.add_port_mappings(ecs.PortMapping(container_port=8000))
        if evidently_bucket is not None:
            evidently_bucket.grant_read_write(evidently_task.task_role)

        evidently_service = ecs.FargateService(
            self,
            "EvidentlyService",
            cluster=self.cluster,
            task_definition=evidently_task,
            desired_count=1,
            assign_public_ip=False,
            security_groups=[self.services_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )
        self.evidently_http_listener.add_targets(
            "EvidentlyTg",
            port=80,
            targets=[
                evidently_service.load_balancer_target(container_name="evidently", container_port=8000),
            ],
            health_check=elbv2.HealthCheck(path="/", interval=Duration.seconds(30)),
        )

        # ========== Prefect Server ==========
        prefect_srv_task = ecs.FargateTaskDefinition(self, "PrefectServerTask", cpu=512, memory_limit_mib=1024)
        prefect_srv_container = prefect_srv_task.add_container(
            "prefect-server",
            image=ecs.ContainerImage.from_registry("prefecthq/prefect:3-latest"),
            logging=ecs.LogDriver.aws_logs(stream_prefix="prefect-server", log_group=self.prefect_logs),
            environment={
                "PREFECT_SERVER_API_HOST": "0.0.0.0",
                # UI and API URLs will use the ALB DNS at runtime; optional to set
            },
            command=["/bin/sh", "-lc", 'prefect server start'],
        )
        prefect_srv_container.add_port_mappings(ecs.PortMapping(container_port=4200))
        # Prefect DB connection: supply via env from RDS secret
        if rds_instance and rds_instance.secret is not None:
            prefect_srv_container.add_secrets(
                {
                    "DB_USER": ecs.Secret.from_secrets_manager(rds_instance.secret, field="username"),
                    "DB_PASSWORD": ecs.Secret.from_secrets_manager(rds_instance.secret, field="password"),
                }
            )
            prefect_srv_container.add_environment("DB_HOST", rds_instance.db_instance_endpoint_address)
            prefect_srv_container.add_environment("DB_PORT", rds_instance.db_instance_endpoint_port)
            prefect_srv_container.add_environment("DB_NAME", "prefect")  # TODO: ensure DB exists
            # Prefect asyncpg syntax
            prefect_srv_container.add_environment(
                "PREFECT_API_DATABASE_CONNECTION_URL",
                "postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}",
            )
            rds_instance.secret.grant_read(prefect_srv_task.task_role)
            rds_instance.connections.allow_from(self.services_sg, ec2.Port.tcp(5432), "Prefect server to RDS")

        prefect_srv = ecs.FargateService(
            self,
            "PrefectServerService",
            cluster=self.cluster,
            task_definition=prefect_srv_task,
            desired_count=1,
            assign_public_ip=False,
            security_groups=[self.services_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )
        self.prefect_http_listener.add_targets(
            "PrefectTg",
            port=80,
            targets=[prefect_srv.load_balancer_target(container_name="prefect-server", container_port=4200)],
            health_check=elbv2.HealthCheck(path="/api/health", interval=Duration.seconds(30)),
        )

        # ========== Prefect Worker ==========
        prefect_worker_task = ecs.FargateTaskDefinition(self, "PrefectWorkerTask", cpu=512, memory_limit_mib=1024)
        prefect_worker_container = prefect_worker_task.add_container( # noqa
            "prefect-worker",
            image=ecs.ContainerImage.from_registry("prefecthq/prefect:3-latest"),
            logging=ecs.LogDriver.aws_logs(stream_prefix="prefect-worker", log_group=self.prefect_logs),
            environment={
                # Connect worker to Prefect server via internal ALB
                "PREFECT_API_URL": f"http://{self.prefect_alb.load_balancer_dns_name}/api",
            },
            command=["/bin/sh", "-lc", 'prefect worker start -p "default" --name worker-' + env_name],
        )

        prefect_worker = ecs.FargateService( # noqa
            self,
            "PrefectWorkerService",
            cluster=self.cluster,
            task_definition=prefect_worker_task,
            desired_count=1,
            assign_public_ip=False,
            security_groups=[self.services_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        # ========== DB Init Tasks (one-off) ==========
        # These task definitions can be executed manually via aws ecs run-task to create DBs.
        db_init_mlflow = ecs.FargateTaskDefinition(self, "DbInitMlflowTask", cpu=256, memory_limit_mib=512)
        db_init_mlflow_container = db_init_mlflow.add_container(
            "db-init-mlflow",
            image=ecs.ContainerImage.from_registry("postgres:14"),
            logging=ecs.LogDriver.aws_logs(stream_prefix="db-init-mlflow", log_group=self.mlflow_logs),
            command=[
                "/bin/sh",
                "-lc",
                "psql postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/postgres -v ON_ERROR_STOP=1 -c 'CREATE DATABASE mlflow;' || true",
            ],
        )
        if rds_instance and rds_instance.secret is not None:
            db_init_mlflow_container.add_secrets(
                {
                    "DB_USER": ecs.Secret.from_secrets_manager(rds_instance.secret, field="username"),
                    "DB_PASSWORD": ecs.Secret.from_secrets_manager(rds_instance.secret, field="password"),
                }
            )
            db_init_mlflow_container.add_environment("DB_HOST", rds_instance.db_instance_endpoint_address)
            db_init_mlflow_container.add_environment("DB_PORT", rds_instance.db_instance_endpoint_port)
            rds_instance.secret.grant_read(db_init_mlflow.task_role)
            rds_instance.connections.allow_from(self.services_sg, ec2.Port.tcp(5432), "DB init to RDS")

        db_init_prefect = ecs.FargateTaskDefinition(self, "DbInitPrefectTask", cpu=256, memory_limit_mib=512)
        db_init_prefect_container = db_init_prefect.add_container(
            "db-init-prefect",
            image=ecs.ContainerImage.from_registry("postgres:14"),
            logging=ecs.LogDriver.aws_logs(stream_prefix="db-init-prefect", log_group=self.prefect_logs),
            command=[
                "/bin/sh",
                "-lc",
                "psql postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/postgres -v ON_ERROR_STOP=1 -c 'CREATE DATABASE prefect;' || true",
            ],
        )
        if rds_instance and rds_instance.secret is not None:
            db_init_prefect_container.add_secrets(
                {
                    "DB_USER": ecs.Secret.from_secrets_manager(rds_instance.secret, field="username"),
                    "DB_PASSWORD": ecs.Secret.from_secrets_manager(rds_instance.secret, field="password"),
                }
            )
            db_init_prefect_container.add_environment("DB_HOST", rds_instance.db_instance_endpoint_address)
            db_init_prefect_container.add_environment("DB_PORT", rds_instance.db_instance_endpoint_port)
            rds_instance.secret.grant_read(db_init_prefect.task_role)
            rds_instance.connections.allow_from(self.services_sg, ec2.Port.tcp(5432), "DB init to RDS")

        CfnOutput(self, "ApiAlbDns", value=self.api_alb.load_balancer_dns_name)
        CfnOutput(self, "MlflowAlbDns", value=self.mlflow_alb.load_balancer_dns_name)
        CfnOutput(self, "EvidentlyAlbDns", value=self.evidently_alb.load_balancer_dns_name)
        CfnOutput(self, "PrefectAlbDns", value=self.prefect_alb.load_balancer_dns_name)
        CfnOutput(self, "ApiRepoUri", value=self.repo_api.repository_uri)
        CfnOutput(self, "MlflowRepoUri", value=self.repo_mlflow.repository_uri)
        CfnOutput(self, "EvidentlyRepoUri", value=self.repo_evidently.repository_uri)
