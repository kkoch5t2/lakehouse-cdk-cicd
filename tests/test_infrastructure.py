import json
import unittest
import tempfile
from pathlib import Path
import aws_cdk as cdk
from lakehouse.pipeline import LakehousePipeline

class InfrastructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        config={"PIPELINE_ACCOUNT":"111111111111","TEST_ACCOUNT":"222222222222",
            "PROD_ACCOUNT":"333333333333","AWS_REGION":"ap-southeast-2",
            "GITHUB_REPOSITORY":"example/lakehouse-cdk-cicd",
            "CONNECTION_ARN":"arn:aws:codeconnections:ap-southeast-2:111111111111:connection/00000000-0000-0000-0000-000000000000"}
        app=cdk.App(outdir=cls.temp.name)
        LakehousePipeline(app,"LakehousePipeline",config=config,
            env=cdk.Environment(account=config["PIPELINE_ACCOUNT"],region=config["AWS_REGION"]))
        app.synth()
        cls.templates={str(p.relative_to(cls.temp.name)):json.loads(p.read_text())
            for p in Path(cls.temp.name).rglob("*.template.json")}

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_test_gate_and_manual_approval_precede_production_deploy(self):
        pipeline=next(x for x in self.templates["LakehousePipeline.template.json"]["Resources"].values()
            if x["Type"]=="AWS::CodePipeline::Pipeline")["Properties"]
        self.assertEqual(pipeline["PipelineType"],"V2")
        stages=pipeline["Stages"]
        names=[s["Name"] for s in stages]
        self.assertLess(names.index("Test"),names.index("Prod"))
        test=next(s for s in stages if s["Name"]=="Test")["Actions"]
        self.assertEqual(test[-1]["Name"],"VerifyTest")
        prod=next(s for s in stages if s["Name"]=="Prod")["Actions"]
        approval=next(a for a in prod if a["ActionTypeId"]["Category"]=="Approval")
        self.assertTrue(all(approval["RunOrder"]<a["RunOrder"] for a in prod
            if a["ActionTypeId"]["Category"]=="Deploy"))

    def test_no_always_running_compute_or_public_bucket(self):
        workloads=[t for name,t in self.templates.items() if name.startswith("assembly-")]
        self.assertEqual(len(workloads),2)
        for template in workloads:
            resources=template["Resources"]
            kinds=[v["Type"] for v in resources.values()]
            for forbidden in ["AWS::EC2::NatGateway","AWS::EC2::Instance","AWS::ECS::Service"]:
                self.assertNotIn(forbidden,kinds)
            for resource in resources.values():
                if resource["Type"]=="AWS::S3::Bucket":
                    self.assertTrue(all(resource["Properties"]["PublicAccessBlockConfiguration"].values()))
            self.assertNotIn("SecurityGroupIngress",resources["SecurityGroup"]["Properties"])
            self.assertEqual(resources["Task"]["Properties"]["Cpu"],"512")
            self.assertEqual(resources["Task"]["Properties"]["Memory"],"1024")
            check=resources["Workflow"]["Properties"]["Definition"]["States"]["CheckExit"]
            self.assertEqual(check["Default"],"DbtFailed")

if __name__=="__main__":unittest.main()
