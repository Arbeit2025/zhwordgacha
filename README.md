# zhwordgacha（中国語単語ガチャ）

「ガチャを引く」感覚で中国語の単語に出会える、単一ファイル Flask の小さな Web アプリです。

## これは何をするもの？

- 「ガチャを引く」ボタンを押すと、中国語の単語が1つランダムに表示されます
  - 簡体字・ピンイン・日本語訳・短い例文（中国語＋日本語訳つき）
- 単語データはコード内蔵の110語（HSK初級〜中級程度の基本語彙）です
- 引いた単語は SQLite に履歴として保存され、「今日引いた単語」と「履歴一覧」で振り返れます
- 1日1語に縛られず、同じ日に何回でも引けます

## 由来

zhtranslate（中国語翻訳ツール）× おみくじ の発想から生まれた、中国語学習用の小さな派生ツールです。翻訳するだけではなく、「引く」楽しさで単語に触れる機会を増やすことを狙っています。

## ローカル起動

```bash
pip install -r requirements.txt
python app.py
```

起動したらブラウザで http://127.0.0.1:5000 を開いてください。

履歴 DB の保存先は環境変数 `ZHWORDGACHA_DB` で変更できます（未設定時はアプリと同じフォルダの `gacha_history.db`）。

## テスト

```bash
python -m unittest discover -s tests
```

テストは一時 DB を使い、実際の履歴ファイルには触れません。

## デプロイ（Render）

`render.yaml` を同梱しています。Render の Web Service（Free / Python）として、ビルド `pip install -r requirements.txt`、起動 `gunicorn app:app` で公開できます。ヘルスチェックは `/healthz` です。

※ Render Free ではファイルが再デプロイ等で消えるため、履歴も消える場合があります。履歴は「残ればラッキー」程度の位置づけです。

## 構成

- `app.py` … 本体（単一ファイル。単語データ内蔵、履歴のみ SQLite）
- `tests/test_app.py` … unittest
- `requirements.txt` … Flask / gunicorn
- `render.yaml` … Render 用設定
