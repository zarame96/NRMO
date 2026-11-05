# Graphiti をデスクトップに導入する(Claude から使う)

Graphiti = 会話やメモを「人・課題・関心」などの関係つきで覚える知識グラフ(getzep/graphiti)。
**このファイルの手順は上流の README を確認しながら進めてください**(バージョンでオプション名が変わるため、私は未検証です)。

## 前提
- Docker Desktop(または Docker Engine + Compose)
- Git
- LLM の API キー(Graphiti の既定は OpenAI。Anthropic 等への切替は上流 README の設定を参照)

## 1. 取得と起動
```bash
git clone https://github.com/getzep/graphiti.git
cd graphiti/mcp_server
cp .env.example .env        # OPENAI_API_KEY などを記入(.env は絶対にコミットしない)
docker compose up -d        # グラフDB + MCPサーバが起動
docker compose ps           # 全て Up になっているか確認
```

## 2. Claude に登録
MCP サーバの URL は上流 README の記載を使う(HTTP の場合の例):
```bash
claude mcp add --transport http graphiti http://localhost:8000/mcp/
claude mcp list
```
Claude Desktop の場合は、設定の MCP サーバ追加で同じ URL を指定する。

## 3. 動作確認
Claude に「Graphiti に『請求書作成が毎回面倒』と記録して」→「Graphiti で私の不満を検索して」と頼み、
記録と検索ができればOK。

## 4. stock-hub との連携(次のステップ)
ノート保存時に Graphiti にも送り、「繰り返し出る話題」を取り出す。連携を実装する際は
`GRAPHITI_MCP_URL` を設定した時だけ動く形にし、未設定・停止中でも stock-hub は従来通り動くようにする。

## 注意
- 記録した内容は DB とLLMプロバイダ(API)に送られる。他人の個人情報や機密は入れない。
- ポートはローカルのみで公開する(`0.0.0.0` で外部公開しない)。
