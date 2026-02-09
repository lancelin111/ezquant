"""
可视化模块
==========
收益曲线、回撤图、持仓分布饼图。

用法：
    from ezquant.plot import plot_returns, plot_drawdown, plot_allocation

    # 画收益曲线
    plot_returns(result["nav"], result["benchmark_nav"], title="均线策略")

    # 画回撤图
    plot_drawdown(result["nav"])

    # 画持仓分布
    plot_allocation({"沪深300": 0.4, "中证红利": 0.3, "国债ETF": 0.3})
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# 支持中文显示
matplotlib.rcParams["font.sans-serif"] = ["Arial Unicode MS", "SimHei", "PingFang SC", "Microsoft YaHei"]
matplotlib.rcParams["axes.unicode_minus"] = False


def plot_returns(
    nav: pd.Series,
    benchmark_nav: pd.Series = None,
    title: str = "策略收益曲线",
    figsize: tuple = (12, 6),
    save_path: str = None,
):
    """
    绘制收益曲线。

    参数：
        nav:           策略净值序列
        benchmark_nav: 基准净值序列（可选）
        title:         图表标题
        figsize:       图表大小
        save_path:     保存路径（None则显示）
    """
    fig, ax = plt.subplots(figsize=figsize)

    # 归一化为百分比收益
    strat_ret = (nav / nav.iloc[0] - 1) * 100
    ax.plot(strat_ret.index, strat_ret.values, label="策略", color="#e74c3c", linewidth=2)

    if benchmark_nav is not None:
        bench_ret = (benchmark_nav / benchmark_nav.iloc[0] - 1) * 100
        ax.plot(bench_ret.index, bench_ret.values, label="基准(买入持有)",
                color="#95a5a6", linewidth=1.5, linestyle="--")

    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_ylabel("收益率 (%)")
    ax.set_xlabel("日期")
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linewidth=0.5)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"📊 图表已保存: {save_path}")
    else:
        plt.show()

    plt.close(fig)


def plot_drawdown(
    nav: pd.Series,
    title: str = "回撤曲线",
    figsize: tuple = (12, 4),
    save_path: str = None,
):
    """
    绘制回撤曲线。

    参数：
        nav:       净值序列
        title:     图表标题
        figsize:   图表大小
        save_path: 保存路径（None则显示）
    """
    fig, ax = plt.subplots(figsize=figsize)

    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax * 100

    ax.fill_between(drawdown.index, drawdown.values, 0, color="#e74c3c", alpha=0.3)
    ax.plot(drawdown.index, drawdown.values, color="#e74c3c", linewidth=1)

    max_dd = drawdown.min()
    max_dd_date = drawdown.idxmin()
    ax.annotate(
        f"最大回撤: {max_dd:.1f}%",
        xy=(max_dd_date, max_dd),
        xytext=(30, -20),
        textcoords="offset points",
        fontsize=11,
        arrowprops=dict(arrowstyle="->", color="#c0392b"),
        color="#c0392b",
        fontweight="bold",
    )

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("回撤 (%)")
    ax.set_xlabel("日期")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"📊 图表已保存: {save_path}")
    else:
        plt.show()

    plt.close(fig)


def plot_allocation(
    weights: dict,
    title: str = "资产配置",
    figsize: tuple = (8, 8),
    save_path: str = None,
):
    """
    绘制持仓分布饼图。

    参数：
        weights:   资产权重字典，如 {"沪深300": 0.4, "国债ETF": 0.3, ...}
        title:     图表标题
        figsize:   图表大小
        save_path: 保存路径（None则显示）
    """
    fig, ax = plt.subplots(figsize=figsize)

    labels = list(weights.keys())
    values = list(weights.values())

    # 配色方案
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
              "#1abc9c", "#e67e22", "#34495e", "#16a085", "#c0392b"]

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        colors=colors[: len(labels)],
        startangle=90,
        textprops={"fontsize": 12},
    )

    for autotext in autotexts:
        autotext.set_fontsize(11)
        autotext.set_fontweight("bold")

    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"📊 图表已保存: {save_path}")
    else:
        plt.show()

    plt.close(fig)


def plot_multi_nav(
    navs: dict,
    title: str = "策略对比",
    figsize: tuple = (12, 6),
    save_path: str = None,
):
    """
    绘制多条净值曲线对比图。

    参数：
        navs:      字典 {策略名: 净值Series}
        title:     图表标题
        figsize:   图表大小
        save_path: 保存路径
    """
    fig, ax = plt.subplots(figsize=figsize)

    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
              "#1abc9c", "#e67e22", "#34495e"]

    for i, (name, nav) in enumerate(navs.items()):
        ret = (nav / nav.iloc[0] - 1) * 100
        ax.plot(ret.index, ret.values, label=name,
                color=colors[i % len(colors)], linewidth=2)

    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_ylabel("收益率 (%)")
    ax.set_xlabel("日期")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linewidth=0.5)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"📊 图表已保存: {save_path}")
    else:
        plt.show()

    plt.close(fig)


def plot_correlation(
    corr: pd.DataFrame,
    title: str = "资产相关性热力图",
    figsize: tuple = (10, 8),
    save_path: str = None,
):
    """
    绘制相关性热力图。

    参数：
        corr:      相关性矩阵 DataFrame
        title:     图表标题
        figsize:   图表大小
        save_path: 保存路径
    """
    fig, ax = plt.subplots(figsize=figsize)

    im = ax.imshow(corr.values, cmap="RdYlGn_r", vmin=-1, vmax=1, aspect="auto")

    # 标注
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=10)
    ax.set_yticklabels(corr.index, fontsize=10)

    # 在每个格子里写数值
    for i in range(len(corr)):
        for j in range(len(corr)):
            val = corr.iloc[i, j]
            color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    color=color, fontsize=10, fontweight="bold")

    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"📊 图表已保存: {save_path}")
    else:
        plt.show()

    plt.close(fig)
