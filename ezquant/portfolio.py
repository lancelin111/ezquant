"""
组合管理模块
============
资产配置、相关性分析、再平衡建议。

用法：
    from ezquant.portfolio import Portfolio

    port = Portfolio({"沪深300": 0.4, "中证红利": 0.3, "国债ETF": 0.3})
    port.load_data(start="2022-01-01")
    port.summary()
"""

import pandas as pd
import numpy as np
from ezquant.data import get_etfs


class Portfolio:
    """
    投资组合管理器。

    功能：
    - 加载多只ETF数据
    - 计算组合收益
    - 相关性分析
    - 再平衡建议
    - 绩效归因
    """

    def __init__(self, weights: dict):
        """
        初始化组合。

        参数：
            weights: 资产权重字典，如 {"沪深300": 0.4, "中证红利": 0.3, "国债ETF": 0.3}
                     权重之和应为1（会自动归一化）
        """
        total = sum(weights.values())
        self.weights = {k: v / total for k, v in weights.items()}
        self.prices = None
        self.monthly_ret = None
        self.portfolio_ret = None

    def load_data(self, start: str = "2020-01-01", end: str = None):
        """加载组合中所有ETF的历史数据。"""
        self.prices = get_etfs(list(self.weights.keys()), start=start, end=end)

        if self.prices.empty:
            raise ValueError("未获取到任何数据，请检查ETF名称")

        # 计算日收益率
        self.daily_ret = self.prices.pct_change().dropna()

        # 计算月收益率
        monthly = self.prices.resample("ME").last()
        self.monthly_ret = monthly.pct_change().dropna()

        # 组合日收益
        self.portfolio_ret = sum(
            self.daily_ret[name] * w
            for name, w in self.weights.items()
            if name in self.daily_ret.columns
        )

        # 组合净值
        self.nav = (1 + self.portfolio_ret).cumprod()

        return self

    def correlation(self) -> pd.DataFrame:
        """
        计算资产间的相关性矩阵（基于月收益率）。

        返回：
            相关性矩阵 DataFrame
        """
        if self.monthly_ret is None:
            raise ValueError("请先调用 load_data()")
        return self.monthly_ret.corr().round(3)

    def annual_returns(self) -> pd.DataFrame:
        """
        计算各资产的年度收益率。

        返回：
            DataFrame，行=年份，列=ETF名称
        """
        if self.prices is None:
            raise ValueError("请先调用 load_data()")

        yearly = self.prices.resample("YE").last()
        return (yearly.pct_change().dropna() * 100).round(2)

    def rebalance_suggestion(self) -> pd.DataFrame:
        """
        再平衡建议：对比目标权重和当前实际权重（按最新价格漂移后的比例）。

        返回：
            DataFrame，包含目标权重、当前权重、偏差、建议操作
        """
        if self.prices is None:
            raise ValueError("请先调用 load_data()")

        # 计算从起点到现在各资产的累计收益
        start_prices = self.prices.iloc[0]
        end_prices = self.prices.iloc[-1]
        growth = end_prices / start_prices

        # 当前实际权重（假设初始按目标权重配置）
        current_value = {name: self.weights.get(name, 0) * growth.get(name, 1)
                        for name in self.weights}
        total = sum(current_value.values())
        current_weights = {name: v / total for name, v in current_value.items()}

        rows = []
        for name in self.weights:
            target = self.weights[name]
            current = current_weights.get(name, 0)
            diff = current - target
            if diff > 0.02:
                action = f"📉 减仓 {diff*100:.1f}%"
            elif diff < -0.02:
                action = f"📈 加仓 {abs(diff)*100:.1f}%"
            else:
                action = "✅ 持有"

            rows.append({
                "ETF": name,
                "目标权重": f"{target*100:.1f}%",
                "当前权重": f"{current*100:.1f}%",
                "偏差": f"{diff*100:+.1f}%",
                "建议": action,
            })

        return pd.DataFrame(rows)

    def risk_contribution(self) -> pd.DataFrame:
        """
        风险贡献分析：各资产对组合波动率的贡献。

        返回：
            DataFrame，包含各资产的风险贡献
        """
        if self.daily_ret is None:
            raise ValueError("请先调用 load_data()")

        # 协方差矩阵（年化）
        cov = self.daily_ret.cov() * 252
        w = np.array([self.weights.get(c, 0) for c in self.daily_ret.columns])

        # 组合方差
        port_var = w @ cov.values @ w
        port_vol = np.sqrt(port_var)

        # 边际风险贡献 = (Cov × w) / σ_p
        mrc = cov.values @ w / port_vol

        # 风险贡献 = w_i × MRC_i
        rc = w * mrc
        rc_pct = rc / rc.sum() * 100

        rows = []
        for i, col in enumerate(self.daily_ret.columns):
            rows.append({
                "ETF": col,
                "权重": f"{w[i]*100:.1f}%",
                "年化波动": f"{np.sqrt(cov.iloc[i, i])*100:.1f}%",
                "风险贡献": f"{rc_pct[i]:.1f}%",
            })

        return pd.DataFrame(rows)

    def summary(self):
        """打印组合概要报告。"""
        if self.portfolio_ret is None:
            raise ValueError("请先调用 load_data()")

        nav = self.nav
        total_ret = (nav.iloc[-1] / nav.iloc[0] - 1) * 100
        days = len(nav)
        years = days / 252
        ann_ret = ((1 + total_ret / 100) ** (1 / max(years, 0.01)) - 1) * 100

        cummax = nav.cummax()
        max_dd = ((nav - cummax) / cummax).min() * 100

        vol = self.portfolio_ret.std() * np.sqrt(252) * 100
        sharpe = (self.portfolio_ret.mean() * 252 - 0.02) / (self.portfolio_ret.std() * np.sqrt(252)) if self.portfolio_ret.std() > 0 else 0

        print(f"\n{'=' * 55}")
        print(f"💼 组合概要")
        print(f"{'=' * 55}")
        print(f"  配置: {self.weights}")
        print(f"  数据区间: {self.prices.index[0].strftime('%Y-%m-%d')} ~ {self.prices.index[-1].strftime('%Y-%m-%d')}")
        print(f"  总收益率:    {total_ret:>+8.2f}%")
        print(f"  年化收益率:  {ann_ret:>+8.2f}%")
        print(f"  最大回撤:    {max_dd:>+8.2f}%")
        print(f"  年化波动率:  {vol:>8.2f}%")
        print(f"  夏普比率:    {sharpe:>8.2f}")

        print(f"\n📊 相关性矩阵:")
        print(self.correlation().to_string())

        print(f"\n📋 再平衡建议:")
        print(self.rebalance_suggestion().to_string(index=False))
        print(f"{'=' * 55}\n")
