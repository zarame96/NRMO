"""MCPサーバ。Claude Desktop / Claude Code / MCP対応のJarvis系アシスタントから株情報を呼べる。

起動: python -m app.mcp_server        (stdio)
"""
from mcp.server.fastmcp import FastMCP

from . import data, hub
from . import modules  # noqa: F401

mcp = FastMCP("stock-hub")


@mcp.tool()
def get_stock_quote(symbol: str) -> dict:
    """株価の最新値と前日比を返す。米国株は AAPL、日本株は 7203 または 7203.T。"""
    return data.get_quote(symbol)


@mcp.tool()
def get_stock_chart(symbol: str, range: str = "3mo") -> dict:
    """日足終値の時系列(range: 5d,1mo,3mo,6mo,1y,5y)。"""
    return data.get_chart(symbol, range)


@mcp.tool()
def get_stock_news(query: str, limit: int = 10, lang: str = "ja") -> list[dict]:
    """銘柄名・ティッカー・テーマで関連ニュースを検索(lang: ja|en)。"""
    return data.get_news(query, limit, lang)


@mcp.tool()
def list_hub_modules() -> list[dict]:
    """統合環境のモジュール一覧(カテゴリ>モジュール、有効/無効)。"""
    return hub.tree()


@mcp.tool()
def run_hub_module(module_id: str) -> dict:
    """モジュールを実行して結果を返す(例: finance.crypto, news.topics, net.tech, notes.memo)。"""
    return hub.run(module_id)


if __name__ == "__main__":
    mcp.run()
