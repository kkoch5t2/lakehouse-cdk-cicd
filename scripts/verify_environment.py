import platform
"""Run the deployed workflow and assert independent expected data. Fails the pipeline on any mismatch."""
import json
import os
import time
import uuid
from pathlib import Path
import boto3

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)

def wait_for(poll, success, failed, timeout=720):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        result = poll()
        status = success(result)
        if status: return result
        error = failed(result)
        if error: raise RuntimeError(json.dumps(result,default=str))
        time.sleep(5)
    raise TimeoutError("Verification exceeded timeout")

def main():
    print("Verification runtime: Python " + platform.python_version(), flush=True)
    region=os.environ["AWS_REGION"]
    credentials=boto3.client("sts",region_name=region).assume_role(
        RoleArn=os.environ["VALIDATION_ROLE"],RoleSessionName="lakehouse-verification")["Credentials"]
    session=boto3.Session(region_name=region,aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],aws_session_token=credentials["SessionToken"])
    s3=session.client("s3"); sf=session.client("stepfunctions"); athena=session.client("athena")
    data=os.environ["DATA_BUCKET"]; results=os.environ["RESULTS_BUCKET"]
    # Dedicated fixture prefix owned by this lab, not production business data.
    s3.upload_file(str(ROOT/"samples/orders-001.csv"),data,"medallion-lab/bronze/orders/orders-001.csv")
    execution=sf.start_execution(stateMachineArn=os.environ["WORKFLOW_ARN"],name="verify-"+uuid.uuid4().hex,
        input=json.dumps({"force_fail":"0"}))["executionArn"]
    print("Execution:",execution,flush=True)
    try:
        outcome=wait_for(lambda:sf.describe_execution(executionArn=execution),
            lambda x:x["status"]=="SUCCEEDED",lambda x:x["status"] not in ["RUNNING","SUCCEEDED"])
    except TimeoutError:
        sf.stop_execution(executionArn=execution,error="VerificationTimeout")
        raise
    finally:
        outcome=sf.describe_execution(executionArn=execution)
        (EVIDENCE/"workflow.json").write_text(json.dumps(outcome,default=str,indent=2))
        s3.put_object(Bucket=results,Key="medallion-lab/cicd/"+execution.rsplit(":",1)[1]+"/workflow.json",
            Body=json.dumps(outcome,default=str).encode())
    queries={
        "bronze":("select count(*) from medallion_lab_bronze.orders_raw",[["8"]]),
        "clean":("select count(*) from medallion_lab_silver.orders_clean",[["4"]]),
        "rejected":("select count(*) from medallion_lab_silver.orders_rejected",[["3"]]),
        "gold":("select cast(order_date as varchar), cast(order_count as varchar), cast(sales_amount as decimal(18,2)) from medallion_lab_gold.daily_sales order by order_date",[["2026-11-01","2","3850.00"]]),
    }
    report={"execution":execution,"source_revision":os.environ.get("CODEBUILD_RESOLVED_SOURCE_VERSION"),"checks":{}}
    for name,(sql,expected) in queries.items():
        qid=athena.start_query_execution(QueryString=sql,WorkGroup=os.environ["ATHENA_WORKGROUP"])["QueryExecutionId"]
        try:
            result=wait_for(lambda:athena.get_query_execution(QueryExecutionId=qid),
                lambda x:x["QueryExecution"]["Status"]["State"]=="SUCCEEDED",
                lambda x:x["QueryExecution"]["Status"]["State"] in ["FAILED","CANCELLED"],timeout=120)
        except TimeoutError:
            athena.stop_query_execution(QueryExecutionId=qid)
            raise
        rows=athena.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"][1:]
        actual=[[column.get("VarCharValue") for column in row["Data"]] for row in rows]
        report["checks"][name]={"query_id":qid,"expected":expected,"actual":actual,
            "bytes_scanned":result["QueryExecution"]["Statistics"].get("DataScannedInBytes",0)}
        (EVIDENCE/"verification.json").write_text(json.dumps(report,indent=2))
        if actual!=expected: raise AssertionError(f"{name}: expected {expected}, got {actual}")
    payload=json.dumps(report,indent=2)
    s3.put_object(Bucket=results,Key="medallion-lab/cicd/"+execution.rsplit(":",1)[1]+"/verification.json",Body=payload.encode())
    print(payload,flush=True)

if __name__=="__main__":main()
