#!/usr/bin/env python3
"""
组合优化示例
============
构建多资产组合，分析相关性，给出再平衡建议。

运行：
    cd ezquant
    python examples/portfolio_optimization.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ezquant.portfolio import Portfolio
import matplotlib
matplotlib.use("Agg")


def main():
    print("💼 组合优化示例")
    print("=" * 55)

    # ===== 组合1：保守型 =====
    print("\n📦 组合1：保守型（60%债券 + 20%红利 + 20%黄金）")
    port1 = Portfolio({
        "国债ETF": 0.6,
        "中证红利": 0.2,
        "黄金ETF": 0.2,
    })
    port1.load_data(start="2022-01-01")
    port1.summary()

    # ===== 组合2：均衡型 =====
    print("\n📦 组合2：均衡型（30%债券 + 30%红利 + 20%宽基 + 20%黄金）")
    port2 = Portfolio({
        "国债ETF": 0.3,
        "中证红利": 0.3,
        "沪深300": 0.2,
        "黄金ETF": 0.2,
    })
    port2.load_data(start="2022-01-01")
    port2.summary()

    # ===== 组合3：进取型 =====
    print("\n📦 组合3：进取型（40%宽基 + 30%红利 + 20%纳指 + 10%黄金）")
    port3 = Portfolio({
        "沪深300": 0.4,
        "中证红利": 0.3,
        "纳指ETF": 0.2,
        "黄金ETF": 0.1,
    })
    port3.load_data(start="2022-01-01")
    port3.summary()

    # ===== 风险贡献分析 =====
    print("\n📊 均衡组合风险贡献分析:")
    print(port2.risk_contribution().to_string(index=False))

    # ===== 年度收益 =====
    print("\n📅 均衡组合年度成分收益:")
    annual = port2.annual_returns()
    if not annual.empty:
        print(annual.to_string())

    # ===== 保存图表 =====
    try:
        from ezquant.plot import plot_allocation, plot_correlation, plot_multi_nav
        os.makedirs("output", exist_ok=True)

        plot_allocation(
            port2.weights,
            title="均衡组合资产配置",
            save_path="output/portfolio_allocation.png",
        )

        plot_correlation(
            port2.correlation(),
            title="均衡组合相关性热力图",
            save_path="output/portfolio_correlation.png",
        )

        plot_multi_nav(
            {
                "保守型": port1.nav,
                "均衡型": port2.nav,
                "进取型": port3.nav,
            },
            title="三种组合对比",
            save_path="output/portfolio_comparison.png",
        )
    except Exception as e:
        print(f"\n   图表生成跳过: {e}")

    print("\n✅ 组合优化演示完成！")
    print("   提示：可以自行修改权重，找到适合自己的配置")


if __name__ == "__main__":
    main()
