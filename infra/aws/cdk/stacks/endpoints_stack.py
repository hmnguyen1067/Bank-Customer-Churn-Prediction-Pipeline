from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class EndpointsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Gateway endpoint for S3
        vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            # route tables auto-selected for private subnets by CDK
        )

        # Interface endpoints for common services used by ECS tasks
        # Note: CDK selects all private subnets with default security groups unless overridden
        interface_endpoints = [
            ec2.InterfaceVpcEndpointAwsService.ECR,
            ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            ec2.InterfaceVpcEndpointAwsService.SSM,
        ]

        for idx, svc in enumerate(interface_endpoints):
            vpc.add_interface_endpoint(f"InterfaceEndpoint{idx}", service=svc)
