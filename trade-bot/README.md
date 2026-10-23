# Trade Desk

A six-agent AI research desk that runs on [OpenRouter](https://openrouter.ai) instead of Grok.

Six agents (Chief, Scout, News, Sentiment, Charts, Skeptic) talk to each other in
a group chat, each does one job, and the Chief sends you up to three decision cards
a day. Nothing trades unless you say so — this is paper-only by default.

> Not financial advice. Educational only. Trading can lose money. Everything here
> is editable: change the watchlist, the risk limits and the agent prompts in
> `config/` and re-run.

This is a reimplementation of the desk described in `trade_bot.txt`, using
OpenRouter for AI credits instead of Grok Bot, running on GitHub Actions.

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────┐
│  GitHub      │────▶│  src/main.py (runner)             │
│  Actions     │     │  orchestrates the six bots         │
└─────────────┘     │  reads config/rules.json           │
                     │  writes desk/paper-ledger.csv      │
                     └──┬────────────────┬──────────────┘
                        │                │
              ┌─────────▼──┐    ┌───────▼──────────┐
              │ src/market │    │ OpenRouter API   │
              │ price/     │    │ (all 6 agents)   │
              │ news data  │    └──────────────────┘
              └────────────┘
```

Each agent is a thin class with a system prompt, a user message, and a parser.
The runner threads messages through them in order, so the group chat is just a
list of messages.

## Setup

```bash
./scripts/setup.sh          # install python deps
cp config/rules.json config/rules.local.json   # edit watchlist/limits
cp config/agents.json config/agents.local.json # edit model ids
```

Secrets (never committed):

| Secret | Where |
|--------|-------|
| `OPENROUTER_API_KEY` | GitHub Actions → Settings → Secrets, or `.env` locally |
| `DESK_ADDRESS` | optional, for the on-chain Whale seat |

## Run

```bash
python scripts/run_desk.py        # run the full desk once
python scripts/run_desk.py --scout-only
python scripts/run_desk.py --chief-only
```

Output: `desk/decision-cards.md`, `desk/paper-ledger.csv`, `desk/run.log`.

## GitHub Actions

`.github/workflows/desk.yml` runs the desk every weekday at 11:00 AM Eastern
(Chief's card routine). Edit the schedule in the workflow file.

## Data sources (all free, keyless)

| Source | What it gives |
|--------|---------------|
| Yahoo Finance chart API | price, volume, 30-day avg volume |
| Google News RSS | headlines per ticker |
| Binance spot + futures | crypto price, depth, funding rate |
| Polymarket CLOB / Gamma | prediction market data |
| Reddit public JSON | crowd mood |

No broker, no wallet, no real money. Paper-only.