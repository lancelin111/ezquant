"""
ezquant - A股小白量化入门工具包
================================

简单易用的A股量化投资工具，5分钟上手。

主要模块：
- data: 数据获取（基于yfinance）
- strategy: 经典量化策略（均线交叉、动量、低波轮动、RSI、网格）
- backtest: 向量化回测引擎
- portfolio: 组合管理与资产配置
- signal: 每日买卖信号生成
- plot: 可视化（收益曲线、回撤图、持仓饼图）
"""

__version__ = "0.1.0"
__author__ = ""

from ezquant.data import get_etf, get_etfs, ETF_POOL
from ezquant.strategy import (
    ma_crossover,
    momentum,
    low_volatility_rotation,
    rsi_signal,
    grid_trading,
)
from ezquant.backtest import backtest, calc_metrics
from ezquant.portfolio import Portfolio
from ezquant.signal import generate_signals
from ezquant.plot import plot_returns, plot_drawdown, plot_allocation
