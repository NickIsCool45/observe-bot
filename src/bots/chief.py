from typing import Any, List, Optional

from .base import Bot, load_config

class Chief(Bot):
    """Runs the desk, gives every idea an ID and sends decision cards"""

    SYSTEM_PROMPT = """You run a research-only trading desk and coordinate Scout, News, Sentiment, Charts and Skeptic in our group chat. Every lead gets an ID like #L001, and every message about it repeats that ID. When a lead has reports from all four researchers plus Skeptic's verdict, send me one decision card: lead ID, ticker, verdict (PAPER BUY, WAIT or SKIP), the three strongest reasons, the biggest risk, entry, stop and target, and what would prove it wrong. Send at most 3 cards a day. If two bots quote different numbers, flag it instead of picking one. Where you stop: never place a real trade, never sign in to a broker, exchange or crypto wallet, never move money, and never edit desk/my-rules.md."""

    def __init__(self, model: str, rules_config: dict):
        super().__init__("Chief", model, self.SYSTEM_PROMPT)
        self.rules = rules_config

    def build_user_message(self, **kwargs) -> str:
        """Build message from rules and output files"""
        rules = "\n".join(f"{k}: {v}" for k, v in self.rules.items())
        return f"""
Read these rules:
{rules}

If trade_ledger.csv exists, close any open trades that hit their stop or target and update their P&L.

Then run the scout.cron routine to find leads and generate decision cards.
""".strip()

    def parse_response(self, content: str) -> Any:
        """Parse Chief's response as decision cards"""
        return {
            "cards": self._extract_cards(content),
            "ledger_updated": any("triggered" in line.lower() for line in content.split("\n"))
        }

    def _extract_cards(self, content: str) -> List[dict]:
        """Extract decision cards from Chief's output"""
        cards = []
        # Look for cards in markdown format
        for line in content.split("\n"):
            if "#L" in line and "-" in line:
                # Basic card header pattern
                parts = line.split("-")
                if len(parts) >= 3:
                    ticker = parts[0].strip()
                    verdict = parts[1].strip()
                    cards.append({"ticker": ticker, "verdict": verdict})
        return cards