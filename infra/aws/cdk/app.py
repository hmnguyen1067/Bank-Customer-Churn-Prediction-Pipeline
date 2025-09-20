#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from stacks.ecs_stack import EcsStack
from stacks.endpoints_stack import EndpointsStack
from stacks.network_stack import NetworkStack
from stacks.rds_stack import RdsStack
from stacks.storage_stack import StorageStack

app = App()

env_name = app.node.try_get_context("envName") or os.getenv("CDK_ENV", "dev")
account = app.node.try_get_context("account") or os.getenv("CDK_ACCOUNT") or "111111111111"
region = app.node.try_get_context("region") or os.getenv("CDK_REGION") or "us-east-1"

env = Environment(account=account, region=region)

network = NetworkStack(
    app,
    f"{env_name}-network",
    env=env,
    description="VPC, subnets, and basic security groups",
    env_name=env_name,
)

storage = StorageStack(
    app,
    f"{env_name}-storage",
    env=env,
    description="S3 buckets for artifacts/workspace",
    env_name=env_name,
)

rds = RdsStack(
    app,
    f"{env_name}-rds",
    env=env,
    description="PostgreSQL DB instance for MLflow/Prefect/Grafana (as needed)",
    env_name=env_name,
    vpc=network.vpc,
)

endpoints = EndpointsStack(
    app,
    f"{env_name}-endpoints",
    env=env,
    description="VPC endpoints for private access to AWS services",
    vpc=network.vpc,
)

ecs = EcsStack(
    app,
    f"{env_name}-ecs",
    env=env,
    description="ECS cluster, ALBs, and Fargate services (api/mlflow/evidently/prefect)",
    env_name=env_name,
    vpc=network.vpc,
    rds_instance=rds.db,
    mlflow_bucket=storage.mlflow_bucket,
    evidently_bucket=storage.evidently_bucket,
)

app.synth()
