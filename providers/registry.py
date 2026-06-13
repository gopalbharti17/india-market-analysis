"""
providers/registry.py — The factory. config.py names a provider; this file
turns the name into a working object. Adding a new provider = one import
+ one dictionary entry here.
"""

from providers.stocks_yahoo import YahooStockProvider
from providers.mf_mfapi import MFApiProvider
from providers.benchmarks_yahoo import YahooBenchmarkProvider
from providers.benchmarks_nse_tri import NSETRIBenchmarkProvider

STOCK_PROVIDERS = {
    "yahoo": YahooStockProvider,
    # "kite": lazily imported below (needs credentials + kiteconnect package)
}

MF_PROVIDERS = {
    "mfapi": MFApiProvider,
}

BENCHMARK_PROVIDERS = {
    "yahoo": YahooBenchmarkProvider,          # PRICE indices (alpha overstated)
    "nse_tri": NSETRIBenchmarkProvider,       # official TRI, auto-falls back to yahoo
}


def get_stock_provider(name: str):
    if name == "kite":  # lazy import so free users never need kiteconnect
        from providers.stocks_kite import KiteStockProvider
        return KiteStockProvider()
    if name == "screener_export":
        from providers.stocks_screener_export import ScreenerExportProvider
        from config import SCREENER_EXPORT_PATH
        return ScreenerExportProvider(SCREENER_EXPORT_PATH)
    try:
        return STOCK_PROVIDERS[name]()
    except KeyError:
        raise ValueError(f"Unknown stock provider '{name}'. Options: "
                         f"{list(STOCK_PROVIDERS) + ['kite', 'screener_export']}")


def get_mf_provider(name: str):
    try:
        return MF_PROVIDERS[name]()
    except KeyError:
        raise ValueError(f"Unknown MF provider '{name}'. Options: {list(MF_PROVIDERS)}")


def get_benchmark_provider(name: str):
    try:
        return BENCHMARK_PROVIDERS[name]()
    except KeyError:
        raise ValueError(f"Unknown benchmark provider '{name}'. Options: {list(BENCHMARK_PROVIDERS)}")
