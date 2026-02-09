"""
回测引擎
========
简单的向量化回测，输入价格和信号，输出绩效指标。

用法：
    from ezquant import backtest, calc_metrics

    result = backtest(close, signal)
    print(result)
    # {'total_return': 35.2, 'annual_return': 12.1, 'max_drawdown': -8.5, ...}
"""

import pandas as pd
import numpy as np


def backtest(
    close: pd.Series,
    signal: pd.Series,
    commission: float = 0.001,
    initial_capital: float = 100000,
    slippage: float = 0.0005,
) -> dict:
    """
    向量化回测引擎。

    参数：
        close:           收盘价序列（DatetimeIndex）
        signal:          持仓信号序列（0~1，与 close 同索引）
        commission:      单边手续费率，默认 0.1%
        initial_capital: 初始资金，默认 10万
        slippage:        滑点，默认 0.05%

    返回：
        dict，包含所有绩效指标和净值曲线
    """
    # 对齐索引
    close = close.dropna()
    signal = signal.reindex(close.index).fillna(0)

    # 每日收益率
    daily_ret = close.pct_change().fillna(0)

    # 计算换手（信号变化时产生交易成本）
    turnover = signal.diff().abs().fillna(0)
    # 交易成本 = 换手 × (手续费 + 滑点)
    cost = turnover * (commission + slippage)

    # 策略每日收益 = 持仓比例 × 标的收益 - 交易成本
    strategy_ret = signal.shift(1).fillna(0) * daily_ret - cost

    # 净值曲线
    nav = (1 + strategy_ret).cumprod() * initial_capital

    # 基准净值（买入持有）
    benchmark_nav = (1 + daily_ret).cumprod() * initial_capital

    # 计算指标
    metrics = calc_metrics(nav, benchmark_nav)

    # 附加详细数据
    metrics["nav"] = nav
    metrics["benchmark_nav"] = benchmark_nav
    metrics["daily_return"] = strategy_ret
    metrics["signal"] = signal
    metrics["initial_capital"] = initial_capital
    metrics["trades"] = int(turnover[turnover > 0].count())

    return metrics


def calc_metrics(nav: pd.Series, benchmark_nav: pd.Series = None) -> dict:
    """
    根据净值序列计算绩效指标。

    参数：
        nav:           策略净值序列
        benchmark_nav: 基准净值序列（可选）

    返回：
        dict，包含：
        - total_return:  总收益率 (%)
        - annual_return: 年化收益率 (%)
        - max_drawdown:  最大回撤 (%)
        - sharpe_ratio:  夏普比率（无风险利率按2%计算）
        - calmar_ratio:  Calmar比率
        - volatility:    年化波动率 (%)
        - win_rate:      日胜率 (%)
        - profit_loss_ratio: 盈亏比
    """
    returns = nav.pct_change().dropna()
    days = len(nav)

    # 总收益率
    total_return = (nav.iloc[-1] / nav.iloc[0] - 1) * 100

    # 年化收益率
    years = days / 252
    annual_return = ((1 + total_return / 100) ** (1 / max(years, 0.01)) - 1) * 100

    # 最大回撤
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax
    max_drawdown = drawdown.min() * 100

    # 年化波动率
    volatility = returns.std() * np.sqrt(252) * 100

    # 夏普比率（无风险利率2%）
    risk_free_daily = 0.02 / 252
    excess_returns = returns - risk_free_daily
    sharpe = (
        (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
        if excess_returns.std() > 0
        else 0
    )

    # Calmar比率
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # 日胜率
    win_rate = (returns > 0).mean() * 100

    # 盈亏比
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    profit_loss_ratio = (
        abs(wins.mean() / losses.mean()) if len(losses) > 0 and losses.mean() != 0 else 0
    )

    result = {
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "calmar_ratio": round(calmar, 2),
        "volatility": round(volatility, 2),
        "win_rate": round(win_rate, 1),
        "profit_loss_ratio": round(profit_loss_ratio, 2),
        "trade_days": days,
    }

    # 基准对比
    if benchmark_nav is not None:
        bench_ret = (benchmark_nav.iloc[-1] / benchmark_nav.iloc[0] - 1) * 100
        excess = total_return - bench_ret
        result["benchmark_return"] = round(bench_ret, 2)
        result["excess_return"] = round(excess, 2)

    return result


def compare_strategies(close: pd.Series, strategies: dict, **kwargs) -> pd.DataFrame:
    """
    对比多个策略的回测结果。

    参数：
        close:      收盘价序列
        strategies: 字典，{策略名: 信号Series}
        **kwargs:   传递给 backtest 的其他参数

    返回：
        DataFrame，每行为一个策略的绩效指标
    """
    results = []
    for name, signal in strategies.items():
        metrics = backtest(close, signal, **kwargs)
        row = {k: v for k, v in metrics.items() if not isinstance(v, pd.Series)}
        row["strategy"] = name
        results.append(row)

    df = pd.DataFrame(results).set_index("strategy")
    # 去掉不需要显示的列
    drop_cols = [c for c in df.columns if c in ("nav", "benchmark_nav", "daily_return", "signal")]
    df = df.drop(columns=drop_cols, errors="ignore")
    return df


def print_result(result: dict, name: str = "策略"):
    """
    美观打印回测结果。

    参数：
        result: backtest() 返回的字典
        name:   策略名称
    """
    print(f"\n{'=' * 50}")
    print(f"📊 {name} 回测报告")
    print(f"{'=' * 50}")
    print(f"  总收益率:      {result['total_return']:>+8.2f}%")
    print(f"  年化收益率:    {result['annual_return']:>+8.2f}%")
    print(f"  最大回撤:      {result['max_drawdown']:>+8.2f}%")
    print(f"  夏普比率:      {result['sharpe_ratio']:>8.2f}")
    print(f"  Calmar比率:    {result['calmar_ratio']:>8.2f}")
    print(f"  年化波动率:    {result['volatility']:>8.2f}%")
    print(f"  日胜率:        {result['win_rate']:>8.1f}%")
    print(f"  盈亏比:        {result['profit_loss_ratio']:>8.2f}")
    print(f"  交易天数:      {result['trade_days']:>8d}")
    if "trades" in result:
        print(f"  交易次数:      {result['trades']:>8d}")
    if "benchmark_return" in result:
        print(f"  基准收益:      {result['benchmark_return']:>+8.2f}%")
        print(f"  超额收益:      {result['excess_return']:>+8.2f}%")
    print(f"{'=' * 50}\n")
