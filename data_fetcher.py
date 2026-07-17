# -*- coding: utf-8 -*-
"""
文件名: data_fetcher.py
功能说明: 多源行情数据获取器
          数据源优先级: 东方财富 → 腾讯财经 → Mock 兜底
          - 东方财富 push2: 国内首选，但境外(Render新加坡)可能被限
          - 腾讯财经 qt.gtimg.cn: CDN 全球分发，境内外通用
          - Mock: 所有数据源失败时的保底方案
作者: Investment App Team
创建日期: 2024-01-01
最后更新: 2026-07-17 — 增加腾讯财经备用源，适配 Render 海外部署
"""

import time
import random
import logging
import re
import json
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
        """获取大盘指数实时行情（上证/深证/创业板/科创50/沪深300）
        数据源: 东方财富 → 腾讯财经 → Mock
        """
        # ---- 数据源 1: 东方财富 ----
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
                logger.info(f"[东方财富] 大盘指数获取成功，共 {len(result)} 条")
                return result
        except Exception as e:
            logger.warning(f"[东方财富] 大盘指数失败: {e}，尝试腾讯财经...")

        # ---- 数据源 2: 腾讯财经 (CDN 全球可达) ----
        try:
            result = self._fetch_tencent_indices()
            if result:
                self._mark_live()
                logger.info(f"[腾讯财经] 大盘指数获取成功，共 {len(result)} 条")
                return result
        except Exception as e:
            logger.warning(f"[腾讯财经] 大盘指数失败: {e}")

        # ---- 数据源 3: Mock 兜底 ----
        self._mark_mock()
        logger.warning("[大盘指数] 全部数据源失败，降级为模拟数据")
        return self._mock_indices()

    def get_stock_list(self, page: int = 1, page_size: int = 50,
                       sort_field: str = "f3", sort_order: str = "desc") -> dict:
        """获取 A 股股票列表（分页 + 排序）
        数据源: 东方财富 → 腾讯财经 → Mock
        """
        # ---- 数据源 1: 东方财富 ----
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
                logger.info(f"[东方财富] 股票列表获取成功，共 {result['total']} 条")
                return result
        except Exception as e:
            logger.warning(f"[东方财富] 股票列表失败: {e}，尝试腾讯财经...")

        # ---- 数据源 2: 腾讯财经 (热门股实时行情) ----
        try:
            result = self._fetch_tencent_stock_list(page, page_size, sort_order)
            if result and result.get("list"):
                self._mark_live()
                logger.info(f"[腾讯财经] 股票列表获取成功，共 {result['total']} 条")
                return result
        except Exception as e:
            logger.warning(f"[腾讯财经] 股票列表失败: {e}")

        # ---- 数据源 3: Mock 兜底 ----
        self._mark_mock()
        logger.warning("[股票列表] 全部数据源失败，降级为模拟数据")
        return self._mock_stock_list(page, page_size)

    def get_stock_detail(self, code: str) -> dict:
        """获取个股实时行情详情
        数据源: 东方财富 → 腾讯财经 → Mock
        """
        # ---- 数据源 1: 东方财富 ----
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
            logger.warning(f"[东方财富] 个股详情 {code} 失败: {e}，尝试腾讯财经...")

        # ---- 数据源 2: 腾讯财经 ----
        try:
            result = self._fetch_tencent_stock_detail(code)
            if result:
                self._mark_live()
                logger.info(f"[腾讯财经] 个股详情 {code} 获取成功")
                return result
        except Exception as e:
            logger.warning(f"[腾讯财经] 个股详情 {code} 失败: {e}")

        # ---- 数据源 3: Mock 兜底 ----
        self._mark_mock()
        logger.warning(f"[个股详情] {code} 全部数据源失败，降级为模拟数据")
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
        """获取 K 线历史数据（前复权）
        数据源: 腾讯财经 → 东方财富 → Mock
        """
        # ---- 数据源 1: 腾讯财经 (qffq=前复权, 境外可用) ----
        try:
            result = self._fetch_tencent_kline(code, count)
            if result:
                self._mark_live()
                logger.info(f"[腾讯财经] K线 {code} 获取成功，共 {len(result)} 条")
                return result
        except Exception as e:
            logger.warning(f"[腾讯财经] K线 {code} 失败: {e}，尝试东方财富...")

        # ---- 数据源 2: 东方财富 ----
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
                logger.info(f"[东方财富] K线 {code} 获取成功，共 {len(klines)} 条")
                return klines
        except Exception as e:
            logger.warning(f"[东方财富] K线 {code} 失败: {e}")

        # ---- 数据源 3: Mock 兜底 ----
        self._mark_mock()
        logger.warning(f"[K线] {code} 全部数据源失败，降级为模拟数据")
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


    # ================================================================
    #  腾讯财经 API（CDN 全球可分，适配 Render 等海外平台）
    # ================================================================

    # 热门 A 股池（用于腾讯财经股票列表，覆盖主要蓝筹 + 热门股）
    HOT_STOCKS = [
        ("600519", "贵州茅台"), ("000858", "五粮液"), ("300750", "宁德时代"),
        ("601318", "中国平安"), ("000333", "美的集团"), ("600036", "招商银行"),
        ("002594", "比亚迪"), ("600276", "恒瑞医药"), ("000725", "京东方A"),
        ("601012", "隆基绿能"), ("600900", "长江电力"), ("002475", "立讯精密"),
        ("601888", "中国中免"), ("300059", "东方财富"), ("600030", "中信证券"),
        ("000001", "平安银行"), ("600887", "伊利股份"), ("002714", "牧原股份"),
        ("601668", "中国建筑"), ("600585", "海螺水泥"), ("601398", "工商银行"),
        ("601939", "建设银行"), ("601288", "农业银行"), ("601988", "中国银行"),
        ("600028", "中国石化"), ("601857", "中国石油"), ("601088", "中国神华"),
        ("002415", "海康威视"), ("000651", "格力电器"), ("600031", "三一重工"),
        ("300015", "爱尔眼科"), ("300124", "汇川技术"), ("601899", "紫金矿业"),
        ("603259", "药明康德"), ("688981", "中芯国际"), ("002230", "科大讯飞"),
        ("300274", "阳光电源"), ("601166", "兴业银行"), ("600809", "山西汾酒"),
        ("301280", "德福科技"), ("600941", "中国移动"), ("600050", "中国联通"),
        ("601728", "中国电信"), ("002049", "紫光国微"), ("688111", "金山办公"),
        ("300782", "卓胜微"), ("601615", "东方电气"), ("688012", "中微公司"),
        ("300760", "迈瑞医疗"), ("600309", "万华化学"), ("002371", "北方华创"),
        ("000568", "泸州老窖"), ("002460", "赣锋锂业"), ("300014", "亿纬锂能"),
    ]

    def _make_tencent_code(self, code: str) -> str:
        """股票代码 → 腾讯行情代码 (shXXXXXX 或 szXXXXXX)"""
        code = code.strip()
        if code.startswith("6") or code.startswith("5"):
            return f"sh{code}"
        else:
            return f"sz{code}"

    @staticmethod
    def _parse_tencent_line(line: str) -> dict | None:
        """解析腾讯行情返回的单行数据 v_xxx="..." """
        if not line or "=" not in line:
            return None
        try:
            # v_sh000001="1~上证指数~000001~..."
            raw = line.split("=", 1)[1].strip().strip('"').strip(";")
            return dict(enumerate(raw.split("~")))
        except Exception:
            return None

    def _fetch_tencent_indices(self) -> list:
        """腾讯财经: 获取大盘指数"""
        codes = "sh000001,sz399001,sz399006,sh000688,sh000300"
        url = Config.TENCENT_QUOTE_URL + codes
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            resp.encoding = "gbk"
            lines = resp.text.strip().split("\n")
            result = []
            for line in lines:
                d = self._parse_tencent_line(line)
                if not d:
                    continue
                name = d.get(1, "").strip()
                code = d.get(2, "")
                price = float(d.get(3, 0))
                change_pct = float(d.get(32, 0))
                change = float(d.get(31, 0))
                volume = int(float(d.get(6, 0)))
                # 复合字段: "当前价/成交量/成交额"
                composite = d.get(35, "")
                amount = 0
                if composite and "/" in composite:
                    parts = composite.split("/")
                    if len(parts) >= 3:
                        amount = int(float(parts[2]))
                result.append({
                    "code": code, "name": name, "price": price,
                    "change_pct": round(change_pct, 2),
                    "change": round(change, 2),
                    "volume": volume, "amount": amount,
                })
            return result if result else None
        except Exception as e:
            logger.warning(f"[腾讯财经] 大盘指数请求失败: {e}")
            return None

    def _fetch_tencent_stock_list(self, page: int, page_size: int,
                                   sort_order: str = "desc") -> dict:
        """腾讯财经: 获取热门股票列表（实时行情 + 分页）"""
        # 取当前页对应的股票
        start = (page - 1) * page_size
        batch = self.HOT_STOCKS[start:start + page_size]
        if not batch:
            return {"list": [], "total": len(self.HOT_STOCKS), "page": page, "page_size": page_size}

        # 构造批量查询
        codes = ",".join(self._make_tencent_code(c) for c, _ in batch)
        url = Config.TENCENT_QUOTE_URL + codes
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            resp.encoding = "gbk"
            lines = resp.text.strip().split("\n")
            stock_list = []
            for line in lines:
                d = self._parse_tencent_line(line)
                if not d:
                    continue
                name = d.get(1, "").strip()
                code = d.get(2, "")
                price = float(d.get(3, 0))
                prev_close = float(d.get(4, 0))
                open_p = float(d.get(5, 0))
                volume = int(float(d.get(6, 0)))
                change = float(d.get(31, 0))
                change_pct = float(d.get(32, 0))
                high = float(d.get(33, 0))
                low = float(d.get(34, 0))
                amount = float(d.get(37, 0)) * 10000 if d.get(37) else 0  # 万元→元
                turnover = float(d.get(38, 0))
                pe = float(d.get(39, 0))
                amplitude = float(d.get(43, 0))
                market_cap = float(d.get(44, 0)) * 100000000 if d.get(44) else 0  # 亿→元
                float_cap = float(d.get(45, 0)) * 100000000 if d.get(45) else 0
                pb = float(d.get(46, 0))
                stock_list.append({
                    "code": code, "name": name, "price": round(price, 2),
                    "change_pct": round(change_pct, 2), "change": round(change, 2),
                    "volume": volume, "amount": amount,
                    "amplitude": round(amplitude, 2), "turnover": round(turnover, 2),
                    "pe": round(pe, 2), "high": round(high, 2), "low": round(low, 2),
                    "open": round(open_p, 2), "prev_close": round(prev_close, 2),
                    "market_cap": int(market_cap), "float_cap": int(float_cap),
                    "pb": round(pb, 2),
                })
            # 排序
            if sort_order == "desc":
                stock_list.sort(key=lambda x: x["change_pct"], reverse=True)
            else:
                stock_list.sort(key=lambda x: x["change_pct"])
            return {
                "list": stock_list,
                "total": len(self.HOT_STOCKS),
                "page": page, "page_size": page_size,
            }
        except Exception as e:
            logger.warning(f"[腾讯财经] 股票列表请求失败: {e}")
            return None

    def _fetch_tencent_stock_detail(self, code: str) -> dict | None:
        """腾讯财经: 获取个股实时行情"""
        tencent_code = self._make_tencent_code(code)
        url = Config.TENCENT_QUOTE_URL + tencent_code
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            resp.encoding = "gbk"
            d = self._parse_tencent_line(resp.text.strip())
            if not d or not d.get(1):
                return None
            price = float(d.get(3, 0))
            prev_close = float(d.get(4, 0))
            open_p = float(d.get(5, 0))
            volume = int(float(d.get(6, 0)))
            change_pct = float(d.get(32, 0))
            change = float(d.get(31, 0))
            high = float(d.get(33, 0))
            low = float(d.get(34, 0))
            amount = float(d.get(37, 0)) * 10000 if d.get(37) else 0
            pe = float(d.get(39, 0))
            pb = float(d.get(46, 0))
            market_cap = float(d.get(44, 0)) * 100000000 if d.get(44) else 0
            float_cap = float(d.get(45, 0)) * 100000000 if d.get(45) else 0
            name = d.get(1, "").strip()
            return {
                "code": code, "name": name, "price": round(price, 2),
                "high": round(high, 2), "low": round(low, 2),
                "open": round(open_p, 2), "volume": volume,
                "amount": int(amount), "prev_close": round(prev_close, 2),
                "market_cap": int(market_cap), "float_cap": int(float_cap),
                "pe": round(pe, 2), "pb": round(pb, 2),
                "change": round(change, 2), "change_pct": round(change_pct, 2),
            }
        except Exception as e:
            logger.warning(f"[腾讯财经] 个股详情 {code} 失败: {e}")
            return None

    def _fetch_tencent_kline(self, code: str, count: int = 120) -> list | None:
        """腾讯财经: 获取日K线（前复权）"""
        tencent_code = self._make_tencent_code(code)
        url = f"{Config.TENCENT_KLINE_URL}?param={tencent_code},day,,,{count},qfq"
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            data = resp.json()
            # 路径: data[tencent_code]["qfqday"] 或 data[tencent_code]["day"]
            stock_data = data.get("data", {}).get(tencent_code, {})
            klines_raw = stock_data.get("qfqday") or stock_data.get("day") or []
            if not klines_raw:
                return None
            klines = []
            for item in klines_raw:
                # 格式: ["2026-07-17","1258.99","1269.01","1238.98","1252.60","34212.00"]
                if isinstance(item, list) and len(item) >= 6:
                    klines.append({
                        "date": item[0],
                        "open": float(item[1]),
                        "close": float(item[4]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "volume": int(float(item[5])),
                        "amount": float(item[5]) * float(item[4]),
                        "amplitude": 0,
                    })
            return klines if klines else None
        except Exception as e:
            logger.warning(f"[腾讯财经] K线 {code} 失败: {e}")
            return None


# 全局实例
fetcher = DataFetcher()
