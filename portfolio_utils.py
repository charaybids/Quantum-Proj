# ============================================================
# Shared utilities for the Quantum vs Classical portfolio study
# (data loading, performance metrics, portfolio helpers)
# ============================================================

import os
import time
import tempfile
import numpy as np
import pandas as pd

# ------------------------------------------------------------
# Asset universe
# 8 liquid ETFs spanning the major asset classes. Eight assets
# means an 8-qubit QUBO, which runs in milliseconds on the
# state-vector simulator while still giving a non-trivial
# "choose B of 8" combinatorial selection problem.
# ------------------------------------------------------------
TICKERS = [
    "SPY",   # US large-cap equity
    "QQQ",   # US growth / technology
    "EFA",   # Developed international equity
    "EEM",   # Emerging-market equity
    "TLT",   # Long-dated US Treasuries
    "LQD",   # Investment-grade corporate bonds
    "GLD",   # Gold
    "DBC",   # Broad commodities
]

# Annualisation factor for monthly data
PERIODS_PER_YEAR = 12

# Cache location so the notebook and both scripts reuse one download
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_CACHE_FILE = os.path.join(_CACHE_DIR, "monthly_returns.csv")


def download_monthly_returns(start="2015-01-01", end="2024-12-31",
                             tickers=None, use_cache=True):
    """Download adjusted prices and return a DataFrame of monthly returns.

    Results are cached to data/monthly_returns.csv so repeated runs are
    fast and reproducible (and work offline once cached).
    """
    tickers = tickers or TICKERS

    if use_cache and os.path.exists(_CACHE_FILE):
        cached = pd.read_csv(_CACHE_FILE, index_col=0, parse_dates=True)
        if list(cached.columns) == list(tickers):
            return cached

    import yfinance as yf

    # Use an isolated, writable timezone cache to avoid the
    # "database is locked" error that yfinance can throw when its default
    # cache lives on a synced drive (e.g. OneDrive).
    try:
        yf.set_tz_cache_location(os.path.join(tempfile.gettempdir(), "yf_tz_cache"))
    except Exception:
        pass

    # Download each ticker separately (threads off) with a couple of retries
    # so one flaky symbol cannot wipe out the whole panel.
    closes = {}
    for ticker in tickers:
        for attempt in range(3):
            try:
                data = yf.download(
                    ticker,
                    start=start,
                    end=end,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                )
                if not data.empty:
                    closes[ticker] = data["Close"].squeeze()
                    break
            except Exception:
                pass
            time.sleep(1.0)
        if ticker not in closes:
            raise RuntimeError(f"Failed to download price data for {ticker}")

    prices = pd.DataFrame(closes)[tickers]

    monthly_prices = prices.resample("ME").last()
    monthly_returns = monthly_prices.pct_change(fill_method=None).dropna()

    if use_cache:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        monthly_returns.to_csv(_CACHE_FILE)

    return monthly_returns


# ------------------------------------------------------------
# Performance metrics (operate on a Series of periodic returns)
# ------------------------------------------------------------
def annualised_return(returns):
    return (1 + returns.mean()) ** PERIODS_PER_YEAR - 1


def annualised_volatility(returns):
    return returns.std() * np.sqrt(PERIODS_PER_YEAR)


def sharpe_ratio(returns, risk_free_rate=0.02):
    vol = annualised_volatility(returns)
    if vol == 0:
        return np.nan
    return (annualised_return(returns) - risk_free_rate) / vol


def max_drawdown(returns):
    wealth = (1 + returns).cumprod()
    peak = wealth.cummax()
    drawdown = wealth / peak - 1
    return drawdown.min()


def calmar_ratio(returns):
    mdd = max_drawdown(returns)
    if mdd == 0:
        return np.nan
    return annualised_return(returns) / abs(mdd)


def summarise_performance(returns_dict, risk_free_rate=0.02):
    """Build a tidy metrics table for a dict of {name: returns Series}."""
    rows = {}
    for name, returns in returns_dict.items():
        rows[name] = {
            "Annualised Return": annualised_return(returns),
            "Annualised Volatility": annualised_volatility(returns),
            "Sharpe Ratio": sharpe_ratio(returns, risk_free_rate),
            "Maximum Drawdown": max_drawdown(returns),
            "Calmar Ratio": calmar_ratio(returns),
        }
    return pd.DataFrame(rows).T


# ------------------------------------------------------------
# Portfolio helpers
# ------------------------------------------------------------
def equal_weights(selected_assets, all_assets):
    """Equal-weight vector over the selected assets (0 elsewhere)."""
    weights = np.zeros(len(all_assets))
    if len(selected_assets) == 0:
        return weights
    w = 1.0 / len(selected_assets)
    for asset in selected_assets:
        weights[all_assets.index(asset)] = w
    return weights


def benchmark_60_40(all_assets):
    """Static 60/40: 60% SPY, 40% TLT (0 elsewhere)."""
    weights = np.zeros(len(all_assets))
    weights[all_assets.index("SPY")] = 0.60
    weights[all_assets.index("TLT")] = 0.40
    return weights


def benchmark_equal_weight(all_assets):
    """Equal weight across the full universe."""
    return np.full(len(all_assets), 1.0 / len(all_assets))
