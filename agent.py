"""
agent.py — OPTIONAL Phase 3: the AI brain on top of your screener.

This turns the pipeline into a conversational agent: you ask questions in
plain English ("compare TCS and Infosys", "which fund held up best in crashes?")
and Claude decides which of your analysis functions to call, then explains
the numbers like an analyst would.

Setup (only needed for this file — everything else is free):
  1. pip install anthropic
  2. Get an API key at https://platform.claude.com  (usage-based; a few rupees
     per question at typical sizes)
  3. Set it:   export ANTHROPIC_API_KEY="sk-ant-..."     (Mac/Linux)
               setx ANTHROPIC_API_KEY "sk-ant-..."       (Windows, then reopen terminal)
  4. Run:      python agent.py

Docs: https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview
"""

import json
import anthropic

from config import STOCK_WATCHLIST, MF_WATCHLIST
from providers.registry import get_stock_provider, get_mf_provider
from config import STOCK_PROVIDER, MF_PROVIDER

_stocks = get_stock_provider(STOCK_PROVIDER)
_mf = get_mf_provider(MF_PROVIDER)
get_stock_data = _stocks.get_stock
get_all_stocks = _stocks.get_many
get_nav_history = _mf.get_nav_history
from analysis.stock_screener import score_stocks
from analysis.mf_analyzer import analyze_fund

MODEL = "claude-sonnet-4-6"  # good balance of capability and cost

# ----- 1. Describe your Python functions as tools Claude can call -----
TOOLS = [
    {
        "name": "get_stock_metrics",
        "description": "Fetch fundamentals, valuation and momentum metrics for one NSE stock. Ticker must end in .NS, e.g. TCS.NS",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "screen_watchlist",
        "description": "Score and rank ALL stocks in the user's watchlist across quality, growth, valuation and momentum. Use for 'best stock' style questions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_fund_metrics",
        "description": "Fetch CAGR, rolling returns, volatility, drawdown and Sharpe for one mutual fund by its AMFI scheme code.",
        "input_schema": {
            "type": "object",
            "properties": {"scheme_code": {"type": "string"}},
            "required": ["scheme_code"],
        },
    },
]


def run_tool(name: str, args: dict) -> str:
    """Execute the tool Claude asked for and return the result as JSON text."""
    try:
        if name == "get_stock_metrics":
            return json.dumps(get_stock_data(args["ticker"]), default=str)
        if name == "screen_watchlist":
            scored = score_stocks(get_all_stocks(STOCK_WATCHLIST))
            return scored.round(2).to_json(orient="records")
        if name == "get_fund_metrics":
            nav = get_nav_history(args["scheme_code"])
            return json.dumps(analyze_fund(nav), default=str)
        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error: {e}"


SYSTEM_PROMPT = f"""You are a research analyst for Indian markets assisting the user
with THEIR OWN analysis. Use the tools to get real numbers — never invent figures.
Always present both strengths and risks. Remind the user that rankings are relative
to their watchlist and this is research, not investment advice.
The user's mutual fund watchlist (code: name): {json.dumps(MF_WATCHLIST)}"""


def chat():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment
    messages = []
    print("Indian Markets Research Agent — type 'quit' to exit\n")

    while True:
        user_q = input("You: ").strip()
        if user_q.lower() in {"quit", "exit"}:
            break
        messages.append({"role": "user", "content": user_q})

        # Agent loop: keep going while Claude wants to call tools
        while True:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                # Final text answer
                for block in response.content:
                    if block.type == "text":
                        print(f"\nAgent: {block.text}\n")
                break

            # Execute every tool call Claude requested, feed results back
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [calling {block.name} ...]")
                    result = run_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    chat()
