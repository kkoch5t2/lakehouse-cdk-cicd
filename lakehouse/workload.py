from pathlib import Path
from constructs import Construct
from aws_cdk import Stack, Stage, CfnOutput, Duration, RemovalPolicy, ArnFormat
from aws_cdk import aws_s3 as s3, aws_iam as iam, aws_ecr_assets as assets
from aws_cdk import cloudformation_include as include

ROOT = Path(__file__).resolve().parents[1]

class Workload(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, pipeline_account: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        # Independent buckets per environment. Keep data and evidence on stack deletion.
        bucket_args = dict(encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True, removal_policy=RemovalPolicy.RETAIN)
        data = s3.Bucket(self, "Data", **bucket_args)
        results = s3.Bucket(self, "Results", lifecycle_rules=[
            s3.LifecycleRule(prefix="medallion-lab/query-results/", expiration=Duration.days(7)),
        ], **bucket_args)
        image = assets.DockerImageAsset(self, "DbtImage", directory=str(ROOT / "container"),
            platform=assets.Platform.LINUX_AMD64)
        imported = include.CfnInclude(self, "Lakehouse", template_file=str(ROOT / "infra/workload.json"),
            parameters={"DataBucket": data.bucket_name, "ResultsBucket": results.bucket_name,
                "ImageUri": image.image_uri}, preserve_logical_ids=True)
        workflow = imported.get_resource("Workflow")
        workgroup = imported.get_resource("Workgroup")
        # Only the pipeline's verification CodeBuild roles can assume this role.
        validation = iam.Role(self, "ValidationRole", role_name=f"{self.stack_name}-verification", assumed_by=iam.AccountPrincipal(pipeline_account),
            max_session_duration=Duration.hours(1))
        validation.add_to_policy(iam.PolicyStatement(actions=["states:StartExecution"], resources=[workflow.ref]))
        validation.add_to_policy(iam.PolicyStatement(actions=["states:DescribeExecution", "states:StopExecution"],
            resources=[self.format_arn(service="states", resource="execution", resource_name="*:*", arn_format=ArnFormat.COLON_RESOURCE_NAME)]))
        data.grant_read_write(validation, "medallion-lab/*")
        results.grant_read_write(validation, "medallion-lab/*")
        validation.add_to_policy(iam.PolicyStatement(actions=["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults", "athena:StopQueryExecution"],
            resources=[self.format_arn(service="athena",resource="workgroup",resource_name=workgroup.ref)]))
        validation.add_to_policy(iam.PolicyStatement(actions=["glue:GetDatabase", "glue:GetTable", "glue:GetPartitions"], resources=[
            self.format_arn(service="glue",resource="catalog"),
            self.format_arn(service="glue",resource="database",resource_name="medallion_lab*"),
            self.format_arn(service="glue",resource="table",resource_name="medallion_lab*/*")]))
        self.verification_outputs = {
            "VALIDATION_ROLE": CfnOutput(self,"ValidationRoleArn",value=validation.role_arn),
            "DATA_BUCKET": CfnOutput(self,"DataBucketName",value=data.bucket_name),
            "RESULTS_BUCKET": CfnOutput(self,"ResultsBucketName",value=results.bucket_name),
            "WORKFLOW_ARN": CfnOutput(self,"WorkflowOutput",value=workflow.ref),
            "ATHENA_WORKGROUP": CfnOutput(self,"WorkgroupOutput",value=workgroup.ref),
        }

class WorkloadStage(Stage):
    def __init__(self, scope: Construct, construct_id: str, *, pipeline_account: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        self.workload = Workload(self,"Lakehouse",pipeline_account=pipeline_account,
            stack_name=f"lakehouse-{construct_id.lower()}")
