# negotiation-agent

## 概要
商談の音声データと会社名を入力すると、
- 音声→テキスト変換（Whisper）
- テンション・興味分析（OpenAI GPT）
- 会社情報・予算推定（OpenAI GPT）
- Dify事例DB（Notion）からAIによる事例検索
- 3エージェント合議による最適提案生成
- Notion出力DBに「議事録」「提案」を自動記録
までを自動化するAIエージェントシステムです。

---

## 必要なもの
- Python 3.8+
- Node.js（Next.jsフロント用）
- OpenAI APIキー
- Notion APIキー
- Dify事例DBのID（例: 1813ace1838e8025909beb861f5972b2）
- 出力先DBのID（例: 17c3ace1838e80208a52f27f31240cea）

---

## セットアップ手順

### 1. .envファイルの作成
`backend/.env` に以下を記載してください。

```
OPENAI_API_KEY=sk-...
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=1813ace1838e8025909beb861f5972b2
OUTPUT_DATABASE_ID=17c3ace1838e80208a52f27f31240cea
```

### 2. Pythonパッケージのインストール

```bash
cd backend
source venv/bin/activate  # 仮想環境がなければ python3 -m venv venv
pip install -r requirements.txt  # requirements.txtがなければ手動で fastapi, uvicorn, openai, notion-client, python-dotenv をインストール
```

### 3. Next.jsフロントのセットアップ

```bash
cd frontend
npm install
npm run dev
```

### 4. FastAPIサーバの起動

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

---

## テスト方法

1. ブラウザで `http://localhost:3000` にアクセス
2. 音声ファイル（mp3, wav等）と会社名を入力し「解析実行」
3. 解析が完了すると、
    - 議事録
    - 提案
    - 各エージェントの推論ログ
   が画面に表示されます
4. Notionの出力先DB（企業ごとにページが作成され、その中に「議事録」「提案」ページが自動生成）を確認

---

## 注意事項
- NotionのDBカラム名やIDはご自身の環境に合わせて調整してください
- OpenAI/Notion APIの利用には従量課金が発生します
- .envファイルは絶対に公開しないでください

---

## トラブルシューティング
- APIキーやDB IDが間違っているとエラーになります
- Notion DBのカラム名が違う場合はコードを修正してください
- WhisperやGPTのAPI利用制限・料金にご注意ください

---

## ライセンス
MIT 