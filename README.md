# CDK PipelinesでデータレイクハウスのCI/CDを検証する

前回の [medallion-fargate-lab](https://github.com/kkoch5t2/medallion-fargate-lab) のSQL・dbtテスト・Fargate用テンプレートを再利用する学習用プロジェクトです。

## 構成と流れ

3つのAWSアカウントを使います。同じOrganizations組織内の `cicd`、`test`、`prod` を想定します。AWS Settingsのプロジェクトを使う場合は、それぞれに含まれるAWSアカウントを指定します。

ここでのprodは学習のための「本番を模した環境」です。test・prodともに架空の注文CSVを使います。

1. GitHubのmainへのpushをCodeConnectionsで受け取る。
2. CodeBuildでCDKの静的テストを行い、CloudFormationテンプレートを合成する。
3. CDK Pipelinesが必要に応じて自分自身を更新する。
4. CodeBuildでdbtイメージをビルドし、各環境のCDK bootstrap ECRに発行する。
5. testにCloudFormationでデプロイする。
6. 検証用CSVをS3へ置き、Step FunctionsからFargateの単発タスクで `dbt build` を実行する。
7. Athenaで期待値を照合する。成功後、手動承認を待つ。
8. 承認後に同じソースリビジョンをprodへデプロイし、同じ検査を実行する。

各環境のデータ処理は `S3 Bronze CSV → Athena/dbt → Silver・Gold Iceberg` です。Glue Data Catalogをメタデータ管理に使います。Glue ETLジョブは使いません。

## 初期設定

Python 3.12、Node.js、AWS CLI、CDK CLIを用意します。Dockerを手元へインストールする必要はありません。コード中ではCDK CLI 2.1149.0とaws-cdk-lib 2.278.0を使用します。

```powershell
# Python環境を作り、CDKと操作用ライブラリを導入する
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm install -g aws-cdk@2.1149.0

# 各アカウントの既存ログインを使ってCLI認証を行う
aws login --profile lakehouse-cicd --region ap-southeast-2
aws login --profile lakehouse-test --region ap-southeast-2
aws login --profile lakehouse-prod --region ap-southeast-2
```

`config.example.txt` の値を環境変数に設定します。AWSの認証情報をファイルやGitへ書き込まないでください。アカウントID・接続ARN自体は認証情報ではありません。

```powershell
$env:PIPELINE_ACCOUNT = '111111111111'
$env:TEST_ACCOUNT = '222222222222'
$env:PROD_ACCOUNT = '333333333333'
$env:AWS_REGION = 'ap-southeast-2'
$env:GITHUB_REPOSITORY = 'YOUR_OWNER/lakehouse-cdk-cicd-public'
$env:CONNECTION_ARN = 'YOUR_CODECONNECTIONS_ARN'

# CI/CDアカウントと、CI/CDからのデプロイを信頼する2環境を初期化する
cdk bootstrap "aws://$env:PIPELINE_ACCOUNT/$env:AWS_REGION" --profile lakehouse-cicd --termination-protection
cdk bootstrap "aws://$env:TEST_ACCOUNT/$env:AWS_REGION" --profile lakehouse-test --trust $env:PIPELINE_ACCOUNT --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess --termination-protection
cdk bootstrap "aws://$env:PROD_ACCOUNT/$env:AWS_REGION" --profile lakehouse-prod --trust $env:PIPELINE_ACCOUNT --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess --termination-protection

# AWSコンソールでCodeConnectionsとGitHubアプリを接続し、対象リポジトリに限定する
# 作成済みの接続ARNをCONNECTION_ARNへ設定し、AVAILABLEを確認する
aws codeconnections get-connection --connection-arn $env:CONNECTION_ARN --profile lakehouse-cicd --region $env:AWS_REGION

# 構成を検査して、最初のパイプラインだけ手元から作成する
python -m unittest discover -s tests -v
cdk synth
cdk deploy LakehousePipeline --profile lakehouse-cicd
```

bootstrapのCloudFormation実行ロールには、この検証ではAdministratorAccessを指定します。本番運用への流用時は、実際のデプロイ対象に合わせたポリシーへ制限してください。CI/CDアカウントへのコード変更権限は各環境のデプロイ権限につながります。

## 検証項目と証跡

| 検査 | 期待値 |
| --- | --- |
| Bronze | 8行 |
| Silver orders_clean | 4行 |
| Silver orders_rejected | 3行 |
| Gold daily_sales | 2026-11-01、注文2件、売上3850.00 |
| 不正なdbtモデルをpush | Testの検証に失敗し、Prodへ進まない |
| 修正をpush | Test成功・手動承認・Prod成功 |

`scripts/verify_environment.py` はdbtの終了だけでなく、上記の固定期待値をAthenaで確認します。dbtのmanifest、run_results、ログ、exit.jsonはResultsバケットの `medallion-lab/artifacts/` へ保存されます。ワークフローと期待値照合の結果は `medallion-lab/cicd/` とCodeBuildの出力アーティファクトに保存します。

失敗テストの例は、`container/dbt/models/gold/daily_sales.sql` の `sum(amount)` を `sum(amount) + 100` に変更してpushする方法です。`sales_reconcile` が不一致を検出します。Prodの最終更新時刻・稼働イメージ・直前の成功実行を控え、失敗後も変化しないことを確認してから元に戻します。

記事では、CodePipeline全体、Testの失敗理由、手動承認、Prod成功、Athenaの実行結果を撮影します。個人情報や認証情報を画像に含めないでください。実施結果は `VALIDATION.md` に記録します。

## コストと片付け

常時稼働するECSサービス・EC2・NAT Gateway・ロードバランサー・定期実行は作りません。FargateはLinux/AMD64、0.5 vCPU・1 GiBの単発実行です。送信先へHTTPS通信するため、実行中だけパブリックIPv4を使います。Security Groupの受信許可はありません。

CodeBuild・CodePipeline V2・Fargate・Athenaの実行と、S3・ECR・CloudWatch Logs・クロスアカウントアーティファクト暗号化用KMSキーに課金されます。手動承認の待ち時間ではCodeBuildを動かしません。無料枠は前提にしません。

証跡を保存した後に片付けます。まずパイプラインの実行が停止し、Fargateタスクが0であることを確認します。prod/testのワークロードスタックを各アカウントで削除し、CI/CDのパイプラインスタックを削除します。データ・結果バケットは意図的にRetainとしているため、スタック削除後も残ります。削除前に必要な結果を退避し、対象バケット名を確認してください。

CDKToolkitも別スタックです。他プロジェクトと共用する場合は削除しません。専用の場合も、ECRイメージ・bootstrapのS3・バージョン付きアーティファクト・ログ・KMSキー・CodeConnectionsが残っていないか確認します。CDKToolkitの削除には終了保護の解除が必要です。

## 参考にしたAWS公式資料

- [CDK Pipelines](https://docs.aws.amazon.com/cdk/v2/guide/cdk-pipeline.html)
- [既存CloudFormationテンプレートの利用](https://docs.aws.amazon.com/cdk/v2/guide/use-cfn-template.html)
- [CDK bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)
- [Deploy data lake ETL jobs using CDK Pipelines](https://aws.amazon.com/blogs/devops/deploying-data-lake-etl-jobs-using-cdk-pipelines/)

公式のCDK Pipelines設計を参考に、以前のdbt・Fargate構成を接続した検証案です。AWSブログのGlue ETLサンプルそのものとは構成が異なります。
