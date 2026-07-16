# -*- coding: utf-8 -*-
"""
文件名: data_fetcher.py
功能说明: 东方财富行情数据获取器
          - 优先使用真实行情 API（东方财富 push2）
          - 请求带重试机制和限流
          - 失败时返回 Mock 数据保证前端可用性，并标记 data_source = "mock"
          - 前端可根据 data_source 字段区分真实/模拟数据
作者: Investment App Team
创建日期: 2024-01-01
最后更新: 2026-07-16 — 真实行情对接优化
"""

import time
import random
import logging
import requests
from typing import Any

from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DataFetcher:
    """东方财富行情数据获取器 — 真实行情优先"""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://quote.eastmoney.com/",
        }
        self.timeout = Config.REQUEST_TIMEOUT
        self.max_retries = Config.MAX_RETRIES
        self._last_request_time = 0
        self._data_source = "unknown"  # "live" / "mock" / "unknown"

    # ---- 公开属性 ----

    @property
    def data_source(self) -> str:
        """最近一次数据请求的数据源: "live" | "mock" | "unknown" """
        return self._data_source

    def is_live(self) -> bool:
        """最近一次数据是否为真实行情"""
        return self._data_source == "live"

    # ---- 内部方法 ----

    def _rate_limit(self) -> None:
        """请求限流"""
        elapsed = time.time() - self._last_request_time
        if elapsed < Config.REQUEST_INTERVAL:
            time.sleep(Config.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _request(self, url: str, params: dict = None) -> dict:
        """带重试的 HTTP GET"""
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                resp = requests.get(
                    url, params=params, headers=self.headers, timeout=self.timeout
                )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.Timeout:
                logger.warning(f"[重试 {attempt+1}/{self.max_retries}] 超时: {url}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"[重试 {attempt+1}/{self.max_retries}] 连接失败: {url}")
            except Exception as e:
                logger.warning(f"[重试 {attempt+1}/{self.max_retries}] 异常: {url} | {e}")
            if attempt < self.max_retries - 1:
                time.sleep(1 * (attempt + 1))
        logger.error(f"[最终失败] {url} — 将使用模拟数据")
        return {}

    @staticmethod
    def _get_secid(code: str) -> str:
        """股票代码 → 东方财富 secid"""
        code = code.strip()
        if code.startswith("6"):
            return f"1.{code}"
        elif code.startswith("8") or code.startswith("4"):
            return f"0.{code}"
        else:
            return f"0.{code}"

    def _mark_live(self):
        self._data_source = "live"

    def _mark_mock(self):
        self._data_source = "mock"

    # ================================================================
    #  公开数据接口
    # ================================================================

    def get_market_indices(self) -> list:
        """获取大盘指数实时行情（上证/深证/创业板/科创50/沪深300）"""
        secids = "1.000001,0.399001,0.399006,1.000688,1.000300"
        url = f"{Config.EASTMONEY_PUSH_URL}/ulist.np/get"
        params = {
            "fltt": "2",
            "fields": "f2,f3,f4,f5,f6,f12,f13,f14",
            "secids": secids,
        }
        try:
            data = self._request(url, params)
            if data and data.get("data") and data["data"].get("diff"):
                result = []
                for item in data["data"]["diff"]:
                    result.append({
                        "code": item.get("f12", ""),
                        "name": item.get("f14", ""),
                        "price": item.get("f2", 0),
                        "change_pct": item.get("f3", 0),
                        "change": item.get("f4", 0),
                        "volume": item.get("f5", 0),
                        "amount": item.get("f6", 0),
                    })
                self._mark_live()
                logger.info(f"[实时] 大盘指数获取成功，共 {len(result)} 条")
                return result
        except Exception as e:
            logger.error(f"[大盘指数] 请求异常: {e}")
        self._mark_mock()
        logger.warning("[大盘指数] 降级为模拟数据")
        return self._mock_indices()

    def get_stock_list(self, page: int = 1, page_size: int = 50,
                       sort_field: str = "f3", sort_order: str = "desc") -> dict:
        """获取 A 股股票列表（分页 + 排序）"""
        url = f"{Config.EASTMONEY_PUSH_URL}/clist/get"
        params = {
            "pn": page, "pz": page_size,
            "po": 1 if sort_order == "desc" else 0,
            "np": 1, "fltt": 2, "invt": 2,
            "fid": sort_field,
            "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
            "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23",
        }
        try:
            data = self._request(url, params)
            if data and data.get("data"):
                stock_list = []
                for item in data["data"].get("diff", []):
                    stock_list.append({
                        "code": item.get("f12", ""),
                        "name": item.get("f14", ""),
                        "price": item.get("f2", 0),
                        "change_pct": item.get("f3", 0),
                        "change": item.get("f4", 0),
                        "volume": item.get("f5", 0),
                        "amount": item.get("f6", 0),
                        "amplitude": item.get("f7", 0),
                        "turnover": item.get("f8", 0),
                        "pe": item.get("f9", 0),
                        "high": item.get("f15", 0),
                        "low": item.get("f16", 0),
                        "open": item.get("f17", 0),
                        "prev_close": item.get("f18", 0),
                        "market_cap": item.get("f20", 0),
                        "float_cap": item.get("f21", 0),
                        "pb": item.get("f23", 0),
                    })
                result = {
                    "list": stock_list,
                    "total": data["data"].get("total", 0),
                    "page": page, "page_size": page_size,
                }
                self._mark_live()
                logger.info(f"[实时] 股票列表获取成功，共 {result['total']} 条")
                return result
        except Exception as e:
            logger.error(f"[股票列表] 请求异常: {e}")
        self._mark_mock()
        logger.warning("[股票列表] 降级为模拟数据")
        return self._mock_stock_list(page, page_size)

    def get_stock_detail(self, code: str) -> dict:
        """获取个股实时行情详情"""
        secid = self._get_secid(code)
        url = f"{Config.EASTMONEY_PUSH_URL}/stock/get"
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,"
                      "f60,f116,f117,f162,f167,f168,f169,f170,f171,f292",
        }
        try:
            data = self._request(url, params)
            if data and data.get("data"):
                d = data["data"]
                return self._parse_stock_detail(code, d)
        except Exception as e:
            logger.error(f"[个股详情] {code} 请求异常: {e}")
        self._mark_mock()
        logger.warning(f"[个股详情] {code} 降级为模拟数据")
        return self._mock_stock_detail(code)

    def _parse_stock_detail(self, code: str, d: dict) -> dict:
        """解析个股行情字段（除以100还原实际值）"""
        result = {
            "code": code,
            "name": d.get("f58", ""),
            "price": d.get("f43", 0) / 100 if d.get("f43") else 0,
            "high": d.get("f44", 0) / 100 if d.get("f44") else 0,
            "low": d.get("f45", 0) / 100 if d.get("f45") else 0,
            "open": d.get("f46", 0) / 100 if d.get("f46") else 0,
            "volume": d.get("f47", 0),
            "amount": d.get("f48", 0),
            "prev_close": d.get("f60", 0) / 100 if d.get("f60") else 0,
            "market_cap": d.get("f116", 0),
            "float_cap": d.get("f117", 0),
            "pe": d.get("f162", 0) / 100 if d.get("f162") else 0,
            "pb": d.get("f167", 0) / 100 if d.get("f167") else 0,
            "change": d.get("f169", 0) / 100 if d.get("f169") else 0,
            "change_pct": d.get("f170", 0) / 100 if d.get("f170") else 0,
        }
        self._mark_live()
        return result

    def get_kline_data(self, code: str, klt: int = 101, count: int = 120) -> list:
        """获取 K 线历史数据（前复权）"""
        secid = self._get_secid(code)
        url = f"{Config.EASTMONEY_PUSHHIS_URL}/stock/kline/get"
        params = {
            "secid": secid, "klt": klt, "fqt": 1,
            "end": "20500101", "lmt": count,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        }
        try:
            data = self._request(url, params)
            if data and data.get("data") and data["data"].get("klines"):
                klines = []
                for line in data["data"]["klines"]:
                    parts = line.split(",")
                    if len(parts) >= 8:
                        klines.append({
                            "date": parts[0],
                            "open": float(parts[1]),
                            "close": float(parts[2]),
                            "high": float(parts[3]),
                            "low": float(parts[4]),
                            "volume": int(float(parts[5])),
                            "amount": float(parts[6]),
                            "amplitude": float(parts[7]) if parts[7] else 0,
                        })
                self._mark_live()
                logger.info(f"[实时] K线数据获取成功: {code}，共 {len(klines)} 条")
                return klines
        except Exception as e:
            logger.error(f"[K线] {code} 请求异常: {e}")
        self._mark_mock()
        logger.warning(f"[K线] {code} 降级为模拟数据")
        return self._mock_kline(code, count)

    def get_dragon_tiger(self) -> list:
        """获取龙虎榜数据"""
        url = Config.EASTMONEY_DATACENTER_URL
        params = {
            "sortColumns": "TRADE_DATE", "sortTypes": "-1",
            "pageSize": 20, "pageNumber": 1,
            "reportName": "RPT_DAILYBILLBOARD_DETAILS",
            "columns": "ALL", "source": "WEB", "client": "WEB",
        }
        try:
            data = self._request(url, params)
            if data and data.get("result") and data["result"].get("data"):
                result = []
                for item in data["result"]["data"]:
                    result.append({
                        "code": item.get("SECURITY_CODE", ""),
                        "name": item.get("SECURITY_NAME_ABBR", ""),
                        "date": str(item.get("TRADE_DATE", ""))[:10],
                        "close": item.get("CLOSE_PRICE", 0),
                        "change_pct": item.get("CHANGE_RATE", 0),
                        "net_buy": item.get("NET_AMOUNT", 0),
                        "buy_amount": item.get("BUY_AMOUNT", 0),
                        "sell_amount": item.get("SELL_AMOUNT", 0),
                        "reason": item.get("EXPLAIN", ""),
                    })
                self._mark_live()
                logger.info(f"[实时] 龙虎榜获取成功，共 {len(result)} 条")
                return result
        except Exception as e:
            logger.error(f"[龙虎榜] 请求异常: {e}")
        self._mark_mock()
        logger.warning("[龙虎榜] 降级为模拟数据")
        return self._mock_dragon_tiger()

    def search_stock(self, keyword: str) -> list:
        """搜索股票（代码/名称模糊匹配）"""
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": keyword, "type": "14",
            "token": "D43BF722C8E33BDC906FB84D85E326E8", "count": 10,
        }
        try:
            data = self._request(url, params)
            if data:
                table = data.get("QuotationCodeTable") or {}
                items = table.get("Data") or []
                result = []
                for item in items:
                    code = item.get("Code", "")
                    name = item.get("Name", "")
                    mkt = item.get("MktNum", "")
                    market = "SH" if mkt == "1" else ("SZ" if mkt == "2" else "CN")
                    result.append({"code": code, "name": name, "market": market})
                self._mark_live()
                return result
        except Exception as e:
            logger.error(f"[搜索] 关键字={keyword} 异常: {e}")
        return []

    # ================================================================
    #  Mock 兜底（仅在真实 API 失败时使用）
    # ================================================================

    def _mock_indices(self) -> list:
        indices = [
            ("000001", "上证指数", 3200), ("399001", "深证成指", 10500),
            ("399006", "创业板指", 2100), ("000688", "科创50", 980),
            ("000300", "沪深300", 3900),
        ]
        result = []
        for code, name, price in indices:
            c = random.uniform(-2, 2)
            result.append({
                "code": code, "name": name, "price": round(price + random.uniform(-50, 50), 2),
                "change_pct": round(c, 2), "change": round(price * c / 100, 2),
                "volume": random.randint(100_000_000, 500_000_000),
                "amount": random.randint(10_000_000_000, 50_000_000_000),
            })
        return result

    def _mock_stock_list(self, page: int, page_size: int) -> dict:
        names = [
            ("600519", "贵州茅台"), ("000858", "五粮液"), ("300750", "宁德时代"),
            ("601318", "中国平安"), ("000333", "美的集团"), ("600036", "招商银行"),
            ("002594", "比亚迪"), ("600276", "恒瑞医药"), ("000725", "京东方A"),
            ("601012", "隆基绿能"), ("600900", "长江电力"), ("002475", "立讯精密"),
            ("601888", "中国中免"), ("300059", "东方财富"), ("600030", "中信证券"),
            ("000001", "平安银行"), ("600887", "伊利股份"), ("002714", "牧原股份"),
            ("601668", "中国建筑"), ("600585", "海螺水泥"),
        ]
        start = (page - 1) * page_size
        stock_list = []
        for code, name in names[start:start + page_size]:
            price = round(random.uniform(5, 2000), 2)
            change_pct = round(random.uniform(-10, 10), 2)
            change = round(price * change_pct / 100, 2)
            stock_list.append({
                "code": code, "name": name, "price": price,
                "change_pct": change_pct, "change": change,
                "volume": random.randint(100_000, 10_000_000),
                "amount": random.randint(100_000_000, 5_000_000_000),
                "amplitude": round(random.uniform(1, 15), 2),
                "turnover": round(random.uniform(0.5, 20), 2),
                "pe": round(random.uniform(5, 100), 2),
                "high": round(price * 1.03, 2), "low": round(price * 0.97, 2),
                "open": round(price * random.uniform(0.97, 1.03), 2),
                "prev_close": round(price - change, 2),
                "market_cap": random.randint(10_000_000_000, 3_000_000_000_000),
                "float_cap": random.randint(5_000_000_000, 2_000_000_000_000),
                "pb": round(random.uniform(1, 20), 2),
            })
        return {"list": stock_list, "total": len(names), "page": page, "page_size": page_size}

    def _mock_stock_detail(self, code: str) -> dict:
        price = round(random.uniform(5, 2000), 2)
        change_pct = round(random.uniform(-10, 10), 2)
        return {
            "code": code, "name": f"模拟-{code}",
            "price": price, "high": round(price * 1.03, 2),
            "low": round(price * 0.97, 2), "open": round(price * 0.99, 2),
            "volume": random.randint(100_000, 10_000_000),
            "amount": random.randint(100_000_000, 5_000_000_000),
            "prev_close": round(price - price * change_pct / 100, 2),
            "market_cap": random.randint(10_000_000_000, 3_000_000_000_000),
            "float_cap": random.randint(5_000_000_000, 2_000_000_000_000),
            "pe": round(random.uniform(5, 100), 2),
            "pb": round(random.uniform(1, 20), 2),
            "change": round(price * change_pct / 100, 2),
            "change_pct": change_pct,
        }

    def _mock_kline(self, code: str, count: int) -> list:
        from datetime import datetime, timedelta
        klines = []
        base = random.uniform(10, 100)
        today = datetime.now()
        for i in range(count):
            d = (today - timedelta(days=count - i)).strftime("%Y-%m-%d")
            o = base + random.uniform(-2, 2)
            c = o + random.uniform(-3, 3)
            h = max(o, c) + random.uniform(0.5, 2)
            l = min(o, c) - random.uniform(0.5, 2)
            klines.append({
                "date": d, "open": round(o, 2), "close": round(c, 2),
                "high": round(h, 2), "low": round(l, 2),
                "volume": random.randint(500_000, 5_000_000),
                "amount": round(random.uniform(50_000_000, 500_000_000), 2),
                "amplitude": round((h - l) / o * 100, 2),
            })
            base = c
        return klines

    def _mock_dragon_tiger(self) -> list:
        names = [
            ("600519", "贵州茅台"), ("300750", "宁德时代"), ("002594", "比亚迪"),
            ("601012", "隆基绿能"), ("300059", "东方财富"), ("000725", "京东方A"),
        ]
        result = []
        for code, name in names:
            result.append({
                "code": code, "name": name, "date": "----",
                "close": round(random.uniform(10, 500), 2),
                "change_pct": round(random.uniform(-10, 10), 2),
                "net_buy": 0, "buy_amount": 0, "sell_amount": 0,
                "reason": "（模拟数据）",
            })
        return result


# 全局实例
fetcher = DataFetcher()
