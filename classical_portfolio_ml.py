# ============================================================
# Classical Machine-Learning Portfolio (the quantum challenger)
# ============================================================
#
# This is the classical baseline that competes head-to-head with the
# QAOA quantum optimiser. Instead of solving a combinatorial QUBO, it
# *predicts* each asset's next-month return with a Random Forest and
# then holds the B assets with the highest predicted return.
#
# To keep the comparison fair, everything except the selection logic is
# identical to the quantum strategy:
#   * same 8-asset universe and monthly data
#   * same trailing look-back window
#   * same "hold exactly B assets, equal-weighted" rule
#
# So the experiment isolates one question: does a quantum optimiser or a
# classical ML predictor build the better portfolio?

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

import portfolio_utils as pu


# ------------------------------------------------------------
# Feature engineering
# ------------------------------------------------------------
def build_feature_panel(monthly_returns):
    """Long-format panel of momentum / volatility features per (asset, month).

    Every feature uses only information available at the end of month t;
    the target is the return of month t+1, so there is no look-ahead.
    """
    frames = []
    for asset in monthly_returns.columns:
        s = monthly_returns[asset]
        df = pd.DataFrame(index=monthly_returns.index)
        df["r_lag1"] = s                 # this month's realised return
        df["r_lag2"] = s.shift(1)
        df["r_lag3"] = s.shift(2)
        df["mom_3"] = s.rolling(3).sum()
        df["mom_6"] = s.rolling(6).sum()
        df["mom_12"] = s.rolling(12).sum()
        df["vol_6"] = s.rolling(6).std()
        df["target"] = s.shift(-1)       # next month's return (label)
        df["asset"] = asset
        df["month"] = monthly_returns.index
        frames.append(df)

    panel = pd.concat(frames, ignore_index=True)
    return panel


FEATURE_COLS = ["r_lag1", "r_lag2", "r_lag3", "mom_3", "mom_6", "mom_12", "vol_6"]


# ------------------------------------------------------------
# One-step prediction + selection
# ------------------------------------------------------------
def select_assets_ml(panel, assets, decision_month, train_months, budget, seed):
    """Train a Random Forest on the trailing window and pick the top-B assets
    by predicted next-month return. Returns (selected, predictions)."""
    train = panel[panel["month"].isin(train_months)].dropna(subset=FEATURE_COLS + ["target"])

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=4,
        min_samples_leaf=5,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(train[FEATURE_COLS], train["target"])

    today = panel[(panel["month"] == decision_month)].dropna(subset=FEATURE_COLS)
    preds = pd.Series(
        model.predict(today[FEATURE_COLS]),
        index=today["asset"].values,
    )

    # rank all assets, hold the best `budget`
    ranked = preds.reindex(assets).fillna(-np.inf).sort_values(ascending=False)
    selected = list(ranked.index[:budget])
    return selected, preds


# ------------------------------------------------------------
# Walk-forward backtest (mirrors quantum_portfolio_qaoa)
# ------------------------------------------------------------
def run_classical_ml_backtest(monthly_returns, budget=4, lookback=36,
                              rebalance=3, seed=42, verbose=False):
    assets = list(monthly_returns.columns)
    panel = build_feature_panel(monthly_returns)
    months = monthly_returns.index

    strategy_returns = []
    selections = []
    dates = []

    pred_record = []   # (predicted, actual) pairs for OOS accuracy metrics
    current_selection = None

    for i in range(lookback, len(monthly_returns) - 1):
        if current_selection is None or (i - lookback) % rebalance == 0:
            train_months = months[i - lookback:i]
            current_selection, preds = select_assets_ml(
                panel, assets, months[i], train_months, budget, seed,
            )
            if verbose:
                print(f"{months[i].date()}  ->  {current_selection}")

            actual_next = monthly_returns.iloc[i + 1]
            for asset in assets:
                if asset in preds.index:
                    pred_record.append((preds[asset], actual_next[asset]))

        weights = pu.equal_weights(current_selection, assets)
        next_month = monthly_returns.iloc[i + 1]

        strategy_returns.append(float(next_month.values @ weights))
        selections.append(tuple(current_selection))
        dates.append(months[i + 1])

    strategy_returns = pd.Series(strategy_returns, index=dates,
                                 name="ML_Classical")

    pred_arr = np.array(pred_record)
    rmse = float(np.sqrt(np.mean((pred_arr[:, 0] - pred_arr[:, 1]) ** 2)))
    directional = float(np.mean(np.sign(pred_arr[:, 0]) == np.sign(pred_arr[:, 1])))

    diagnostics = {
        "model": "RandomForestRegressor(n=200, depth=4)",
        "features": FEATURE_COLS,
        "prediction_rmse": rmse,
        "directional_accuracy": directional,
        "n_predictions": len(pred_record),
    }

    return {
        "strategy_returns": strategy_returns,
        "selections": selections,
        "diagnostics": diagnostics,
    }


# ------------------------------------------------------------
# Stand-alone demo
# ------------------------------------------------------------
if __name__ == "__main__":
    returns = pu.download_monthly_returns()
    print(f"Loaded {returns.shape[0]} months x {returns.shape[1]} assets\n")

    result = run_classical_ml_backtest(returns, verbose=True)

    perf = pu.summarise_performance({
        "Classical ML": result["strategy_returns"],
    })
    print("\nPerformance:")
    print(perf.round(4).to_string())

    print("\nML model diagnostics:")
    for k, v in result["diagnostics"].items():
        print(f"  {k}: {v}")
