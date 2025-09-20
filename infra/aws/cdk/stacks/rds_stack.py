from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from constructs import Construct


class RdsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, env_name: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Security group for RDS
        self.db_sg = ec2.SecurityGroup(
            self, "DbSecurityGroup", vpc=vpc, allow_all_outbound=True, description="RDS SG"
        )

        # Postgres instance (simple single-AZ for dev; switch to Multi-AZ in prod)
        self.db = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.V14),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            multi_az=False if env_name == "dev" else True,
            security_groups=[self.db_sg],
            allocated_storage=20,
            storage_encrypted=True,
            credentials=rds.Credentials.from_generated_secret("pgadmin"),
            delete_automated_backups=True,
            backup_retention=Duration.days(7),
            removal_policy=None,  # TODO: set to RETAIN for prod
        )

        CfnOutput(self, "DbEndpoint", value=self.db.db_instance_endpoint_address)
        CfnOutput(self, "DbSecretArn", value=self.db.secret.secret_arn if self.db.secret else "")
