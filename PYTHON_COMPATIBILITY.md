# Python runtime compatibility

Date: 2026-11-23 (Asia/Tokyo)

## Earlier Python 3.15 probe

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

## Selected runtime

Use Python 3.14 consistently for local CDK, CodeBuild and dbt/Fargate. The container uses python:3.14.10-slim; native dependencies are compiled in a separate builder stage. The dependency lock remains unchanged. Actual Fargate Python/dbt versions are printed and stored as runtime.json.

Python 3.14 verification results are recorded in VALIDATION.md. The table above records the earlier Python 3.15 probe, not the final deployed runtime.

No compatibility metadata overrides or unmerged upstream code are used.

## Python 3.14 pre-deployment checks

- NAB7 project virtual environment: CPython 3.14.10; requirements installation, pip check and both structural tests passed.
- CodeBuild standard:7.0: Python 3.14.10 selected.
- Linux/AMD64 container: Python 3.14.10, dbt-core 1.12.6, dbt-athena 1.11.1.
- Docker image build, native wheel build, pip check and dbt parse passed with the existing requirements.lock.
- Compatibility build: PipelineAssetsDockerAssetA7-9M9QE44vApbn:b1284d5a-301b-4f9f-b814-0074416a610d (SUCCEEDED).

## Deployment verification

The updated pipeline completed test and prod validation successfully on Python 3.14.10: c3851ba8-10c8-4693-af78-40c5d7f266e0. Both environments passed 3 models, 8 dbt tests and all four independent Athena expected-value checks. See VALIDATION.md for the complete result.

## Sources

- https://www.python.org/downloads/release/python-3152/
- https://docs.aws.amazon.com/codebuild/latest/userguide/available-runtimes.html
- https://pypi.org/project/dbt-core/1.12.6/
- https://pypi.org/project/metricflow/0.213.0/
- https://pypi.org/project/metricflow/0.214.0/
- https://github.com/dbt-labs/metricflow/pull/2153 (open when checked)
