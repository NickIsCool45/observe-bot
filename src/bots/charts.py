from typing import Any, List, Optional

try:
    import yfinance as yf
except ImportError:
    yf = None

from .base import Bot

class Charts(Bot):
    """Marks trend, support, resistance, entry, stop and target"""

    SYSTEM_PROMPT = """For each lead, read the numbers: trend on the daily and 1-hour chart, support and resistance, volume, and a possible entry, stop and target with the risk-to-reward ratio. Use only real price data, with the link and the time you pulled it. If data is missing, say what's missing instead of guessing. Repeat the lead ID. Where you stop: never place a real trade, never sign in to a broker, exchange or crypto wallet, never move money, and never edit desk/my-rules.md."""

    def __init__(self, model: str):
        super().__init__("Charts", model, self.SYSTEM_PROMPT)

    def build_user_message(self, lead_id: str, ticker: str, **kwargs) -> str:
        """Report on a specific lead"""
        return (
            f"Lead {lead_id} ({ticker}): Get the numbers. "
            "Report: trend (daily + 1h), support/resistance levels, volume, "
            "entry price, stop-loss, target price, risk-to-reward ratio. "
            "Use real data only with links and timestamps. Don't trade."
        )

    def parse_response(self, content: str) -> Any:
        """Parse Charts report"""
        trend = ""
        support = None
        resistance = None
        entry = None
        stop = None
        target = None
        rr = 0
        for line in content.split("\n"):
            line = line.strip()
            if "trend" in line.lower():
                trend = line.split(":", 1)[-1].strip()
            elif "support" in line.lower():
                support = line.split(":", 1)[-1].strip("(no support)")
            elif "resistance" in line.lower():
                resistance = line.split(":", 1)[-1].strip("(no resistance)")
            elif "entry" in line.lower():
                entry = line.split(":", 1)[-1].strip()
            elif "stop" in line.lower():
                stop = line.split(":", 1)[-1].strip()
            elif "target" in line.lower():
                target = line.split(":", 1)[-1].strip()
        return {
            "lead_id": content.split("#L")[1].split()[0] if "#L" in content else "",
            "trend": trend,
            "support": support,
            "resistance": resistance,
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_reward": rr
        }