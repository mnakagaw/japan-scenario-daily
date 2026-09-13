# 米中・中間選挙 シナリオ日報

公開サイト: https://mnakagaw.github.io/japan-scenario-daily/

日本への影響から米中関係と米中間選挙を読む、日本語の日報サイトです。公開ニュースの分析、シナリオの主観確率、参照研究を読んだ後の違い、総合判断を掲載します。

## ページ

- 最新号：短いサマリー、シナリオ表、ニュースの検索・絞り込み、4段階の全文
- シナリオ詳細：判定条件、根拠と留保、次の注目点、実際の記録履歴
- 日付比較・アーカイブ：公開済みの日付だけを表示
- 方法・訂正履歴、RSS、Markdown/JSON保存、印刷

初回は2026年9月13日。主観確率は未校正で併存可能です。初回の読前・前日値は未設定のまま残し、架空の推移は作成しません。

## ビルド

Python 3.12以上とNode.js（検査用）。外部JavaScriptやAPIへの実行時依存はありません。Pythonのzoneinfoが使うIANA時刻データが必要です（Ubuntuに標準搭載。Windowsで不足する場合はtzdataを導入）。

```sh
python build.py
python validate.py
node --check assets/app.js
node test-client.cjs
python preview.py
```

プレビューは `http://127.0.0.1:8767/japan-scenario-daily/`。公開対象は `dist/` のみです。

## 日報の追加

1. Web分析と数値を先に記録し、その後に参照研究を読む。内部調査の記録はこの公開リポジトリへ入れない。
2. 確認済みの公開版だけを `content/YYYY-MM-DD/report.md` と `data.json` に新規追加する。初回号の形式を参照し、本文は表示4000〜5000字にする。各ニュースに `countries` 配列で主な関係国・地域を付ける。既存号への表示ラベルの追加は、本文・確率を保持したまま同日フォルダの `news-labels.json`（ニュースIDからラベル配列への対応）で管理できる。特定国に絞れない市況には「国際市場」を使う。
3. `initial`、時刻、モデル、ニュースの期間、件数、比較説明、確率を当日の実態に合わせる。`numeric_recorded_at` は実際の数値記録時刻。`forecast_start`・`deadline`・定義・系列を保持し、比較条件が変わる場合は新しい系列にする。
4. 連続する前日で定義・期限・系列が一致した場合だけ `p_previous_final` と `daily_delta_pp` を入れる。欠測をまたいだ前日差はnull。`github_delta_pp` は当日読前の固定値がある場合だけ算出する。
5. 各日のファイルSHA-256を `publications.json` に追記する。公開済みの日付とファイルは変更しない。
6. ビルドと検査を通し、今回の公開物と必要なサイト変更だけをcommit/pushする。GitHub Actionsが検証後にPagesへ公開する。公開URLを確認する。

公開済みの誤記は原文を上書きせず、`corrections/` に日付、対象日、訂正内容・理由をJSONで追記します（`date`, `report_date`, `text`）。訂正は対象の日報と方法ページに表示されます。

ニュース生成はGitHub Actionsでは行いません。日報作成側が確認した公開版を追加し、Actionsは静的サイトの検証と配信だけを担当します。未作成日は架空の記事で補いません。

## 公開範囲

このリポジトリは公開ページと公開版の日報のための独立した保存先です。参照研究へのメッセージ・登録・書き戻しは行いません。認証情報、個人の作業パス、内部タスク・実行ログ、非公開研究の原文や参照先は含めません。記事本文の転載はせず、短い要約と外部の出典リンクを掲載します。

## GitHub Pages

mainへのpushで `.github/workflows/pages.yml` が実行されます。Pagesの公開元はGitHub Actions。公式アクションは確認したコミットに固定しています。

参考: [GitHub Pagesのカスタムワークフロー](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
