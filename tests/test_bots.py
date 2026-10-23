import pytest
from src.bots.base import load_config
from src.bots.chief import Chief
from src.bots.scout import Scout
from src.bots.skeptic import Skeptic

def test_load_config():
    config = load_config("config/rules.json")
    assert "watchlist" in config
    assert "paper_balance" in config

def test_chief_init():
    config = load_config("config/rules.json")
    chief = Chief(model="anthropic/claude-opus-4.5", rules_config=config)
    assert chief.name == "Chief"
    assert "research-only" in chief.description

def test_scout_init():
    scout = Scout(model="meta-llama/llama-4-maverick", watchlist=["NVDA", "AAPL"])
    assert scout.name == "Scout"
    assert len(scout.watchlist) == 2

def test_skeptic_init():
    config = load_config("config/rules.json")
    skeptic = Skeptic(model="mistralai/mistral-large-4-0", rules=config)
    assert skeptic.name == "Skeptic"
