import os
import aws_cdk as cdk
from lakehouse.pipeline import LakehousePipeline

required = ["PIPELINE_ACCOUNT", "TEST_ACCOUNT", "PROD_ACCOUNT", "GITHUB_REPOSITORY", "CONNECTION_ARN"]
config = {key: os.environ[key] for key in required}
config["AWS_REGION"] = os.environ.get("AWS_REGION", "ap-southeast-2")
app = cdk.App()
LakehousePipeline(app, "LakehousePipeline", config=config,
    env=cdk.Environment(account=config["PIPELINE_ACCOUNT"], region=config["AWS_REGION"]))
cdk.Tags.of(app).add("Project", "lakehouse-cdk-cicd")
app.synth()
