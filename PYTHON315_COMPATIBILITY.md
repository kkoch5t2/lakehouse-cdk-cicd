# Python 3.15 compatibility investigation

Date: 2026-11-23 (Asia/Tokyo)

## Verified results

| Component | Result |
| --- | --- |
| NAB7 Python | CPython 3.15.2 installed from python.org; official SHA-256 verified |
| CDK dependencies | Existing requirements.txt installed successfully on Python 3.15.2 |
| CDK structural tests | Existing 2 tests passed on Python 3.15.2 |
| CodeBuild runtime | Python 3.15 selected successfully on aws/codebuild/standard:7.0 |
| dbt container on Python 3.15.2 | Dependency resolution failed before dbt execution |
| Blocking dependency | metricflow==0.213.0 declares Python >=3.10,<3.15 |
| Latest MetricFlow checked | 0.214.0 also declares Python >=3.10,<3.15 |

The failed compatibility build did not deploy workloads or run Athena/dbt against the test/prod environments.

## Proposed scope

Use Python 3.15 for local CDK and CodeBuild, while retaining the validated Python 3.12 dbt/Fargate runtime. The dependency lock remains unchanged. The runner records its actual Python/dbt versions as runtime.json so the two runtime scopes can be verified separately.

No compatibility metadata overrides or unmerged upstream code are used.

## Sources

- https://www.python.org/downloads/release/python-3152/
- https://docs.aws.amazon.com/codebuild/latest/userguide/available-runtimes.html
- https://pypi.org/project/dbt-core/1.12.6/
- https://pypi.org/project/metricflow/0.213.0/
- https://pypi.org/project/metricflow/0.214.0/
- https://github.com/dbt-labs/metricflow/pull/2153 (open when checked)
