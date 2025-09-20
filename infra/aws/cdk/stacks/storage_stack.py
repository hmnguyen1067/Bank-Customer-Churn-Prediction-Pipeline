from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from constructs import Construct


class StorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, env_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # KMS key for buckets
        bucket_key = kms.Key(
            self,
            "ArtifactsBucketKey",
            alias=f"alias/{env_name}-artifacts-kms",
            enable_key_rotation=True,
        )

        self.mlflow_bucket = s3.Bucket(
            self,
            "MlflowArtifactsBucket",
            bucket_name=None,  # Let AWS name; set explicitly if required
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=bucket_key,
            versioned=True,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    transitions=[
                        s3.Transition(storage_class=s3.StorageClass.INTELLIGENT_TIERING, transition_after=Duration.days(30)),
                    ],
                )
            ],
        )

        self.evidently_bucket = s3.Bucket(
            self,
            "EvidentlyWorkspaceBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=bucket_key,
            versioned=True,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    transitions=[
                        s3.Transition(storage_class=s3.StorageClass.INTELLIGENT_TIERING, transition_after=Duration.days(30)),
                    ],
                )
            ],
        )

        CfnOutput(self, "MlflowBucketName", value=self.mlflow_bucket.bucket_name)
        CfnOutput(self, "EvidentlyBucketName", value=self.evidently_bucket.bucket_name)
