from constructs import Construct
from aws_cdk import Stack, Environment, Duration
from aws_cdk import pipelines, aws_codebuild as codebuild, aws_codepipeline as codepipeline, aws_iam as iam
from lakehouse.workload import WorkloadStage

class LakehousePipeline(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        source = pipelines.CodePipelineSource.connection(config["GITHUB_REPOSITORY"], "main",
            connection_arn=config["CONNECTION_ARN"], trigger_on_push=True)
        pipeline = pipelines.CodePipeline(self,"Pipeline",pipeline_name="lakehouse-cdk-cicd",
            cli_version="2.1149.0", cdk_assets_cli_version="4.8.1",
            pipeline_type=codepipeline.PipelineType.V2,
            cross_account_keys=True, enable_key_rotation=True,
            docker_enabled_for_synth=False, publish_assets_in_parallel=False,
            synth=pipelines.ShellStep("Synth",input=source,
                install_commands=["python -m pip install -r requirements.txt", "npm install -g aws-cdk@2.1149.0"],
                commands=["python -m unittest discover -s tests -v", "cdk synth"],
                env=config),
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    compute_type=codebuild.ComputeType.SMALL),
                partial_build_spec=codebuild.BuildSpec.from_object({"phases":{"install":{
                    "runtime-versions":{"python":"3.12","nodejs":22}}}}),
                timeout=Duration.minutes(20)),
            self_mutation_code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(environment_variables={
                    key: codebuild.BuildEnvironmentVariable(value=value) for key,value in config.items()})),
        )
        for name, key in [("Test","TEST_ACCOUNT"),("Prod","PROD_ACCOUNT")]:
            stage = WorkloadStage(self,name,pipeline_account=config["PIPELINE_ACCOUNT"],
                env=Environment(account=config[key],region=config["AWS_REGION"]))
            verification = pipelines.CodeBuildStep(f"Verify{name}",input=source,
                install_commands=["python -m pip install boto3"],
                commands=["python scripts/verify_environment.py"],
                env={"AWS_REGION":config["AWS_REGION"]},
                env_from_cfn_outputs=stage.workload.verification_outputs,
                role_policy_statements=[iam.PolicyStatement(actions=["sts:AssumeRole"],resources=[
                    f"arn:aws:iam::{config[key]}:role/lakehouse-{name.lower()}-verification"])],
                timeout=Duration.minutes(15),
                primary_output_directory="evidence")
            pipeline.add_stage(stage,pre=[pipelines.ManualApprovalStep("ApproveProduction")]
                if name=="Prod" else [],post=[verification])
