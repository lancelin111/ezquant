#!/usr/bin/env python3
"""
ETF轮动策略示例
================
低波轮动：每月从ETF池中挑选近期正收益、波动最低的3只等权持有。

运行：
    cd ezquant
    python examples/etf_rotation.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from ezquant.data import get_etfs
from ezquant.strategy import low_volatility_rotation
import matplotlib
matplotlib.use("Agg")


def main():
    print("🔄 ETF低波轮动策略")
    print("=" * 55)

    # 定义ETF池
    etf_names = ["沪深300", "中证红利", "国债ETF", "黄金ETF", "纳指ETF", "中证500"]

    # 获取数据
    print(f"\n📥 获取 {len(etf_names)} 只ETF数据...")
    prices = get_etfs(etf_names, start="2022-01-01")
    print(f"   数据范围: {prices.index[0].strftime('%Y-%m-%d')} ~ {prices.index[-1].strftime('%Y-%m-%d')}")
    print(f"   交易日数: {len(prices)}")

    # 生成轮动权重
    print(f"\n📊 运行低波轮动策略 (回看3个月, 选3只)...")
    weights = low_volatility_rotation(prices, lookback_months=3, top_n=3)

    # 展示最近的持仓
    print(f"\n🎯 最近一期持仓:")
    latest_weights = weights.iloc[-1]
    for name, w in latest_weights.items():
        if w > 0:
            print(f"   {name}: {w*100:.1f}%")

    # 回测：计算组合收益
    daily_ret = prices.pct_change().fillna(0)
    # 策略收益 = 各ETF收益 × 权重
    strategy_ret = (daily_ret * weights.shift(1).fillna(0)).sum(axis=1)
    strategy_nav = (1 + strategy_ret).cumprod()

    # 基准：等权买入持有
    equal_weight = 1.0 / len(prices.columns)
    benchmark_ret = daily_ret.mean(axis=1)
    benchmark_nav = (1 + benchmark_ret).cumprod()

    # 绩效统计
    years = len(strategy_nav) / 252
    total_ret = (strategy_nav.iloc[-1] - 1) * 100
    ann_ret = ((strategy_nav.iloc[-1]) ** (1 / max(years, 0.01)) - 1) * 100
    cummax = strategy_nav.cummax()
    max_dd = ((strategy_nav - cummax) / cummax).min() * 100
    vol = strategy_ret.std() * np.sqrt(252) * 100
    sharpe = (strategy_ret.mean() * 252 - 0.02) / (strategy_ret.std() * np.sqrt(252)) if strategy_ret.std() > 0 else 0

    bench_total = (benchmark_nav.iloc[-1] - 1) * 100

    print(f"\n📈 回测结果:")
    print(f"{'=' * 50}")
    print(f"  总收益率:      {total_ret:>+8.2f}%")
    print(f"  年化收益率:    {ann_ret:>+8.2f}%")
    print(f"  最大回撤:      {max_dd:>+8.2f}%")
    print(f"  年化波动率:    {vol:>8.2f}%")
    print(f"  夏普比率:      {sharpe:>8.2f}")
    print(f"  基准收益:      {bench_total:>+8.2f}% (等权买入持有)")
    print(f"  超额收益:      {total_ret - bench_total:>+8.2f}%")
    print(f"{'=' * 50}")

    # 月度持仓变化
    print(f"\n📅 月度持仓变化（最近6个月）:")
    monthly_weights = weights.resample("ME").last().tail(6)
    for date, row in monthly_weights.iterrows():
        holdings = [f"{name}({w*100:.0f}%)" for name, w in row.items() if w > 0]
        if holdings:
            print(f"   {date.strftime('%Y-%m')}: {', '.join(holdings)}")
        else:
            print(f"   {date.strftime('%Y-%m')}: 空仓(持有现金)")

    # 保存图表
    try:
        from ezquant.plot import plot_multi_nav
        os.makedirs("output", exist_ok=True)

        navs = {"低波轮动": strategy_nav, "等权买入持有": benchmark_nav}
        # 添加各成分ETF的归一化走势
        for col in prices.columns:
            navs[col] = prices[col] / prices[col].iloc[0]

        plot_multi_nav(
            navs,
            title="低波轮动 vs 买入持有 vs 成分ETF",
            save_path="output/etf_rotation.png",
        )
    except Exception as e:
        print(f"\n   图表生成跳过: {e}")

    print(f"\n✅ ETF轮动策略演示完成！")


if __name__ == "__main__":
    main()
