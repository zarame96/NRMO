# stock-hub

株価・関連ニュースを取得するWebアプリ。REST API と MCP サーバを備え、ジャービス等のアシスタントから呼べる。

## 起動
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000        # http://localhost:8000
STOCK_HUB_DEMO=1 uvicorn app.main:app   # 外部API無しのデモデータ
pytest
```

## API
| | |
|---|---|
| `GET /api/quote/{symbol}` | 最新値・前日比 |
| `GET /api/chart/{symbol}?range=3mo` | 日足終値 |
| `GET /api/news?q=トヨタ&limit=10&lang=ja` | ニュース(Google News RSS) |
| `GET /api/summary/{symbol}` | 株価+ニュース(アシスタント向け) |

銘柄: `AAPL`、日本株は `7203` / `7203.T`。外部公開するときは `STOCK_HUB_TOKEN` を設定すると全 `/api/*`(health除く)が `Authorization: Bearer <token>` 必須になる。

## ジャービスなどに接続
- **MCP対応(Claude Desktop / Claude Code 等)**
  ```bash
  claude mcp add stock-hub -- /絶対パス/.venv/bin/python -m app.mcp_server   # stock-hub ディレクトリで
  ```
  ツール: `get_stock_quote` / `get_stock_chart` / `get_stock_news`
- **独自のJarvis**: `GET /api/summary/{symbol}` を HTTP で叩くだけ(JSONを返す)。

## 注意
- 株価は Yahoo Finance の非公式エンドポイントを使用(個人利用向け、60秒キャッシュ)。429 が出る場合は時間を置くか、プロバイダ差し替え(`app/data.py` の `get_chart` のみ)。商用・多人数利用は正規データAPIを使うこと。
- 情報提供のみで投資助言ではありません。
