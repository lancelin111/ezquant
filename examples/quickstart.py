#!/usr/bin/env python3
"""
ezquant 快速体验
================
5分钟跑通量化投资全流程：获取数据 → 生成策略信号 → 回测 → 查看结果

运行：
    cd ezquant
    python examples/quickstart.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ezquant.data import get_etf, get_etfs
from ezquant.strategy import ma_crossover, rsi_signal, momentum
from ezquant.backtest import backtest, print_result, compare_strategies
import matplotlib
matplotlib.use("Agg")  # 非交互模式，适合无GUI环境

def main():
    print("🚀 ezquant 快速体验")
    print("=" * 55)

    # ===== 第1步：获取数据 =====
    print("\n📥 第1步：获取沪深300ETF数据...")
    close = get_etf("沪深300", start="2022-01-01")["Close"]
    print(f"   获取到 {len(close)} 个交易日数据")
    print(f"   时间范围: {close.index[0].strftime('%Y-%m-%d')} ~ {close.index[-1].strftime('%Y-%m-%d')}")
    print(f"   最新价格: {close.iloc[-1]:.3f}")

    # ===== 第2步：生成策略信号 =====
    print("\n📊 第2步：生成策略信号...")

    # 均线交叉策略
    signal_ma = ma_crossover(close, fast=10, slow=30)
    print(f"   均线交叉(10/30): 当前{'持有' if signal_ma.iloc[-1] == 1 else '空仓'}")

    # RSI策略
    signal_rsi = rsi_signal(close, period=14, oversold=30, overbought=70)
    print(f"   RSI(14): 当前{'持有' if signal_rsi.iloc[-1] == 1 else '空仓'}")

    # 动量策略
    signal_mom = momentum(close, lookback=20, hold_days=5)
    print(f"   动量(20日): 当前{'持有' if signal_mom.iloc[-1] == 1 else '空仓'}")

    # ===== 第3步：回测 =====
    print("\n📈 第3步：回测各策略...")

    result_ma = backtest(close, signal_ma)
    print_result(result_ma, "均线交叉(10/30)")

    result_rsi = backtest(close, signal_rsi)
    print_result(result_rsi, "RSI超买超卖(14)")

    result_mom = backtest(close, signal_mom)
    print_result(result_mom, "动量策略(20日)")

    # ===== 第4步：策略对比 =====
    print("\n🏆 第4步：策略对比")
    comparison = compare_strategies(close, {
        "均线交叉": signal_ma,
        "RSI": signal_rsi,
        "动量": signal_mom,
    })
    print(comparison.to_string())

    # ===== 第5步：保存图表 =====
    print("\n🎨 第5步：生成图表...")
    try:
        from ezquant.plot import plot_returns, plot_drawdown, plot_multi_nav

        os.makedirs("output", exist_ok=True)

        plot_returns(
            result_ma["nav"],
            result_ma["benchmark_nav"],
            title="均线交叉策略 vs 买入持有",
            save_path="output/quickstart_returns.png",
        )

        plot_drawdown(
            result_ma["nav"],
            title="均线交叉策略回撤",
            save_path="output/quickstart_drawdown.png",
        )

        plot_multi_nav(
            {
                "均线交叉": result_ma["nav"],
                "RSI": result_rsi["nav"],
                "动量": result_mom["nav"],
                "买入持有": result_ma["benchmark_nav"],
            },
            title="策略对比 - 沪深300ETF",
            save_path="output/quickstart_comparison.png",
        )
        print("   图表已保存到 output/ 目录")
    except Exception as e:
        print(f"   图表生成跳过: {e}")

    print("\n✅ 快速体验完成！")
    print("   下一步可以尝试：")
    print("   - 修改策略参数（均线周期、RSI阈值等）")
    print("   - 换其他ETF（中证红利、黄金ETF等）")
    print("   - 运行 examples/etf_rotation.py 体验轮动策略")
    print("   - 运行 examples/portfolio_optimization.py 体验组合优化")


if __name__ == "__main__":
    main()
