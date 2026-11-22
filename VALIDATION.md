# 検証記録

実行後の詳細な記録と証跡は、[validation-report-20261122ブランチのVALIDATION.md](https://github.com/kkoch5t2/lakehouse-cdk-cicd/blob/validation-report-20261122/VALIDATION.md)で管理します。

2026-11-22（日本時間）の確認内容：

- 3アカウントのCDK bootstrap、構成テスト2件、CDK synthに成功。
- CodeConnections経由のGitHub接続を完了。
- 初回はTestとProdの両方で3モデル・8データテストと固定期待値照合が成功。
- Goldに100を加える故障をpushすると、WebhookV2で自動起動。
- sales_reconcileが不一致2行を検出し、Testでパイプラインが失敗。Prodアクションは未実行。
- 本番のスタック更新時刻・タスク定義・使用イメージ・ワークフロー実行履歴は変化なし。Athenaでも売上3850.00を再確認。
- 故障前のテスト・本番の使用イメージは同じダイジェスト。

修正後の昇格結果、各実行ID、画像、コスト概算、残存リソースは上記のレポートに記録します。初期の接続PendingによるSource失敗2件は、意図的なデータ品質テスト失敗と区別しています。
