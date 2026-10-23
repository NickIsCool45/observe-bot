from typing import Any, List, Optional

from .base import Bot

class Sentiment(Bot):
    """Reads what people are saying and flags hype and paid promos"""

    SYSTEM_PROMPT = """For each lead, read what people are saying on X, Reddit and StockTwits. Report the mood (bullish, bearish or mixed), a score from -100 to 100, the three main reasons people give with example links, and a HYPE CHECK: paid promos, brand-new accounts, copy-paste posts or "guaranteed" claims. Repeat the lead ID. A post is never a fact. Where you stop: never place a real trade, never sign in to a broker, exchange or crypto wallet, never move money, and never edit desk/my-rules.md."""

    def __init__(self, model: str):
        super().__init__("Sentiment", model, self.SYSTEM_PROMPT)

    def build_user_message(self, lead_id: str, ticker: str, **kwargs) -> str:
        """Report on a specific lead"""
        return (
            f"Lead {lead_id} ({ticker}): Check sentiment on X, Reddit and StockTwits. "
            f"Report: mood, -100-to-100 score, three main reasons with example links, "
            "and a HYPE CHECK for paid/promo posts. "
            "Post is information only, never a fact. Don't trade."
        )

    def parse_response(self, content: str) -> Any:
        """Parse Sentiment report"""
        mood = None
        score = 0
        reasons = []
        hype = []
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Simple extraction: convert remaining lines to reasons
                if line.lower().startswith("mood:"):
                    mood = line.split(":", 1)[-1].strip("(bullish, bearish, mixed)")
                elif line.lower().startswith("hype"):
                    hype = line.split(":", 1)[-1].strip("check:").split(",")
                elif "link" in line.lower():
                    reasons.append(line)
        return {
            "lead_id": content.split("#L")[1].split()[0] if "#L" in content else "",
            "mood": mood,
            "score": score,
            "reasons": reasons[-3:],
            "hype": hype
        }