"""
策略模块
========
包含5个经典量化策略，均为向量化实现，输入价格 Series，输出持仓信号 Series。

信号约定：
    1  = 满仓（买入/持有）
    0  = 空仓（卖出/观望）
    可用于 backtest 模块直接回测

策略列表：
    1. ma_crossover    - 均线交叉策略
    2. momentum        - 动量策略
    3. low_volatility_rotation - 低波轮动策略
    4. rsi_signal      - RSI超买超卖策略
    5. grid_trading    - 网格交易策略
"""

import pandas as pd
import numpy as np


def ma_crossover(
    close: pd.Series,
    fast: int = 10,
    slow: int = 30,
) -> pd.Series:
    """
    均线交叉策略（金叉买、死叉卖）

    原理：
        短期均线上穿长期均线 → 买入信号
        短期均线下穿长期均线 → 卖出信号

    参数：
        close: 收盘价序列
        fast:  短期均线周期，默认10日
        slow:  长期均线周期，默认30日

    返回：
        持仓信号 Series（1=持有, 0=空仓）
    """
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()

    # 短均线在长均线上方时持有
    signal = (ma_fast > ma_slow).astype(int)

    # 前 slow 个交易日无信号
    signal.iloc[:slow] = 0

    signal.name = "ma_crossover"
    return signal


def momentum(
    close: pd.Series,
    lookback: int = 20,
    hold_days: int = 5,
) -> pd.Series:
    """
    动量策略（过去N日涨则持有）

    原理：
        过去 lookback 日收益率 > 0 → 持有
        否则 → 空仓
        每 hold_days 天重新评估一次

    参数：
        close:     收盘价序列
        lookback:  回看天数，默认20日
        hold_days: 持仓评估周期，默认5日

    返回：
        持仓信号 Series（1=持有, 0=空仓）
    """
    ret = close.pct_change(lookback)

    # 在评估日决定是否持有
    signal = pd.Series(0, index=close.index)
    position = 0

    for i in range(lookback, len(close)):
        # 每 hold_days 天重新评估
        if (i - lookback) % hold_days == 0:
            position = 1 if ret.iloc[i] > 0 else 0
        signal.iloc[i] = position

    signal.name = "momentum"
    return signal


def low_volatility_rotation(
    prices: pd.DataFrame,
    lookback_months: int = 3,
    top_n: int = 3,
) -> pd.DataFrame:
    """
    低波轮动策略（选波动最低且正收益的ETF持有）

    原理：
        每月末评估：
        1. 过去N个月收益为正的ETF入围
        2. 按波动率从低到高排序
        3. 选 top_n 只等权持有
        4. 若无合格标的，全部持有现金

    参数：
        prices:          多只ETF收盘价 DataFrame（列名=ETF名称）
        lookback_months: 回看月数，默认3个月
        top_n:           持有只数，默认3只

    返回：
        DataFrame，每列为一只ETF的持仓权重（0~1之间）
    """
    # 月度重采样
    monthly = prices.resample("ME").last()
    monthly_ret = monthly.pct_change()

    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    for i in range(lookback_months, len(monthly)):
        # 当前月末日期
        month_end = monthly.index[i]
        # 回看区间收益
        period_ret = monthly.iloc[i] / monthly.iloc[i - lookback_months] - 1
        # 回看区间月度波动率
        period_vol = monthly_ret.iloc[i - lookback_months + 1 : i + 1].std()

        # 筛选：正收益
        candidates = period_ret[period_ret > 0].index.tolist()
        if not candidates:
            # 无合格标的，空仓（等价于持有现金）
            continue

        # 按波动率排序，取最低的 top_n
        vols = period_vol[candidates].sort_values()
        selected = vols.index[:top_n].tolist()

        # 等权
        w = 1.0 / len(selected)

        # 找到下一个月的交易日范围
        if i + 1 < len(monthly):
            next_month_end = monthly.index[i + 1]
            mask = (prices.index > month_end) & (prices.index <= next_month_end)
        else:
            mask = prices.index > month_end

        for etf in selected:
            weights.loc[mask, etf] = w

    return weights


def rsi_signal(
    close: pd.Series,
    period: int = 14,
    oversold: float = 30,
    overbought: float = 70,
) -> pd.Series:
    """
    RSI超买超卖策略

    原理：
        RSI < oversold  → 买入（超卖区间是买入机会）
        RSI > overbought → 卖出（超买区间应卖出）
        中间区域 → 维持上一个信号

    参数：
        close:      收盘价序列
        period:     RSI计算周期，默认14
        oversold:   超卖阈值，默认30
        overbought: 超买阈值，默认70

    返回：
        持仓信号 Series（1=持有, 0=空仓）
    """
    # 计算RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # 生成信号
    signal = pd.Series(0, index=close.index)
    position = 0

    for i in range(period, len(close)):
        r = rsi.iloc[i]
        if pd.isna(r):
            signal.iloc[i] = position
            continue
        if r < oversold:
            position = 1  # 超卖买入
        elif r > overbought:
            position = 0  # 超买卖出
        signal.iloc[i] = position

    signal.name = "rsi"
    return signal


def grid_trading(
    close: pd.Series,
    grid_pct: float = 0.03,
    n_grids: int = 5,
) -> pd.Series:
    """
    网格交易策略

    原理：
        以初始价格为中心，上下各设 n_grids 个网格。
        价格每跌一个网格 → 加一份仓位
        价格每涨一个网格 → 减一份仓位
        输出的信号为仓位比例（0 ~ 1）

    参数：
        close:    收盘价序列
        grid_pct: 单格宽度占比，默认3%
        n_grids:  上下各设几格，默认5

    返回：
        持仓信号 Series（0~1 之间的仓位比例）
    """
    # 以前20日均价作为网格中心
    base_price = close.iloc[:20].mean()

    signal = pd.Series(0.0, index=close.index)

    for i in range(len(close)):
        price = close.iloc[i]
        # 计算当前价格偏离中心多少格
        deviation = (price - base_price) / (base_price * grid_pct)
        # 偏离为负（价格在中心下方）→ 加仓；偏离为正（价格在中心上方）→ 减仓
        # 基础仓位 0.5，每偏一格调整 1/(2*n_grids)
        position = 0.5 - deviation * (0.5 / n_grids)
        # 限制在 [0, 1]
        position = max(0.0, min(1.0, position))
        signal.iloc[i] = position

    signal.name = "grid"
    return signal


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    计算RSI指标（辅助函数，可单独使用）。

    参数：
        close:  收盘价序列
        period: RSI周期，默认14

    返回：
        RSI 序列
    """
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi.name = "RSI"
    return rsi
