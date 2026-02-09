"""
信号生成模块
============
每日生成ETF买卖信号，整合多个策略的综合判断。

用法：
    from ezquant.signal import generate_signals

    report = generate_signals()
    print(report)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from ezquant.data import get_etfs, ETF_POOL
from ezquant.strategy import compute_rsi


# 默认分析的ETF列表
DEFAULT_ETFS = [
    "中证红利", "红利低波", "国债ETF", "十年国债",
    "黄金ETF", "沪深300", "中证500", "医药ETF",
    "恒生ETF", "纳指ETF",
]


def generate_signals(
    etf_names: list = None,
    start: str = "2024-01-01",
) -> str:
    """
    生成每日ETF信号分析报告。

    参数：
        etf_names: 要分析的ETF列表，默认使用内置池
        start:     数据起始日期

    返回：
        格式化的文本报告
    """
    if etf_names is None:
        etf_names = DEFAULT_ETFS

    # 获取数据
    prices = get_etfs(etf_names, start=start)
    if prices.empty or len(prices) < 20:
        return "⚠️ 数据不足，无法生成信号"

    today = datetime.now().strftime("%Y-%m-%d")
    report = []
    report.append(f"📊 每日ETF信号分析 ({today})")
    report.append("=" * 55)

    # ===== 1. 低波轮动信号 =====
    report.append(_low_vol_signal(prices))

    # ===== 2. 技术面快照 =====
    report.append(_tech_snapshot(prices))

    # ===== 3. 异常提醒 =====
    report.append(_alerts(prices))

    # ===== 4. 操作建议 =====
    report.append(_suggestion())

    return "\n".join(report)


def get_signal_table(
    etf_names: list = None,
    start: str = "2024-01-01",
) -> pd.DataFrame:
    """
    返回结构化的信号表（适合程序化使用）。

    返回：
        DataFrame，每行为一只ETF，列包含价格、涨跌、均线位置、RSI、信号
    """
    if etf_names is None:
        etf_names = DEFAULT_ETFS

    prices = get_etfs(etf_names, start=start)
    if prices.empty or len(prices) < 20:
        return pd.DataFrame()

    rows = []
    for name in prices.columns:
        c = prices[name].dropna()
        if len(c) < 20:
            continue

        cur = c.iloc[-1]
        d1 = (c.iloc[-1] / c.iloc[-2] - 1) * 100 if len(c) > 1 else 0
        d5 = (c.iloc[-1] / c.iloc[-5] - 1) * 100 if len(c) > 5 else 0
        d20 = (c.iloc[-1] / c.iloc[-20] - 1) * 100 if len(c) > 20 else 0

        # 20日均线
        ma20 = c.rolling(20).mean().iloc[-1]
        vs_ma20 = (cur / ma20 - 1) * 100

        # RSI
        rsi = compute_rsi(c, 14).iloc[-1]

        # 信号判断
        signal = "观望"
        if rsi < 30:
            signal = "超卖-考虑买入"
        elif rsi > 70:
            signal = "超买-考虑卖出"
        elif vs_ma20 > 0 and d5 > 0:
            signal = "趋势向好"
        elif vs_ma20 < -3:
            signal = "破位-谨慎"

        rows.append({
            "ETF": name,
            "价格": round(cur, 3),
            "日涨跌%": round(d1, 2),
            "5日%": round(d5, 2),
            "20日%": round(d20, 2),
            "vs20均线%": round(vs_ma20, 2),
            "RSI": round(rsi, 1),
            "信号": signal,
        })

    return pd.DataFrame(rows)


# ==================== 内部函数 ====================

def _low_vol_signal(prices: pd.DataFrame) -> str:
    """低波轮动信号"""
    lines = []
    monthly = prices.resample("ME").last()
    monthly_ret = monthly.pct_change()

    if len(monthly) >= 4:
        vols = {}
        for col in prices.columns:
            rets = monthly_ret[col].iloc[-3:]
            rets = rets.dropna()
            if len(rets) < 2:
                continue
            ret_3m = monthly[col].iloc[-1] / monthly[col].iloc[-3] - 1 if pd.notna(monthly[col].iloc[-3]) else -1
            if ret_3m > 0:
                vols[col] = rets.std()

        if vols:
            ranked = sorted(vols.items(), key=lambda x: x[1])[:3]
            lines.append(f"\n🎯 低波轮动信号（本月建议持有）:")
            for name, vol in ranked:
                ret_3m = (monthly[name].iloc[-1] / monthly[name].iloc[-3] - 1) * 100
                lines.append(f"  ✅ {name} (3月涨{ret_3m:+.1f}%, 波动{vol*100:.2f}%)")
        else:
            lines.append(f"\n🎯 低波轮动: 全部不满足条件 → 建议持有国债ETF")
    else:
        lines.append(f"\n🎯 低波轮动: 数据不足")

    return "\n".join(lines)


def _tech_snapshot(prices: pd.DataFrame) -> str:
    """技术面快照"""
    lines = []
    lines.append(f"\n📈 各ETF技术面:")
    lines.append(f"{'名称':<10} {'价格':>8} {'日涨跌':>7} {'5日':>7} {'20日':>7} {'vs20均':>7} {'RSI':>5}")
    lines.append("-" * 58)

    for name in prices.columns:
        c = prices[name].dropna()
        if len(c) < 20:
            continue

        cur = c.iloc[-1]
        d1 = (c.iloc[-1] / c.iloc[-2] - 1) * 100 if len(c) > 1 else 0
        d5 = (c.iloc[-1] / c.iloc[-5] - 1) * 100 if len(c) > 5 else 0
        d20 = (c.iloc[-1] / c.iloc[-20] - 1) * 100 if len(c) > 20 else 0
        ma20 = c.rolling(20).mean().iloc[-1]
        vs_ma = (cur / ma20 - 1) * 100
        rsi = compute_rsi(c, 14).iloc[-1]

        signal = ""
        if rsi < 30:
            signal = "⬇️超卖"
        elif rsi > 70:
            signal = "⬆️超买"
        if vs_ma < -5:
            signal += "📉破位"

        lines.append(
            f"{name:<8} {cur:>8.3f} {d1:>+6.1f}% {d5:>+6.1f}% "
            f"{d20:>+6.1f}% {vs_ma:>+6.1f}% {rsi:>4.0f} {signal}"
        )

    return "\n".join(lines)


def _alerts(prices: pd.DataFrame) -> str:
    """异常提醒"""
    alerts = []

    for name in prices.columns:
        c = prices[name].dropna()
        if len(c) < 2:
            continue
        d1 = (c.iloc[-1] / c.iloc[-2] - 1) * 100
        if abs(d1) > 3:
            direction = "暴涨" if d1 > 0 else "暴跌"
            alerts.append(f"  🚨 {name} {direction} {d1:+.1f}%")

    for name in prices.columns:
        c = prices[name].dropna()
        if len(c) < 15:
            continue
        rsi = compute_rsi(c, 14).iloc[-1]
        if rsi < 25:
            alerts.append(f"  📉 {name} RSI={rsi:.0f} 严重超卖，可能是买入机会")
        elif rsi > 80:
            alerts.append(f"  📈 {name} RSI={rsi:.0f} 严重超买，注意风险")

    if alerts:
        return "\n🚨 异常提醒:\n" + "\n".join(alerts)
    else:
        return "\n✅ 无异常，市场平稳"


def _suggestion() -> str:
    """操作建议"""
    lines = ["\n💡 今日建议:"]
    now = datetime.now()
    if now.day <= 3:
        lines.append("  📋 月初调仓窗口！请对照上方轮动信号执行")
    else:
        lines.append("  ⏳ 非调仓期，持仓不动")
    return "\n".join(lines)
