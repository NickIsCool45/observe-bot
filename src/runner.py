#!/usr/bin/env python3
"""Run the six-bot trading desk"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bots.base import Bot, load_config
from src.bots.chief import Chief
from src.bots.scout import Scout
from src.bots.news import News
from src.bots.sentiment import Sentiment
from src.bots.charts import Charts
from src.bots.skeptic import Skeptic

# Optional import for OpenRouter
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None



def load_rules() -> dict:
    """Load desk rules with local override support"""
    rules_config = load_config("config/rules.json")
    return rules_config


def setup_desk_directories() -> dict:
    """Create desk directory structure and files"""
    desk_dir = Path("desk")
    desk_dir.mkdir(exist_ok=True)

    # Rules file
    rules_path = desk_dir / "my-rules.md"
    if not rules_path.exists():
        rules = load_rules()
        with open(rules_path, "w") as f:
            f.write("# Paper Trading Desk Rules\n\n")
            f.write(f"MODE: {rules.get('mode', 'PAPER ONLY')}\n")
            balances = rules.get('paper_balance', 10000)
            f.write(f"PAPER BALANCE: ${balances}\n")
            watchlist = ", ".join(rules.get('watchlist', []))
            f.write(f"WATCHLIST: {watchlist}\n")
            f.write(f"MAX SIZE: {rules.get('max_size_pct', 5)}% of the balance per paper trade\n")
            f.write(f"MAX LOSS: {rules.get('max_loss_pct', 1)}% of the balance per trade\n")
            f.write(f"DAILY LIMIT: {rules.get('daily_loss_limit_pct', 2)}% loss per day triggers pause\n")
            f.write(f"ALWAYS SKIP: {', '.join(rules.get('always_skip', []))}\n")
            f.write(f"CARDS: {rules.get('cards_per_day', 3)} per day, maximum\n")
            f.write(f"CHANGES: only the human can change this file\n")

    # Paper ledger CSV
    ledger_path = desk_dir / "paper-ledger.csv"
    if not ledger_path.exists():
        with open(ledger_path, "w") as f:
            f.write("date,lead_id,ticker,side,entry,stop,target,size,status,exit,pnl,note\n")

    return {
        "rules_path": str(rules_path),
        "ledger_path": str(ledger_path),
        "desk_dir": str(desk_dir)
    }


def make_openai_client(api_key: str = None):
    """Create OpenRouter/OpenAI client"""
    try:
        from openai import OpenAI
    except ImportError:
        print("[WARN] 'openai' module not installed. Install via: pip install openai")
        return None

    if api_key is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("[WARN] OPENROUTER_API_KEY not set in environment.")
            return None

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )


def scout_runs_desk(rules: dict, agents_config: dict) -> None:
    """Main runner: Scout finds leads, others report, Skeptic validates, Chief issues cards"""

    print("=" * 60)
    print("AI TRADING DESK - OPENROUTER MODE")
    print("=" * 60)

    # Setup
    print("\n[Setup] Creating desk directories...")
    desk_paths = setup_desk_directories()

    # Load config
    print("\n[Setup] Loading configuration...")
    agents = load_config("config/agents.json")
    rules_config = load_rules()

    # Initialize bots
    print("\n[Setup] Initializing agents...")
    chief = Chief(
        model=agents["chief"]["model"],
        rules_config=rules_config
    )
    scout = Scout(
        model=agents["scout"]["model"],
        watchlist=rules_config.get("watchlist", ["NVDA", "AAPL"])
    )
    news = News(model=agents["news"]["model"])
    sentiment = Sentiment(model=agents["sentiment"]["model"])
    charts = Charts(model=agents["charts"]["model"])
    skeptic = Skeptic(
        model=agents["skeptic"]["model"],
        rules=rules_config
    )

    bots = [chief, scout, news, sentiment, charts, skeptic]

    # Get API key
    print("\n[Setup] Loading OpenRouter API key...")
    client = make_openai_client()

    # Prompt approach (for demo/paper mode)
    print("\n[Scout] Running scout to find leads...")
    scout_prompt = scout.build_user_message()
    print(f"Scout command:\n{scout_prompt}\n")

    # Uncomment for actual API calls:
    # scout_messages = [{"role": "user", "content": scout_prompt}]
    # scout_response = client.chat.completions.create(
    #     model=scout.model,
    #     messages=scout_messages,
    #     temperature=0.2
    # )
    # print(f"[Scout] {scout_response.choices[0].message.content}")

    print("[Demo] Scout output would appear here:")
    demo_lead = {
        "id": "#L001",
        "ticker": "NVDA",
        "price": "$180.23",
        "move": 4.2,
        "volume": 3.1,
        "link": "finance.yahoo.com/portfolio?p=NVDA"
    }
    print(f"#L001 - NVDA - $180.23 - +4.2% - 3.1x - https://finance.yahoo.com/portfolio?p=NVDA")

    # News report
    print("\n[News] Report on lead L001:")
    news_prompt = news.build_user_message(lead_id="L001", ticker="NVDA")
    print(f"News command:\n{news_prompt}\n")

    print("[News] Report would show: REPORTED (earnings, filings), UNVERIFIED (rumors)\n")

    # Sentiment report
    print("\n[Sentiment] Mood, score, reasons, hype check for NVDA:")
    sentiment_prompt = sentiment.build_user_message(lead_id="L001", ticker="NVDA")
    print(f"Sentiment command:\n{sentiment_prompt}\n")

    print("[Sentiment] Report would show: mood, -100 to 100 score, top reasons, hype\n")

    # Charts report
    print("\n[Charts] Trend, support, resistance, entry, stop, target:")
    charts_prompt = charts.build_user_message(lead_id="L001", ticker="NVDA")
    print(f"Charts command:\n{charts_prompt}\n")

    print("[Charts] Report would show: daily/trend, support/resistance, entries, strike\n")

    # Skeptic verdict
    print(f"\n[Skeptic] Validate lead {demo_lead['id']} ({demo_lead['ticker']}):")
    skeptic_prompt = skeptic.build_user_message(lead=demo_lead, min_move=3)
    print(f"Skeptic command:\n{skeptic_prompt}\n")

    print("[Skeptic] Verdict: APPROVE/REDUCE/REJECT with reasons\n")

    # Chief decision cards
    print("\n[Chief] Collecting reports and sending decision cards:")
    chief_prompt = chief.build_user_message()
    print(f"Chief command:\n{chief_prompt}\n")

    print("\n[Chief] Decision card would look like:\n")
    print("#L001 - NVDA - PAPER BUY\n")
    print("Entry: $178.50 (10:30 AM ET)\n")
    print("Stop: $176.30 (1.2% risk)\n")
    print("Target: $190.50 (RR 2.5:1)\n")
    print("Three strongest reasons:\n")
    print("1. Earnings beat consensus with +15% revenue growth\n")
    print("2. Strong AI adoption driving GPU demand\n")
    print("3. Analysts raised price targets across the board\n")
    print("Biggest risk:\n")
    print("- US export controls on AI chips remain uncertain\n")
    print("What would prove it wrong:\n")
    print("- Failed to meet guidance on capital spending or margins\n")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("\nTo run the full desk with OpenRouter, edit src/runner.py")
    print("to make actual API calls via client.chat.completions.create().")
    print("=" * 60)


if __name__ == "__main__":
    try:
        rules = load_rules()
        scout_runs_desk(rules, None)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)