# forex-agent

Paper-trading agent for FX majors + commodities. Part of [`janus`](https://github.com/sppidy/janus).

- ICT-style strategies: Asian Sweep + CISD detection, London breakout, killzone reversals
- 15-minute candles, FX majors + cross pairs + gold/silver
- Shares core infrastructure (`data_fetcher`, `backtester`, `paper_trader`, `learner`, `market_calendar`) with the NSE agent — kept as separate copies so each market evolves independently

> **Disclaimer:** Paper-trading only. Not financial advice.

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                      # at least one LLM key
python main.py help
```

## Strategies

| File | Strategy |
| --- | --- |
| `forex_strategy.py`     | ICT Asian Sweep — Asian session high/low sweep + CISD + Fib 50% retrace |
| `london_breakout.py`    | Pre-London range breakout (3 AM – 12 PM ET) |
| `killzone_reversal.py`  | London / NY-open killzone reversals |
| `strategy_engine.py`    | Maps pairs to strategies with trading windows (IST/ET/UTC) |

## Config (`config.py`)

- `INITIAL_CAPITAL = $100,000`
- `MAX_POSITION_SIZE_PCT = 5%` (tighter than NSE's 10%)
- `MAX_OPEN_POSITIONS = 10`
- 15-minute candle interval
- Watchlist: EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, NZD/USD + cross pairs + GC=F (gold), SI=F (silver)

## License

[Apache-2.0](LICENSE). Contributing guidelines and security policy live in the [super-repo](https://github.com/sppidy/janus).
