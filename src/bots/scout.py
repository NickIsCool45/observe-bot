from typing import Any, List, Optional
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    yf = None

from .base import Bot

class Scout(Bot):
    """Finds leads: unusual volume and big moves"""

    SYSTEM_PROMPT = """You find leads for my research desk. Scan the watchlist and the day's top movers for unusual volume (at least 2x the 30-day average) or a big price move. Give each new lead the next ID (#L001, #L002 and so on) and post: ID, ticker, price, % move, volume vs average, and the source link with the time you checked it. Post at most 5 leads a day, best first. If nothing qualifies, post nothing. You only find leads, you never say buy. Where you stop: never place a real trade, never sign in to a broker, exchange or crypto wallet, never move money, and never edit desk/my-rules.md."""

    # Batch size for time-efficient calls
    BATCH_SIZE = 10
    MIN_MOVE_PCT = 3

    def __init__(self, model: str, watchlist: List[str]):
        super().__init__("Scout", model, self.SYSTEM_PROMPT)
        self.watchlist = [t.upper() for t in watchlist if t.strip()]

    def build_user_message(self, **kwargs) -> str:
        """Run scout routine"""
        return (
            "Use this command in the group to trigger scouting:\n"
            f"@Scout scan this watchlist: {', '.join(self.watchlist)}\n"
            f"Look for unusual volume (at least 2x 30-day avg) or price moves of {self.MIN_MOVE_PCT}% or more. "
            f"Post at most 5 leads a day, best first. "
            f"Format: #L{{id}} - {{ticker}} - {{price}} - {{move}}% - {{volume}}x - {{link}}\n\n"
            "If nothing qualifies, post nothing. Don't trade."
        )

    def parse_response(self, content: str) -> Any:
        """Parse Scout's leads"""
        leads = []
        # Extract markdown list items
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("#L"):
                # Simple parse: #L001 - NVDA - $180.23 - +4.2% - 3.1x - link
                parts = [p.strip() for p in line.split(" - ")]
                if len(parts) >= 5:
                    lead_id = parts[0]
                    ticker = parts[1]
                    price = parts[2]
                    move = parts[3].replace("%", "").replace("%%", "")
                    vol = parts[4]
                    link = parts[5] if len(parts) > 5 else ""
                    leads.append({
                        "id": lead_id,
                        "ticker": ticker,
                        "price": price,
                        "move": float(move),
                        "volume": float(vol.replace("x", "")),
                        "link": link or ""
                    })
        return {"leads": leads}