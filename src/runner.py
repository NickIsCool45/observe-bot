#!/usr/bin/env python3
"""Run the six-bot trading desk via OpenRouter API"""

import os
import sys
import json
import time
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
            balances = rules.get('paper_balance', 80)
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

    # Run log
    run_log = desk_dir / "run.log"
    if not run_log.exists():
        with open(run_log, "w") as f:
            f.write(f"# Trading Desk Run Log\nStarted: {datetime.now().isoformat()}\n\n")

    return {
        "rules_path": str(rules_path),
        "ledger_path": str(ledger_path),
        "desk_dir": str(desk_dir),
        "run_log": str(run_log)
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


def call_openrouter(client: OpenAI, model: str, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 1000) -> str:
    """Make a single OpenRouter API call"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"[ERROR calling {model}: {str(e)[:100]}]"


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

    if not client:
        print("\n[ERROR] OPENROUTER_API_KEY not set. This is required for the trading desk to run.")
        print("In GitHub Actions, ensure OPENROUTER_API_KEY secret is configured.")
        print("Locally, export OPENROUTER_API_KEY or create a .env file.")
        sys.exit(1)

    # === REAL API CALLS ===

    # Step 1: Scout finds leads
    print("\n[Scout] Running scout to find leads...")
    scout_prompt = scout.build_user_message()
    print(f"Scout command sent to model {scout.model}")

    scout_response = call_openrouter(client, scout.model, "", scout_prompt)
    print(f"[Scout] Response received ({len(scout_response)} chars)")

    # Parse scout's leads
    scout_leads = []
    for line in scout_response.split("\n"):
        line = line.strip()
        if line.startswith("#L"):
            parts = [p.strip() for p in line.split(" - ")]
            if len(parts) >= 4:
                lead_id = parts[0]
                ticker = parts[1]
                price = parts[2]
                move_str = parts[3].replace("%", "").replace("%%", "")
                try:
                    move = float(move_str)
                except ValueError:
                    move = 0
                vol = parts[4] if len(parts) > 4 else "1x"
                link = parts[5] if len(parts) > 5 else ""
                scout_leads.append({
                    "id": lead_id,
                    "ticker": ticker,
                    "price": price,
                    "move": move,
                    "volume": vol,
                    "link": link
                })

    print(f"[Scout] Found {len(scout_leads)} lead(s)")
    if scout_leads:
        for lead in scout_leads:
            print(f"  {lead['id']} - {lead['ticker']} - {lead['price']} - +{lead['move']:.1f}% - {lead['volume']}")

    if not scout_leads:
        print("[Scout] No leads found matching the criteria. Skipping downstream bots.")
        # Write empty decision cards
        desk_dir = Path(desk_paths.get("desk_dir", "desk"))
        cards_path = desk_dir / "decision-cards.md"
        with open(cards_path, "w") as f:
            f.write("# Trading Desk Decision Cards\n\n")
            f.write("No leads found this cycle. Keep monitoring.\n")
        print("\n" + "=" * 60)
        print("RUN COMPLETE")
        print(f"Decision cards written to: desk/decision-cards.md")
        print("=" * 60)
        return

    # Step 2-5: For each lead, get reports from News, Sentiment, Charts
    all_lead_data = []

    for lead in scout_leads[:5]:  # Process up to 5 leads
        lead_id = lead["id"]
        ticker = lead["ticker"]

        print(f"\n=== Processing lead {lead_id} ({ticker}) ===")

        # News report
        print(f"[News] Getting report for {lead_id}...")
        news_prompt = news.build_user_message(lead_id=lead_id, ticker=ticker)
        news_response = call_openrouter(client, news.model, "", news_prompt)
        print(f"[News] Got report")

        # Sentiment report
        print(f"[Sentiment] Getting report for {lead_id}...")
        sentiment_prompt = sentiment.build_user_message(lead_id=lead_id, ticker=ticker)
        sentiment_response = call_openrouter(client, sentiment.model, "", sentiment_prompt)
        print(f"[Sentiment] Got report")

        # Charts report
        print(f"[Charts] Getting report for {lead_id}...")
        charts_prompt = charts.build_user_message(lead_id=lead_id, ticker=ticker)
        charts_response = call_openrouter(client, charts.model, "", charts_prompt)
        print(f"[Charts] Got report")

        # Parse responses
        parsed_news = news.parse_response(news_response)
        parsed_sentiment = sentiment.parse_response(sentiment_response)
        parsed_charts = charts.parse_response(charts_response)

        # Step 6: Skeptic validates
        print(f"[Skeptic] Validating lead {lead_id}...")
        # Build a summary for skeptic
        skeptic_input = {
            "id": lead_id,
            "ticker": ticker,
            "price": lead.get("price", "0"),
            "move": lead.get("move", 0),
            "news": parsed_news.get("reported", [])[:3],
            "sentiment": {
                "mood": parsed_sentiment.get("mood", "mixed"),
                "score": parsed_sentiment.get("score", 0),
                "reasons": parsed_sentiment.get("reasons", [])[:3]
            },
            "charts": {
                "trend": parsed_charts.get("trend", "neutral"),
                "support": parsed_charts.get("support"),
                "resistance": parsed_charts.get("resistance"),
                "entry": parsed_charts.get("entry"),
                "stop": parsed_charts.get("stop"),
                "target": parsed_charts.get("target")
            }
        }

        # Get rules info for skeptic
        max_size = rules_config.get("max_size_pct", 5)
        max_loss = rules_config.get("max_loss_pct", 1)

        skeptic_prompt = skeptic.build_user_message(lead=skeptic_input, min_move=3)
        skeptic_response = call_openrouter(client, skeptic.model, "", skeptic_prompt)
        parsed_skeptic = skeptic.parse_response(skeptic_response)
        verdict = parsed_skeptic.get("verdict", "SKIP")
        reasons = parsed_skeptic.get("reasons", [])

        print(f"[Skeptic] Verdict: {verdict}")
        if reasons:
            for r in reasons[:2]:
                print(f"  - {r[:80]}")

        # Step 7: Chief issues decision cards
        # Chief only processes leads that got APPROVE or REDUCE
        if verdict in ["APPROVE", "REDUCE"]:
            print(f"[Chief] Processing {lead_id} with verdict {verdict}...")
            chief_prompt = chief.build_user_message()
            chief_response = call_openrouter(client, chief.model, "", chief_prompt)
            print(f"[Chief] Got card guidance")

            # Extract card info - simple parsing
            card_lines = []
            for line in chief_response.split("\n"):
                line = line.strip()
                if "#L" in line and "-" in line:
                    card_lines.append(line)

            if card_lines:
                # Create decision card entry
                card_entry = {
                    "lead_id": lead_id,
                    "ticker": ticker,
                    "verdict": verdict,
                    "reasons": reasons,
                    "news_summary": parsed_news.get("reported", [])[:2],
                    "sentiment_summary": {
                        "mood": parsed_sentiment.get("mood", "mixed"),
                        "score": parsed_sentiment.get("score", 0)
                    },
                    "charts_data": {
                        "trend": parsed_charts.get("trend", "neutral"),
                        "entry": parsed_charts.get("entry"),
                        "stop": parsed_charts.get("stop"),
                        "target": parsed_charts.get("target")
                    }
                }
                all_lead_data.append(card_entry)

                # Log to run.log
                run_log = desk_paths.get("run_log", "")
                if run_log:
                    with open(run_log, "a") as f:
                        f.write(f"\n# Lead {lead_id} - {ticker}\n")
                        f.write(f"Verdict: {verdict}\n")
                        if reasons:
                            f.write(f"Reasons: {'; '.join(reasons)}\n")

        # Small delay to be respectful of API rate limits
        time.sleep(0.5)

    # Write decision cards to file
    desk_dir = Path(desk_paths.get("desk_dir", "desk"))
    cards_path = desk_dir / "decision-cards.md"
    with open(cards_path, "w") as f:
        f.write("# Trading Desk Decision Cards\n\n")
        if all_lead_data:
            for card in all_lead_data:
                f.write(f"## {card['lead_id']} - {card['ticker']} - {card['verdict']}\n\n")
                f.write(f"**Entry:** {card['charts_data'].get('entry', 'N/A')}\n")
                f.write(f"**Stop:** {card['charts_data'].get('stop', 'N/A')}\n")
                f.write(f"**Target:** {card['charts_data'].get('target', 'N/A')}\n")
                f.write(f"**Risk-Reward:** Calculated from stop/target\n\n")
                f.write(f"**Three Strongest Reasons:**\n")
                for i, reason in enumerate(card.get("reasons", [])[:3], 1):
                    f.write(f"{i}. {reason[:100]}\n")
                f.write(f"\n**Biggest Risk:** {card.get('charts_data', {}).get('trend', 'TBD')}\n")
                f.write(f"\n**News Links:**\n")
                for link in card.get("news_summary", []):
                    f.write(f"- {link[:100]}\n")
                f.write(f"\n**Sentiment:** {card.get('sentiment_summary', {}).get('mood', 'mixed')} "
                        f"(score: {card.get('sentiment_summary', {}).get('score', 0)})\n")
                f.write(f"\n---\n\n")
        else:
            f.write("No decisions this cycle. Keep monitoring.\n")

    # Update ledger
    ledger_path = Path(desk_paths.get("ledger_path", "desk/paper-ledger.csv"))
    # Append new entries
    if all_lead_data:
        with open(ledger_path, "a") as f:
            for card in all_lead_data:
                f.write(f"{datetime.now().strftime('%Y-%m-%d')},{card['lead_id']},"
                        f"{card['ticker']},BUY,{card['charts_data'].get('entry', 'N/A')},"
                        f"{card['charts_data'].get('stop', 'N/A')},{card['charts_data'].get('target', 'N/A')},"
                        f"{rules_config.get('paper_balance', 80) * rules_config.get('max_size_pct', 5) / 100:.2f},"
                        f"open,,0,Paper trade\n")

    print("\n" + "=" * 60)
    print("RUN COMPLETE")
    final_value = 80 + sum(
        float(line.split(',')[10]) if len(line.split(',')) > 10 and 'Paper trade' not in line else 0
        for line in open(ledger_path) if line.strip()
    )
    print(f"\nDecision cards written to: desk/decision-cards.md")
    print(f"Ledger updated: {ledger_path}")
    print(f"Final portfolio value: ${final_value:.2f} (starting: ${rules_config.get('paper_balance', 80)})")
    print("=" * 60)


if __name__ == "__main__":
    try:
        rules = load_rules()
        scout_runs_desk(rules, None)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FATAL ERROR] {e}")
        sys.exit(1)