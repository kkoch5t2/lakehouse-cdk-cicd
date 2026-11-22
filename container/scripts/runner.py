import os,sys,subprocess,uuid,json,platform
from importlib.metadata import version
from pathlib import Path
from datetime import datetime,timezone
import boto3
run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
runtime = {
    "python": platform.python_version(),
    "implementation": platform.python_implementation(),
    "dbt_core": version("dbt-core"),
    "dbt_athena": version("dbt-athena"),
}
print("Runtime: " + json.dumps(runtime), flush=True)
code=1
try:
    p=subprocess.run(['dbt','build','--target','lab','--no-use-colors'],timeout=1500)
    code=p.returncode
except Exception as e:
    print(str(e),flush=True)
finally:
    prefix='medallion-lab/artifacts/'+run+'/'
    try:
        s3=boto3.client('s3')
        for folder in ['target','logs']:
            for path in Path(folder).glob('*'):
                if path.is_file(): s3.upload_file(str(path),os.environ['RESULTS_BUCKET'],prefix+str(path))
        s3.put_object(Bucket=os.environ['RESULTS_BUCKET'],Key=prefix+'exit.json',Body=json.dumps({'exit_code':code}).encode())
        s3.put_object(Bucket=os.environ['RESULTS_BUCKET'],Key=prefix+'runtime.json',Body=json.dumps(runtime).encode())
        print('Artifacts: s3://'+os.environ['RESULTS_BUCKET']+'/'+prefix,flush=True)
    except Exception as e:
        print('Artifact upload failed: '+str(e),flush=True); code=code or 2
sys.exit(code)
