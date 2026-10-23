from typing import Any, List, Optional

from .base import Bot

class Skeptic(Bot):
    """Risk officer and hard gate"""

    SYSTEM_PROMPT = """You are the desk's risk officer and hard gate. Read my rules. After Scout, News, Sentiment and Charts report on a lead, answer APPROVE, REDUCE or REJECT with one line of reasons. Check that every number has a source, that two bots quoting the same number agree, that nothing breaks my rules, that the news isn't just hype, and that the stop fits my max loss. You can only make my rules stricter, never looser. If anything is missing or doesn't match, REJECT. Where you stop: never place a real trade, never sign in to a broker, exchange or crypto wallet, never move money, and never edit desk/my-rules.md."""

    # Default thresholds; these should be loaded from rules
    MAX_SIZE_PCT = 5
    MAX_LOSS_PCT = 1

    def __init__(self, model: str, rules: dict):
        super().__init__("Skeptic", model, self.SYSTEM_PROMPT)
        self.rules = rules

    def build_user_message(self, lead: dict, **kwargs) -> str:
        """Validate a lead against rules"""
        # Extract key numbers for validation
        ticker = lead.get("ticker", "")
        price = lead.get("price", 0)
        move = lead.get("move", 0)
        entry = lead.get("entry", price)
        stop = lead.get("stop", "N/A")
        target = lead.get("target", "N/A")
        rr = lead.get("risk_reward", 0)

        return (
            f"Lead {lead.get('id', 'N/A')} ({ticker}): Validate against these rules:\n"
            f"- Max size: {self.MAX_SIZE_PCT}% of balance per trade\n"
            f"- Max loss: {self.MAX_LOSS_PCT}% per trade\n"
            f"- Min move: {kwargs.get('min_move', 3)}% threshold\n\n"
            "Check:\n"
            f"1. Entry vs current price is plausible ({entry} vs {price})\n"
            f"2. Risk-reward ({rr}) is positive\n"
            f"3. Stop is realistic (based on max {self.MAX_LOSS_PCT}% loss)\n"
            f"4. Target is reachable (multi-month horizon)\n\n"
            "Answer: APPROVE, REDUCE, or REJECT with one line of reasons."
        )

    def parse_response(self, content: str) -> Any:
        """Parse Skeptic's verdict"""
        verdict = "SKIP"
        for line in content.split("\n"):
            line = line.strip().upper()
            if line.startswith("APPROVE"):
                verdict = line.split()[0]
            elif line.startswith("REDUCE"):
                verdict = line.split()[0]
            elif line.startswith("REJECT"):
                verdict = line.split()[0]
        return {
            "verdict": verdict,
            "reasons": [line.strip() for line in content.split("\n")[:3]]
        }