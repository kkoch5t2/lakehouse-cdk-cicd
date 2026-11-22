# 検証記録（2026-11-22 / Asia/Tokyo）

## 実行結果

| ケース | コミット | 実行ID | 結果 | 全体時間 |
| --- | --- | --- | --- | --- |
| 01-first-run | `8579536c` | `d699c890-7de6-4392-8be6-02e1eab2a452` | Succeeded | 16分47秒 |
| 02-broken-gold | `b4c98c82` | `628184d6-b052-4ec9-920b-c1387e9f362f` | Failed | 12分36秒 |
| 03-fixed-gold | `a6b5c644` | `d96c48de-b02e-421b-b25d-1893e9ec76b7` | Succeeded | 12分27秒 |

初回：test・prodともに3モデル成功、8データテスト成功。Bronze 8行、Silver正常4行・不正3行、Gold 2026-11-01の注文2件・売上3850.00。

故障：sum(amount) + 100をpush。sales_reconcileが不一致2行を検出。Fargate終了コード1 → Step Functions States.TaskFailed → CodeBuild失敗 → CodePipeline Test失敗。Prodのアクションは0件。

本番保護：スタック最終更新時刻・タスク定義・使用イメージURIとダイジェスト・ワークフロー履歴は変化なし。AthenaでGoldの売上3850.00を再確認。

修正：sum(amount)へ復元。WebhookV2で起動し、Test成功・手動承認・Prod成功。両環境の固定期待値照合が成功。

初回・故障・修正の3ケースで最終的に使用したイメージ：`sha256:077c7685cbfa40efee36064ff2911cf73260d612c38c39cc3c6c0a2747bfc855`。testとprodで一致。両環境の実行中Fargateタスクは0。

## Python 3.14への統一と再検証（2026-11-23 / Asia/Tokyo）

操作端末の仮想環境、CodeBuild、dbt用FargateコンテナーをPython 3.14系に統一しました。既存の依存ロックとSQL・テストは変更していません。

| 確認対象 | 結果 |
| --- | --- |
| NAB7のプロジェクト仮想環境 | Python 3.14.10、pip check成功、構成テスト2件成功 |
| CodeBuild | 全5プロジェクトのruntime-versionsを3.14へ更新。更新後のSynthでPython 3.14.10と構成テスト2件の成功を確認 |
| dbtイメージ | python:3.14.10-slim。別ステージでネイティブ依存をビルド。Dockerビルド、pip check、dbt parse成功 |
| test | Python 3.14.10 / dbt-core 1.12.6 / dbt-athena 1.11.1。3モデル・8データテスト成功 |
| prod | Python 3.14.10 / dbt-core 1.12.6 / dbt-athena 1.11.1。3モデル・8データテスト成功 |
| 両環境の期待値照合 | Bronze 8行、Silver正常4行・不正3行、Gold 2026-11-01の注文2件・売上3850.00 |

- 対象コミット: 9b471d6393d74e7e7bcc550b3138932dcdb8aa9f
- 成功したCodePipeline実行: c3851ba8-10c8-4693-af78-40c5d7f266e0
- PR: https://github.com/kkoch5t2/lakehouse-cdk-cicd/pull/1
- 最初の実行6358330d-6dd6-4a6e-8789-9809e0c740aeはSelfMutate成功後にCancelledとなり、更新されたパイプラインが同じコミットで再実行されました。上記は再実行の成功記録です。
- Test成功後に学習用prodへの手動承認を実施し、Prodの検証まで成功しました。
- 実行時のバージョンはCloudWatch LogsのRuntime行と結果バケットのruntime.jsonへ保存。両環境のコンテナー終了コードは0、タスクはSTOPPEDです。
- 以降の料金概算は初回・故障・修正の3ケースのみが対象で、Python更新の追加ビルド・再検証の実行料は含みません。

Python 3.14のtest・prodでイメージダイジェストが一致: sha256:0194934a722c1f961ea9014eb49516f3b715709ba73b17c90310951c45170901.

再検証後の実行中Fargateタスクは両環境とも0です。

## コスト概算

CodeBuild: 0.155 USD / CodePipeline: 0.122 USD / 小計 0.277 USD（41.55円、1 USD=150円、税別、無料枠未控除）。

Fargate、パブリックIPv4、Athena、S3、ECR、CloudWatch Logs、Step Functions、KMSは小計に含まない。請求確定額ではない。

## 証跡と残存リソース

- CodePipelineの実行・アクション履歴、CodeBuildログ、dbt manifest/run_results/dbt.log/exit.json、Athena照合結果をNAB7のevidence/配下へ保存。
- 初期接続Pendingに伴うSource失敗2件はデータ品質故障テストと区別。
- 図・手動承認待ち・初回成功・故障時Test失敗/Prod未実行・故障後の本番売上・修正後成功を撮影。
- このリポジトリには、検証時に使用した修正済みコード（検証当時のコミットa6b5c644）を収録しています。公開前にGit履歴を整理したため、表のコミットIDは現在のリポジトリの履歴とは異なります。
- S3/ECR/KMS/CDKToolkit等は確認用に保持。保存・維持料金は継続。ECSサービス、EC2、NAT Gateway、ALB、スケジュールは未作成。
- 実データ、多重起動制御、増分処理、全モデルの一括ロールバック、Lake Formationによる権限制御は今回の対象外。

## 参照

- https://docs.aws.amazon.com/cdk/v2/guide/cdk-pipeline.html
- https://docs.aws.amazon.com/cdk/v2/guide/use-cfn-template.html
- https://aws.amazon.com/codepipeline/pricing/
- https://aws.amazon.com/codebuild/pricing/
