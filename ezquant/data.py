"""
数据获取模块
============
基于 yfinance 获取A股ETF行情数据。

用法：
    from ezquant.data import get_etf, get_etfs, ETF_POOL

    # 获取单只ETF
    df = get_etf("沪深300")

    # 批量获取多只ETF收盘价
    prices = get_etfs(["沪深300", "中证红利", "黄金ETF"])
"""

import pandas as pd
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

# ==================== 常用A股ETF池 ====================
# 键为中文简称，值为yfinance代码（.SS=上交所，.SZ=深交所）
ETF_POOL = {
    # 红利类
    "中证红利": "515080.SS",
    "红利低波": "512890.SS",
    "红利ETF": "510880.SS",
    # 债券类
    "国债ETF": "511010.SS",
    "十年国债": "511260.SS",
    # 商品
    "黄金ETF": "518880.SS",
    # 宽基指数
    "沪深300": "510300.SS",
    "中证500": "510500.SS",
    "上证50": "510050.SS",
    "创业板": "159915.SZ",
    # 行业
    "医药ETF": "512010.SS",
    "消费ETF": "159928.SZ",
    "银行ETF": "512800.SS",
    # 跨境
    "纳指ETF": "513100.SS",
    "标普500": "513500.SS",
    "恒生ETF": "159920.SZ",
}


def get_etf(
    name_or_ticker: str,
    start: str = "2020-01-01",
    end: str = None,
) -> pd.DataFrame:
    """
    获取单只ETF的历史行情数据。

    参数：
        name_or_ticker: ETF中文名（如"沪深300"）或yfinance代码（如"510300.SS"）
        start: 开始日期，格式 "YYYY-MM-DD"，默认 "2020-01-01"
        end:   结束日期，默认到最新

    返回：
        DataFrame，包含 Open/High/Low/Close/Volume 列，索引为日期
    """
    # 如果传入的是中文名称，从ETF池查找对应代码
    if name_or_ticker in ETF_POOL:
        ticker = ETF_POOL[name_or_ticker]
    elif "." in name_or_ticker:
        # 已经是完整的 yfinance 代码
        ticker = name_or_ticker
    else:
        # 尝试自动补全后缀（6位数字代码）
        ticker = _guess_ticker(name_or_ticker)

    df = yf.download(ticker, start=start, end=end, progress=False)

    if df is None or df.empty:
        raise ValueError(f"无法获取 {name_or_ticker}({ticker}) 的数据，请检查代码是否正确")

    # yfinance 有时返回 MultiIndex 列，统一处理
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 确保索引是 DatetimeIndex
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    return df


def get_etfs(
    names: list,
    start: str = "2020-01-01",
    end: str = None,
    column: str = "Close",
) -> pd.DataFrame:
    """
    批量获取多只ETF的收盘价（或其他列），合并为一个 DataFrame。

    参数：
        names:  ETF名称列表，如 ["沪深300", "中证红利", "黄金ETF"]
        start:  开始日期
        end:    结束日期
        column: 要提取的列，默认 "Close"

    返回：
        DataFrame，每列为一只ETF，索引为日期
    """
    result = pd.DataFrame()
    failed = []

    for name in names:
        try:
            df = get_etf(name, start=start, end=end)
            if column in df.columns and len(df) > 0:
                result[name] = df[column]
            else:
                failed.append(name)
        except Exception as e:
            failed.append(name)

    if failed:
        print(f"⚠️ 以下ETF获取失败: {failed}")

    # 前向填充缺失值（交易日不一致时）
    result = result.dropna(how="all").ffill()

    return result


def list_etfs() -> dict:
    """列出所有内置的ETF代码映射。"""
    return dict(ETF_POOL)


def _guess_ticker(code: str) -> str:
    """
    根据6位数字代码猜测 yfinance ticker 后缀。
    上海：51xxxx, 510xxx, 511xxx, 512xxx, 513xxx, 515xxx, 518xxx, 560xxx, 563xxx, 588xxx
    深圳：15xxxx, 159xxx
    """
    code = code.strip()
    if code.startswith("5") or code.startswith("0"):
        return f"{code}.SS"
    elif code.startswith("1"):
        return f"{code}.SZ"
    else:
        return f"{code}.SS"
