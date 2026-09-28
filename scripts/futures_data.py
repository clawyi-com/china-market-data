# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""交易所期货/期权与持仓、新浪行情及上金所现货。"""
import _runtime  # noqa: F401  须在第三方库之前导入
import pandas as pd
from _market_common import (
    _v39_date, _v39_frame, _v39_http, _v39_json, _v39_num,
    _v39_req_num, _v39_rows, _v39_src_date, _v39_contract,
)

import csv
import io
import json
import re
from xml.etree import ElementTree

FUTURES_EXCHANGES = ("SHFE", "INE", "CZCE", "CFFEX", "GFEX")
_SHFE_HOSTS = {"SHFE": "https://www.shfe.com.cn", "INE": "https://www.ine.cn"}
CZCE_FILE_URL = "https://www.czce.com.cn/cn/DFSStaticFiles/{kind}/{year}/{ymd}/{name}.txt"
CZCE_FIRST_DAY = "20150921"      # 郑商所现行文件路径的第一天；更早是另一套无表头 CSV，未接入
CFFEX_DAILY_URL = "http://www.cffex.com.cn/fzjy/mrhq/{ym}/{dd}/{ymd}_1.csv"
CFFEX_DAILY_XML = "http://www.cffex.com.cn/fzjy/mrhq/{ym}/{dd}/index.xml"
CFFEX_RANK_URL = "http://www.cffex.com.cn/sj/ccpm/{ym}/{dd}/{product}_1.csv"
# 各品种持仓排名文件的第一天（2026-09-20 逐个二分实测，前一交易日都是 302 缺文件）
CFFEX_RANK_FIRST_DAY = {"IF": "20100416", "IH": "20150416", "IC": "20150416", "IM": "20220722",
                        "TS": "20180817", "TF": "20130906", "T": "20150320", "TL": "20230421"}
GFEX_DAILY_URL = "http://www.gfex.com.cn/u/interfacesWebTiDayQuotes/loadList"
SINA_HQ_URL = "https://hq.sinajs.cn/list="
SINA_FUT_KLINE_URL = ("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_{code}="
                      "/InnerFuturesNewService.getDailyKLine")
SGE_DAILY_URL = "https://www.sge.com.cn/graph/Dailyhq"
_CFFEX_SINA_PRODUCTS = ("IF", "IH", "IC", "IM", "TS", "TF", "T", "TL")
_DCE_HINT = ("大商所官网有 JS 反爬（纯 HTTP 返回 412），不提供官方日行情；大商所品种（豆粕 M、铁矿 I、塑料 L…）"
             "请用 futures_kline('M0') 取逐日 K 线（新浪），futures_realtime('M0') 取实时/收盘快照")
_FUT_COLUMNS = ["date", "exchange", "symbol", "product", "open", "high", "low", "close", "settle",
                "pre_settle", "volume", "open_interest", "oi_change", "turnover_10k"]
_OPT_COLUMNS = ["date", "exchange", "symbol", "series", "option_type", "strike", "open", "high",
                "low", "close", "settle", "pre_settle", "volume", "open_interest", "oi_change",
                "turnover_10k", "delta", "iv_pct", "series_iv_pct"]
_RANK_COLUMNS = ["date", "exchange", "level", "symbol", "rank", "volume_member", "volume",
                 "volume_chg", "long_member", "long_oi", "long_chg", "short_member", "short_oi",
                 "short_chg"]


def _fut_price(value):
    """期货/期权价格：0 不是有效价格（无成交时交易所填 0 或空），统一成 None。"""
    number = _v39_num(value)
    return None if number == 0 else number


def _fut_product(code):
    """合约代码的品种字母（rb2610 -> rb、IF2609 -> IF）；不是字母开头说明来源格式变了。"""
    match = re.match(r"[A-Za-z]+", str(code))
    if not match:
        raise RuntimeError(f"合约代码 {code!r} 不是字母开头，格式可能已变")
    return match.group(0)


def _fut_exchange(exchange):
    exchange = str(exchange).upper()
    if exchange == "DCE":
        raise ValueError(_DCE_HINT)
    if exchange not in FUTURES_EXCHANGES:
        raise ValueError("exchange 只能是 " + " / ".join(FUTURES_EXCHANGES) + "（大商所见 futures_kline / futures_realtime）")
    return exchange


def _shfe_json(exchange, path, ymd, key, allow_missing=False):
    """上期所 / 上期能源的 .dat（实为 JSON）。非交易日官网 404；allow_missing 时返回 (None, url)。
    key 是调用方要读的行列表字段（o_curinstrument / o_cursor）；顶层不是对象、它不是由对象组成的列表，抛 RuntimeError。"""
    url = f"{_SHFE_HOSTS[exchange]}/data/tradedata/{path}{ymd}.dat"
    first = _INE_FIRST_DAY.get(path) if exchange == "INE" else None
    if first and ymd < first:
        # 能源中心首日前有些日子也发文件，但里面没有该类合约；按「当时还没有」处理，不能报成格式改变
        if allow_missing:
            return None, url
        raise ValueError(f"上期能源该类数据从 {first} 起才有（{ymd} 早于首日）")
    response = _v39_http(url, timeout=(10, 60), allow_status=(404,))
    payload = None
    if response.status_code != 404:
        try:
            payload = json.loads(response.content.decode("utf-8"))
        except ValueError as exc:       # 含 UnicodeDecodeError：错误页不是「没有数据」
            raise RuntimeError(f"{exchange} {url} 返回的不是 JSON，可能是错误页") from exc
        rows = payload.get(key) if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise RuntimeError(f"{exchange} {url} 的 {key} 不是由对象组成的列表，格式可能已变")
        reported = payload.get("report_date")
        if reported is not None and str(reported) != ymd:
            raise RuntimeError(f"{exchange} 返回的 report_date={reported}，不是 {ymd}")
        # 早年文件没有 report_date（上期所 2015 年的排名文件），只能以文件名里的日期为准；
        # 能源中心 2019 年的排名文件则是「没有 report_date + 列表为空」的空壳，按没有数据处理
        if reported is None and not any(v for v in payload.values() if isinstance(v, list)):
            payload = None
    if payload is None:
        if allow_missing:
            return None, url
        raise ValueError(f"{exchange} {ymd} 没有数据：非交易日、尚未发布或该品种当时未上市")
    return payload, url


def _czce_text(kind, name, ymd):
    if ymd < CZCE_FIRST_DAY:
        raise ValueError(f"郑商所数据从 {CZCE_FIRST_DAY} 起接入（更早的文件是另一套格式）")
    url = CZCE_FILE_URL.format(kind=kind, year=ymd[:4], ymd=ymd, name=name)
    response = _v39_http(url, timeout=(10, 60), allow_status=(404,))
    if response.status_code == 404:
        raise ValueError(f"郑商所 {ymd} 没有 {name}：非交易日或尚未发布")
    try:
        text = response.content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = response.content.decode("gbk")   # 2017 年及以前的文件是 GBK
    if f"({ymd[:4]}-{ymd[4:6]}-{ymd[6:]})" not in text.split("\n", 1)[0] + text[:200]:
        raise RuntimeError(f"郑商所 {name} 标题里的日期不是 {ymd}")
    return text, url


# 郑商所 2021 年前的表头叫「品种月份 / 品种代码」「空盘量」，与现在的「合约代码」「持仓量」是同一列
_CZCE_HEADER_ALIAS = {"品种月份": "合约代码", "品种代码": "合约代码", "空盘量": "持仓量"}


def _czce_table(text, header_prefix):
    """郑商所竖线分隔表：返回 (表头, 数据行)，千分位逗号已去掉，小计/总计已剔除。"""
    lines = [line for line in text.splitlines() if "|" in line]
    header = [_CZCE_HEADER_ALIAS.get(c.strip(), c.strip()) for c in lines[0].split("|")] if lines else []
    if not header or header[0] != header_prefix:
        raise RuntimeError("郑商所文件表头改变")
    rows = []
    for line in lines[1:]:
        cells = [c.strip().replace(",", "") for c in line.split("|")]
        if not cells[0] or cells[0].endswith(("小计", "总计", "合计")):
            continue                            # 期权文件还有「AP合计」这类品种合计行
        rows.append(dict(zip(header, cells)))
    return header, rows


def _cffex_csv(url, allow_missing=False):
    response = _v39_http(url, timeout=(10, 60), allow_status=(302, 404), allow_redirects=False)
    # 中金所缺文件时 302 跳到 error_404 页面
    if response.status_code in (302, 404):
        if allow_missing:
            return None
        raise ValueError(f"中金所没有该文件（非交易日或尚未发布）: {url}")
    return list(csv.reader(io.StringIO(response.content.decode("gbk"))))


def _cffex_daily_table(ymd):
    """中金所日行情 CSV（期货 + 期权同一个文件）。CSV 里没有交易日列，同目录的 index.xml 每行都带
    tradingday；用它核对交易日，并逐合约核对成交量 / 收盘价 / 持仓量，对不上就抛 RuntimeError，
    不把别的交易日的文件标成这一天（2010–2026 抽 5 天实测两者逐合约一致）。"""
    url = CFFEX_DAILY_URL.format(ym=ymd[:6], dd=ymd[6:], ymd=ymd)
    table = _cffex_csv(url)
    if not table or table[0][:3] != ["合约代码", "今开盘", "最高价"]:
        raise RuntimeError("中金所日行情表头改变")
    xml_url = CFFEX_DAILY_XML.format(ym=ymd[:6], dd=ymd[6:])
    response = _v39_http(xml_url, timeout=(10, 60), allow_status=(302, 404), allow_redirects=False)
    if response.status_code in (302, 404):
        raise RuntimeError(f"中金所 {ymd} 有行情 CSV 却没有 index.xml，无法核对交易日: {xml_url}")
    if b"<!DOCTYPE" in response.content or b"<!ENTITY" in response.content:
        raise RuntimeError(f"中金所 index.xml 含 DOCTYPE / ENTITY，拒绝解析: {xml_url}")
    try:
        nodes = ElementTree.fromstring(response.content).findall("dailydata")
    except ElementTree.ParseError as exc:
        raise RuntimeError(f"中金所 index.xml 无法解析: {exc}") from exc
    witness = {}
    for node in nodes:
        values = {k: (node.findtext(k) or "").strip() for k in
                  ("instrumentid", "tradingday", "volume", "closeprice", "openinterest")}
        if values["tradingday"] != ymd:
            raise RuntimeError(f"中金所 index.xml 的交易日是 {values['tradingday']}，不是 {ymd}")
        witness[values["instrumentid"]] = tuple(_v39_num(values[k]) for k in ("volume", "closeprice", "openinterest"))
    header = [c.strip() for c in table[0]]
    csv_rows = {}
    for rec in table[1:]:
        code = rec[0].strip() if rec else ""
        if not code or code in ("小计", "合计", "总计"):
            continue
        r = dict(zip(header, rec))
        csv_rows[code] = tuple(_v39_num(r.get(k)) for k in ("成交量", "今收盘", "持仓量"))
    if not witness or len(witness) != len(nodes) or csv_rows != witness:
        diff = sorted(set(csv_rows) ^ set(witness)) or sorted(k for k in csv_rows if csv_rows[k] != witness.get(k))
        raise RuntimeError(f"中金所 {ymd} 行情 CSV 与 index.xml 对不上（{len(csv_rows)} / {len(witness)} 个合约，"
                           f"例如 {diff[:3]}），不能确认 CSV 属于这一天")
    return table, url


_CFFEX_RANK_SUB = ["会员简称", "成交量", "比上一交易日增减", "会员简称", "持买单量", "比上一交易日增减",
                   "会员简称", "持卖单量", "比上一交易日增减"]


def _cffex_rank_rows(table, product, ymd):
    """中金所持仓排名 CSV → 行。只在核对过两行表头的「排名」段里取数，列顺序不对就抛错。
    2015 年前后的旧文件在排名段前面还有一段「会员类别」合计（表头同样以 交易日,合约 开头），跳过。"""
    out, in_rank, i = [], False, 0
    while i < len(table):
        cells = [c.strip() for c in table[i]]
        if cells[:2] == ["交易日", "合约"]:
            in_rank = cells[2:3] == ["排名"]
            if in_rank:
                sub = [c.strip() for c in table[i + 1][3:12]] if i + 1 < len(table) else []
                if cells[3:12:3] != ["成交量排名", "持买单量排名", "持卖单量排名"] or sub != _CFFEX_RANK_SUB:
                    raise RuntimeError(f"中金所 {product} 持仓排名表头变了: {cells} / {sub}")
                i += 1
        elif cells[2:3] and cells[2].isdigit():
            if not in_rank:
                raise RuntimeError(f"中金所 {product} 持仓排名在排名表头之前出现数据行: {cells}")
            if len(cells) < 12:
                raise RuntimeError(f"中金所 {product} 持仓排名行缺列: {cells}")
            if cells[0] != ymd:
                raise RuntimeError(f"中金所 {product} 持仓排名交易日是 {cells[0]}，不是 {ymd}")
            out.append({"level": "contract", "symbol": cells[1], "rank": int(cells[2]),
                        "volume_member": _rank_member(cells[3]), "volume": _v39_num(cells[4]),
                        "volume_chg": _v39_num(cells[5]),
                        "long_member": _rank_member(cells[6]), "long_oi": _v39_num(cells[7]),
                        "long_chg": _v39_num(cells[8]),
                        "short_member": _rank_member(cells[9]), "short_oi": _v39_num(cells[10]),
                        "short_chg": _v39_num(cells[11])})
        i += 1
    return out


def _gfex_rows(ymd, trade_type):
    response = _v39_http(GFEX_DAILY_URL, method="POST", data={"trade_date": ymd, "trade_type": trade_type},
                         headers={"Referer": "http://www.gfex.com.cn/gfex/rihq/hqsj_tjsj.shtml"})
    payload = _v39_json(response)
    if not isinstance(payload, dict) or str(payload.get("code")) != "0":
        raise RuntimeError(f"广期所返回错误: {str(payload)[:200]}")
    # 广期所的行里没有交易日字段，只在 param 里回显请求参数；回显不符说明拿到的不是这次请求的结果。
    # 非交易日它返回空表（只剩合计行），不会回退到最近交易日（2026-09-19 周六实测）。
    param = payload.get("param")
    if not isinstance(param, dict):
        raise RuntimeError(f"广期所没有回显请求参数（param 应为对象）: {str(payload)[:200]}")
    data = _v39_rows(payload.get("data"), "广期所 data")
    if param.get("trade_date") not in ([ymd], ymd) or param.get("trade_type") not in ([str(trade_type)], str(trade_type)):
        raise RuntimeError(f"广期所回显的请求参数 {param} 与请求的 {ymd}/{trade_type} 不符")
    rows = []
    for r in data:
        if str(r.get("variety", "")).endswith(("小计", "总计")):
            continue
        # 实测（2022-12-22、2026-09-18/19）只有小计 / 总计行没有 delivMonth；字段改名时不能把合约行全部滤掉、报成非交易日
        if not r.get("delivMonth"):
            raise RuntimeError(f"广期所合约行缺 delivMonth，格式可能已变: {str(r)[:120]}")
        rows.append(r)
    if not rows:
        raise ValueError(f"广期所 {ymd} 没有行情：非交易日或尚未发布")
    return rows, response.url


# 能源中心各文件的第一天（2026-09-20 二分实测）：日行情 2018-03-26 开业即有；持仓排名 2020-07-03 起
# （07-02 仍是空壳，当时上期所排名里也没有能源品种）；期权日行情 2021-06-21 原油期权上市起
# （06-15~18 已发文件但里面没有期权合约，2026-09-22 复测）
_INE_FIRST_DAY = {"future/dailydata/kx": "20180326", "future/dailydata/pm": "20200703",
                  "option/dailydata/kx": "20210621"}


def _shfe_ine_ids(path, ymd, key, field):
    """上期所文件里混有上期能源的品种；取能源中心同一天的 ID 集合用来剔除。
    能源中心该文件第一天之前没有文件（或是空壳），上期所文件里也没有能源品种，返回空集合；
    第一天起缺文件不能当成「没有能源品种」，否则 sc 等合约会被标成上期所，直接抛 RuntimeError。"""
    payload, url = _shfe_json("INE", path, ymd, key, allow_missing=True)
    ids = {str(r[field]).strip() for r in payload[key]} if payload else set()
    if not ids and ymd >= _INE_FIRST_DAY[path]:
        raise RuntimeError(f"上期能源 {ymd} 的对照文件缺失或为空（{url}），无法从上期所数据里剔除能源品种；"
                           "可能尚未发布，稍后重试")
    return ids


@_v39_contract
def futures_daily(date, exchange):
    """期货日行情（交易所官方收盘数据）— 上期所 / 上期能源 / 郑商所 / 中金所 / 广期所。

    exchange: 'SHFE' / 'INE' / 'CZCE' / 'CFFEX' / 'GFEX'；大商所（DCE）官网有反爬，见 futures_kline / futures_realtime。
    一行一个合约（不含小计），settle 为当日结算价，turnover_10k 单位万元，价格为 0 的统一成 None。
    上期所的官方文件里也包含上期能源的品种（原油、20号胶等），这里按能源中心同日文件剔除，
    所以 SHFE 与 INE 两次调用不会重复。非交易日抛 ValueError。
    实测可用起点：上期所 2002-01-07 起（2021 年及以前没有成交额，turnover_10k 为 None）；
    上期能源 2018-03 开业；郑商所 2015-09-21 起（更早是另一套格式，未接入）；中金所 2010-04-16 开业即有；广期所 2022-12 开业。
    """
    exchange = _fut_exchange(exchange)
    day = _v39_date(date)
    ymd = day.replace("-", "")
    rows = []
    if exchange in ("SHFE", "INE"):
        payload, url = _shfe_json(exchange, "future/dailydata/kx", ymd, "o_curinstrument")
        skip = (_shfe_ine_ids("future/dailydata/kx", ymd, "o_curinstrument", "PRODUCTID")
                if exchange == "SHFE" else set())
        for r in payload["o_curinstrument"]:
            month = str(r.get("DELIVERYMONTH", "")).strip()
            product_id = r["PRODUCTID"].strip()
            # 期货品种 ID 以 _f 结尾（cu_f）；sc_tas 是原油 TAS 指令，价格恒为 0，不是独立合约。
            # 不用 PRODUCTCLASS 判断：这个字段 2023 年才出现
            if not product_id.endswith("_f") or not month.isdigit() or product_id in skip:
                continue
            rows.append({"symbol": product_id[:-2] + month,
                         "product": r["PRODUCTNAME"].strip(),
                         "open": _fut_price(r["OPENPRICE"]), "high": _fut_price(r["HIGHESTPRICE"]),
                         "low": _fut_price(r["LOWESTPRICE"]), "close": _fut_price(r["CLOSEPRICE"]),
                         "settle": _fut_price(r["SETTLEMENTPRICE"]),
                         "pre_settle": _fut_price(r["PRESETTLEMENTPRICE"]),
                         "volume": _v39_num(r["VOLUME"]), "open_interest": _v39_num(r["OPENINTEREST"]),
                         "oi_change": _v39_num(r["OPENINTERESTCHG"]),
                         "turnover_10k": _v39_num(r.get("TURNOVER"))})   # 2021 年及以前的文件没有成交额，为 None
    elif exchange == "CZCE":
        text, url = _czce_text("Future", "FutureDataDaily", ymd)
        _, table = _czce_table(text, "合约代码")
        for r in table:
            rows.append({"symbol": r["合约代码"], "product": _fut_product(r["合约代码"]),
                         "open": _fut_price(r["今开盘"]), "high": _fut_price(r["最高价"]),
                         "low": _fut_price(r["最低价"]), "close": _fut_price(r["今收盘"]),
                         "settle": _fut_price(r["今结算"]), "pre_settle": _fut_price(r["昨结算"]),
                         "volume": _v39_num(r["成交量(手)"]), "open_interest": _v39_num(r["持仓量"]),
                         "oi_change": _v39_num(r["增减量"]), "turnover_10k": _v39_num(r["成交额(万元)"])})
    elif exchange == "CFFEX":
        table, url = _cffex_daily_table(ymd)
        for rec in table[1:]:
            code = rec[0].strip()
            if not code or code in ("小计", "合计", "总计") or "-C-" in code or "-P-" in code:
                continue
            r = dict(zip(table[0], rec))
            rows.append({"symbol": code, "product": _fut_product(code),
                         "open": _fut_price(r["今开盘"]), "high": _fut_price(r["最高价"]),
                         "low": _fut_price(r["最低价"]), "close": _fut_price(r["今收盘"]),
                         "settle": _fut_price(r["今结算"]), "pre_settle": _fut_price(r["前结算"]),
                         "volume": _v39_num(r["成交量"]), "open_interest": _v39_num(r["持仓量"]),
                         "oi_change": _v39_num(r["持仓变化"]), "turnover_10k": _v39_num(r["成交金额"])})
    else:
        data, url = _gfex_rows(ymd, 0)
        for r in data:
            rows.append({"symbol": r["varietyOrder"] + r["delivMonth"], "product": r["variety"],
                         "open": _fut_price(r["open"]), "high": _fut_price(r["high"]),
                         "low": _fut_price(r["low"]), "close": _fut_price(r["close"]),
                         "settle": _fut_price(r["clearPrice"]), "pre_settle": _fut_price(r["lastClear"]),
                         "volume": _v39_num(r["volumn"]), "open_interest": _v39_num(r["openInterest"]),
                         "oi_change": _v39_num(r["diffI"]), "turnover_10k": _v39_num(r["turnover"])})
    if not rows:
        raise RuntimeError(f"{exchange} {day} 解析出 0 个期货合约，格式可能已变")
    for row in rows:
        row["date"], row["exchange"] = day, exchange
    frame = _v39_frame(rows, exchange.lower(), url, _FUT_COLUMNS)
    if frame.duplicated(["symbol"]).any():
        raise RuntimeError(f"{exchange} {day} 期货合约代码重复")
    return frame


# 郑商所 CF/RM/OI/SR 另有带两位字母后缀的系列（如 CF701MSC14400），后缀并入 series 原样保留
_OPTION_CODE = re.compile(r"^([A-Za-z]+\d{3,4}(?:[A-Z]{2})?)-?([CP])-?(\d+(?:\.\d+)?)$")


@_v39_contract
def options_daily(date, exchange):
    """商品期权 / 股指期权日行情（交易所官方）— 上期所 / 上期能源 / 郑商所 / 中金所 / 广期所。

    series：期权系列（商品期权 = 标的期货合约，如 cu2610；中金所 = HO/IO/MO + 月份；
    郑商所部分品种另有 CF701MS 这类带后缀的系列，按官方代码原样保留，与 CF701 分开）。
    delta：交易所公布值（中金所不公布，为 None）。
    iv_pct：逐合约隐含波动率 %（郑商所、广期所公布）；series_iv_pct：上期所/能源中心按系列公布的
    隐含波动率（官方 SIGMA × 100）。ETF 期权不在这里，见 Layer 9。非交易日抛 ValueError。
    各所期权上市时间不同（上期所铜期权 2018-09、郑商所白糖期权 2017-04），之前的日期抛 ValueError。
    """
    exchange = _fut_exchange(exchange)
    day = _v39_date(date)
    ymd = day.replace("-", "")
    rows = []
    if exchange in ("SHFE", "INE"):
        payload, url = _shfe_json(exchange, "option/dailydata/kx", ymd, "o_curinstrument")
        skip = (_shfe_ine_ids("option/dailydata/kx", ymd, "o_curinstrument", "PRODUCTID")
                if exchange == "SHFE" else set())
        sigma_rows = _v39_rows(payload.get("o_cursigma"), f"{exchange} {url} 的 o_cursigma")
        if not all("INSTRUMENTID" in r for r in sigma_rows):
            raise RuntimeError(f"{exchange} {url} 的 o_cursigma 行没有 INSTRUMENTID")
        # 字典推导会让重复的 INSTRUMENTID 静默相互覆盖，返回错误的隐含波动率。
        # 2026-09-20 抽查 10 个交易日（2018-09-21 期权首日起）：只有按品种汇总的「小计」行
        # 重复且 SIGMA 恒为空，真实系列 ID 不重复、SIGMA 无空值。
        sigma = {}
        for r in sigma_rows:
            series_id = str(r["INSTRUMENTID"]).strip()
            if series_id in ("小计", "合计", "总计"):
                continue
            if not series_id:
                raise RuntimeError(f"{exchange} {url} 的 o_cursigma 有空的 INSTRUMENTID")
            if series_id in sigma:
                raise RuntimeError(f"{exchange} {url} 的 o_cursigma 里 {series_id} 出现两次，"
                                   "隐含波动率会互相覆盖")
            sigma[series_id] = _v39_req_num(r.get("SIGMA"), f"{exchange} {series_id} 的 SIGMA")
        for r in payload["o_curinstrument"]:
            code = str(r.get("INSTRUMENTID", "")).strip()
            kind = {"1": "C", "2": "P"}.get(str(r.get("OPTIONSTYPE")))
            if kind is None or r["PRODUCTID"].strip() in skip:
                continue                        # 小计 / 总计 行 OPTIONSTYPE 为空
            parsed = _OPTION_CODE.match(code)
            if not parsed or parsed.group(2) != kind:
                raise RuntimeError(f"{exchange} 期权 {code} 的代码与 OPTIONSTYPE={r.get('OPTIONSTYPE')} 不一致")
            series = str(r["UNDERLYINGINSTRID"]).strip()
            if series not in sigma:     # 实测 10 个交易日里主表每个系列都有 sigma 行
                raise RuntimeError(f"{exchange} {url} 的 o_cursigma 里没有系列 {series}，结果不完整")
            iv = sigma[series]
            rows.append({"symbol": code, "series": series, "option_type": kind,
                         "strike": _v39_num(r["STRIKEPRICE"]),
                         "open": _fut_price(r["OPENPRICE"]), "high": _fut_price(r["HIGHESTPRICE"]),
                         "low": _fut_price(r["LOWESTPRICE"]), "close": _fut_price(r["CLOSEPRICE"]),
                         "settle": _fut_price(r["SETTLEMENTPRICE"]),
                         "pre_settle": _fut_price(r["PRESETTLEMENTPRICE"]),
                         "volume": _v39_num(r["VOLUME"]), "open_interest": _v39_num(r["OPENINTEREST"]),
                         "oi_change": _v39_num(r["OPENINTERESTCHG"]), "turnover_10k": _v39_num(r["TURNOVER"]),
                         "delta": _v39_num(r.get("DELTA")), "iv_pct": None,
                         "series_iv_pct": round(iv * 100, 4) if iv is not None else None})
    elif exchange == "CZCE":
        text, url = _czce_text("Option", "OptionDataDaily", ymd)
        if "无交易记录" in text:
            raise ValueError(f"郑商所 {ymd} 没有期权成交记录（郑商所期权 2017-04-19 起上市）")
        _, table = _czce_table(text, "合约代码")
        for r in table:
            parsed = _OPTION_CODE.match(r["合约代码"])
            if not parsed:
                raise RuntimeError(f"郑商所期权代码无法解析: {r['合约代码']}")
            rows.append({"symbol": r["合约代码"], "series": parsed.group(1), "option_type": parsed.group(2),
                         "strike": _v39_num(parsed.group(3)),
                         "open": _fut_price(r["今开盘"]), "high": _fut_price(r["最高价"]),
                         "low": _fut_price(r["最低价"]), "close": _fut_price(r["今收盘"]),
                         "settle": _fut_price(r["今结算"]), "pre_settle": _fut_price(r["昨结算"]),
                         "volume": _v39_num(r["成交量(手)"]), "open_interest": _v39_num(r["持仓量"]),
                         "oi_change": _v39_num(r["增减量"]), "turnover_10k": _v39_num(r["成交额(万元)"]),
                         "delta": _v39_num(r["DELTA"]), "iv_pct": _v39_num(r["隐含波动率"]),
                         "series_iv_pct": None})
    elif exchange == "CFFEX":
        table, url = _cffex_daily_table(ymd)
        for rec in table[1:]:
            code = rec[0].strip()
            if "-C-" not in code and "-P-" not in code:
                continue
            parsed = _OPTION_CODE.match(code)
            if not parsed:
                raise RuntimeError(f"中金所期权代码无法解析: {code}")
            r = dict(zip(table[0], rec))
            rows.append({"symbol": code, "series": parsed.group(1), "option_type": parsed.group(2),
                         "strike": _v39_num(parsed.group(3)),
                         "open": _fut_price(r["今开盘"]), "high": _fut_price(r["最高价"]),
                         "low": _fut_price(r["最低价"]), "close": _fut_price(r["今收盘"]),
                         "settle": _fut_price(r["今结算"]), "pre_settle": _fut_price(r["前结算"]),
                         "volume": _v39_num(r["成交量"]), "open_interest": _v39_num(r["持仓量"]),
                         "oi_change": _v39_num(r["持仓变化"]), "turnover_10k": _v39_num(r["成交金额"]),
                         "delta": None, "iv_pct": None, "series_iv_pct": None})
    else:
        data, url = _gfex_rows(ymd, 1)
        for r in data:
            parsed = _OPTION_CODE.match(r["delivMonth"])
            if not parsed:
                raise RuntimeError(f"广期所期权代码无法解析: {r['delivMonth']}")
            rows.append({"symbol": r["delivMonth"], "series": parsed.group(1), "option_type": parsed.group(2),
                         "strike": _v39_num(parsed.group(3)),
                         "open": _fut_price(r["open"]), "high": _fut_price(r["high"]),
                         "low": _fut_price(r["low"]), "close": _fut_price(r["close"]),
                         "settle": _fut_price(r["clearPrice"]), "pre_settle": _fut_price(r["lastClear"]),
                         "volume": _v39_num(r["volumn"]), "open_interest": _v39_num(r["openInterest"]),
                         "oi_change": _v39_num(r["diffI"]), "turnover_10k": _v39_num(r["turnover"]),
                         "delta": _v39_num(r["delta"]), "iv_pct": _v39_num(r["impliedVolatility"]),
                         "series_iv_pct": None})
    if not rows:
        raise RuntimeError(f"{exchange} {day} 解析出 0 个期权合约，格式可能已变")
    for row in rows:
        row["date"], row["exchange"] = day, exchange
    frame = _v39_frame(rows, exchange.lower(), url, _OPT_COLUMNS)
    if frame.duplicated(["symbol"]).any():
        raise RuntimeError(f"{exchange} {day} 期权合约代码重复")
    return frame


def _rank_member(value):
    value = str(value or "").strip()
    return value if value and value != "-" else None


@_v39_contract
def futures_position_rank(date, exchange, symbol=None):
    """期货会员成交量 / 持买单 / 持卖单前 20 名（交易所官方持仓排名）。

    exchange: 'SHFE' / 'INE' / 'CZCE' / 'CFFEX'（广期所、大商所未接入）。
    level='contract' 为单个合约；level='product' 为品种合计，只有郑商所公布（symbol 为品种字母，如 AP）。
    上期所 / 能源中心文件里的 cuall 行是按会员类型的汇总、没有名次，已剔除。
    symbol 可选，按合约或品种过滤（不区分大小写）。中金所按 IF/IH/IC/IM/TS/TF/T/TL 各取一个文件，
    当天已上市的品种缺任何一个都抛 RuntimeError（不返回部分品种）；source_url 列出实际读取的文件。
    上期能源 2019 年的排名文件是空的（抛 ValueError），实测 2021 年起有数据。
    """
    exchange = _fut_exchange(exchange)
    if exchange == "GFEX":
        raise ValueError("广期所持仓排名未接入")
    day = _v39_date(date)
    ymd = day.replace("-", "")
    rows = []
    if exchange in ("SHFE", "INE"):
        payload, url = _shfe_json(exchange, "future/dailydata/pm", ymd, "o_cursor")
        skip = (_shfe_ine_ids("future/dailydata/pm", ymd, "o_cursor", "INSTRUMENTID")
                if exchange == "SHFE" else set())
        for r in payload["o_cursor"]:
            code = str(r["INSTRUMENTID"]).strip()
            rank = _v39_num(r["RANK"])
            if rank is None:
                raise RuntimeError(f"{exchange} {code} 持仓排名缺名次字段")
            # RANK 1–20 为会员名次；999 = 该合约合计，-1 / 0 = 按会员类型汇总
            if not 1 <= rank <= 20 or code in skip:
                continue
            rows.append({"level": "contract", "symbol": code,
                         "rank": int(rank),
                         "volume_member": _rank_member(r["PARTICIPANTABBR1"]), "volume": _v39_num(r["CJ1"]),
                         "volume_chg": _v39_num(r["CJ1_CHG"]),
                         "long_member": _rank_member(r["PARTICIPANTABBR2"]), "long_oi": _v39_num(r["CJ2"]),
                         "long_chg": _v39_num(r["CJ2_CHG"]),
                         "short_member": _rank_member(r["PARTICIPANTABBR3"]), "short_oi": _v39_num(r["CJ3"]),
                         "short_chg": _v39_num(r["CJ3_CHG"])})
    elif exchange == "CZCE":
        text, url = _czce_text("Future", "FutureDataHolding", ymd)
        level = code = None
        for line in text.splitlines():
            head = re.match(r"^(品种|合约)：\s*(\S+)\s+日期：", line)
            if head:
                level = "product" if head.group(1) == "品种" else "contract"
                found = re.search(r"[A-Za-z]+\d*$", head.group(2))
                if not found:
                    raise RuntimeError(f"郑商所持仓排名表头认不出品种 / 合约: {line[:60]}")
                code = found.group(0)
                continue
            cells = [c.strip().replace(",", "") for c in line.split("|")]
            if len(cells) < 10 or not cells[0].isdigit():
                continue                        # 表头、合计行
            if code is None:
                raise RuntimeError("郑商所持仓排名在品种/合约标题之前出现数据行")
            rows.append({"level": level, "symbol": code, "rank": int(cells[0]),
                         "volume_member": _rank_member(cells[1]), "volume": _v39_num(cells[2]),
                         "volume_chg": _v39_num(cells[3]),
                         "long_member": _rank_member(cells[4]), "long_oi": _v39_num(cells[5]),
                         "long_chg": _v39_num(cells[6]),
                         "short_member": _rank_member(cells[7]), "short_oi": _v39_num(cells[8]),
                         "short_chg": _v39_num(cells[9])})
    else:
        expected = [p for p, first in CFFEX_RANK_FIRST_DAY.items() if ymd >= first]
        if not expected:
            raise ValueError("中金所持仓排名从 2010-04-16（沪深300 期货上市）起才有")
        urls, missing = [], []
        for product in expected:                # 当时还没上市的品种（如 2022 年前的 IM）不请求
            file_url = CFFEX_RANK_URL.format(ym=ymd[:6], dd=ymd[6:], product=product)
            table = _cffex_csv(file_url, allow_missing=True)
            if table is None:
                missing.append(product)
                continue
            urls.append(file_url)
            parsed = _cffex_rank_rows(table, product, ymd)
            rows.extend(parsed)
            if not parsed:
                raise RuntimeError(f"中金所 {product} {day} 持仓排名文件解析出 0 行，格式可能已变")
        if len(missing) == len(expected):
            raise ValueError(f"中金所 {day} 没有持仓排名：非交易日或尚未发布")
        if missing:
            raise RuntimeError(f"中金所 {day} 缺少已上市品种 {'/'.join(missing)} 的持仓排名，结果不完整"
                               "（可能尚未全部发布，稍后重试）")
        url = " | ".join(urls)
    if not rows:
        raise RuntimeError(f"{exchange} {day} 持仓排名解析出 0 行，格式可能已变")
    for row in rows:
        row["date"], row["exchange"] = day, exchange
    frame = _v39_frame(rows, exchange.lower(), url, _RANK_COLUMNS)
    if frame.duplicated(["level", "symbol", "rank"]).any():
        raise RuntimeError(f"{exchange} {day} 持仓排名 合约+名次 重复")
    if symbol:
        frame = frame[frame["symbol"].str.upper() == str(symbol).upper()].reset_index(drop=True)
    return frame


def _sina_hq(codes):
    response = _v39_http(SINA_HQ_URL + ",".join(codes), headers={"Referer": "https://finance.sina.com.cn/"})
    out = {}
    for key, body in re.findall(r'var hq_str_([^=]+)="([^"]*)"', response.content.decode("gbk", "replace")):
        out[key] = body.split(",") if body else []
    # 代码不存在时新浪照样回一个空内容的变量（实测 nf_ZZ9999）；一个变量都没有说明页面变了，
    # 否则会把格式改变报成「代码不存在或已摘牌」
    if not out:
        raise RuntimeError(f"新浪行情页没有 hq_str 变量（{response.url}），格式可能已变")
    return out, response.url


@_v39_contract
def futures_realtime(symbols):
    """国内期货实时行情（新浪）— 覆盖全部六家交易所，大商所品种只能走这里。

    symbols: 'RB0'（主力连续）/ 'CU2610' / 'IF2609' / 'M0' 等，可传列表；带不带 'nf_' 前缀都行。
    中金所品种（IF/IH/IC/IM/TS/TF/T/TL）另有 pre_close / 涨跌停价。无效代码抛 ValueError。
    盘中是实时价；收盘后是当日收盘快照，结算价以 futures_daily 为准。
    """
    if isinstance(symbols, str):
        symbols = [symbols]
    if not isinstance(symbols, (list, tuple, set)) or not symbols:
        raise ValueError("symbols 需为非空的代码或代码列表（例 'RB0' / ['RB0', 'IF2609']）")
    codes = []
    for raw in symbols:
        code = str(raw).strip()
        code = code[3:] if code.lower().startswith("nf_") else code
        if not re.fullmatch(r"[A-Za-z]{1,2}\d{1,4}", code):
            raise ValueError(f"期货代码格式不对: {raw}（例 RB0 / CU2610 / IF2609）")
        codes.append(code.upper())
    data, url = _sina_hq(["nf_" + c for c in codes])
    rows = []
    for code in codes:
        fields = data.get("nf_" + code)
        if not fields:
            raise ValueError(f"新浪没有期货 {code} 的行情（代码不存在或已摘牌）")
        product = _fut_product(code)
        if product in _CFFEX_SINA_PRODUCTS:
            if len(fields) < 50:
                raise RuntimeError(f"新浪中金所期货 {code} 字段数 {len(fields)}，格式可能已变")
            rows.append({"symbol": code, "name": fields[49], "datetime": f"{fields[36]} {fields[37]}",
                         "open": _fut_price(fields[0]), "high": _fut_price(fields[1]),
                         "low": _fut_price(fields[2]), "last": _fut_price(fields[3]),
                         "bid": _fut_price(fields[16]), "ask": _fut_price(fields[26]),
                         "bid_vol": _v39_num(fields[17]), "ask_vol": _v39_num(fields[27]),
                         "volume": _v39_num(fields[4]), "open_interest": _v39_num(fields[6]),
                         "pre_settle": _fut_price(fields[14]), "pre_close": _fut_price(fields[13]),
                         "upper_limit": _fut_price(fields[9]), "lower_limit": _fut_price(fields[10]),
                         "avg_price": _fut_price(fields[48])})
        else:
            if len(fields) < 28:
                raise RuntimeError(f"新浪商品期货 {code} 字段数 {len(fields)}，格式可能已变")
            clock = fields[1].zfill(6)
            rows.append({"symbol": code, "name": fields[0],
                         "datetime": f"{fields[17]} {clock[:2]}:{clock[2:4]}:{clock[4:]}",
                         "open": _fut_price(fields[2]), "high": _fut_price(fields[3]),
                         "low": _fut_price(fields[4]), "last": _fut_price(fields[8]),
                         "bid": _fut_price(fields[6]), "ask": _fut_price(fields[7]),
                         "bid_vol": _v39_num(fields[11]), "ask_vol": _v39_num(fields[12]),
                         "volume": _v39_num(fields[14]), "open_interest": _v39_num(fields[13]),
                         "pre_settle": _fut_price(fields[10]), "pre_close": None,
                         "upper_limit": None, "lower_limit": None, "avg_price": _fut_price(fields[27])})
    return _v39_frame(rows, "sina", url)


@_v39_contract
def futures_kline(symbol, start=None, end=None):
    """国内期货日 K 线（新浪）— 单个合约或主力连续的逐日序列，覆盖全部六家交易所（含大商所）。

    symbol: 'RB0' / 'M0'（主力连续）或 'RB2601' / 'M2601' / 'IF2612'；郑商所也写 4 位年月（'MA2601'），带不带 'nf_' 前缀都行。
    start/end: 'YYYY-MM-DD'，可只给一端。主力连续换月当天会跳空，未做复权。
    实测（2026-09-22）价格与交易所官方 futures_daily 逐日一致，成交量 / 持仓偶有 ≤0.1% 的出入，精确值以 futures_daily 为准。
    结算价新浪给得不全（给 0 的统一成 None）：中金所品种基本没有；主力连续早年缺得多（CU0 5285 根缺 1364 根，
    最晚缺到 2024-09-25），需要结算价用 futures_daily。具体合约只能取到约 2022 年起到期的，更早的新浪返回空。
    代码不存在 / 太老、区间内没有 K 线抛 ValueError；返回格式改变抛 RuntimeError。
    """
    code = str(symbol).strip()
    code = code[3:] if code.lower().startswith("nf_") else code
    if not re.fullmatch(r"[A-Za-z]{1,2}\d{1,4}", code):
        raise ValueError(f"期货代码格式不对: {symbol}（例 RB0 / RB2601 / MA2601）")
    code = code.upper()
    lo = _v39_date(start) if start else None
    hi = _v39_date(end) if end else None
    if lo and hi and lo > hi:
        raise ValueError(f"start {lo} 晚于 end {hi}")
    response = _v39_http(SINA_FUT_KLINE_URL.format(code=code), params={"symbol": code},
                         headers={"Referer": "https://finance.sina.com.cn/"})
    text = response.content.decode("gbk", "replace")
    match = re.search(rf"var _{re.escape(code)}=\((.*)\);?\s*$", text, re.S)
    if not match:
        raise RuntimeError(f"新浪期货日 K {code} 的返回不是预期的 JSONP（{response.url}），格式可能已变")
    body = match.group(1).strip()
    if body == "null":
        raise ValueError(f"新浪没有期货 {code} 的日 K：代码不存在，或是约 2022 年以前到期的老合约"
                         "（郑商所也要写 4 位年月，如 MA2601）")
    try:
        items = json.loads(body)
    except ValueError as exc:
        raise RuntimeError(f"新浪期货日 K {code} 的返回不是 JSON，格式可能已变") from exc
    rows, seen = [], set()
    for r in _v39_rows(items, f"新浪期货日 K {code}"):
        day = _v39_src_date(r["d"])
        if day in seen:
            raise RuntimeError(f"新浪期货日 K {code} 同一天 {day} 出现两次，结果不可信")
        seen.add(day)
        if (lo and day < lo) or (hi and day > hi):
            continue
        rows.append({"date": day, "symbol": code,
                     "open": _fut_price(r["o"]), "high": _fut_price(r["h"]),
                     "low": _fut_price(r["l"]), "close": _fut_price(r["c"]),
                     "settle": _fut_price(r["s"]),       # 新浪没有结算价时给 0 → None
                     "volume": _v39_num(r["v"]), "open_interest": _v39_num(r["p"])})
    if not rows:
        raise ValueError(f"新浪期货 {code} 在所给区间内没有日 K（合约当时未上市或已到期）")
    rows.sort(key=lambda row: row["date"])
    return _v39_frame(rows, "sina", response.url,
                      ["date", "symbol", "open", "high", "low", "close", "settle", "volume", "open_interest"])


@_v39_contract
def a50_futures():
    """富时中国 A50 期指（新浪 hf_CHA50CFD，连续合约报价）— 盘前/夜盘看 A 股外资情绪。"""
    data, url = _sina_hq(["hf_CHA50CFD"])
    fields = data.get("hf_CHA50CFD")
    if not fields or len(fields) < 14:
        raise RuntimeError("新浪 A50 期指行情为空或字段数不对")
    row = {"name": fields[13], "datetime": f"{fields[12]} {fields[6]}",
           "last": _fut_price(fields[0]), "open": _fut_price(fields[8]),
           "high": _fut_price(fields[4]), "low": _fut_price(fields[5]),
           "bid": _fut_price(fields[2]), "ask": _fut_price(fields[3]),
           "pre_settle": _fut_price(fields[7])}
    if row["last"] is None:
        raise RuntimeError("新浪 A50 期指最新价为空")
    return _v39_frame([row], "sina", url)


@_v39_contract
def sge_spot(instrument="Au99.99"):
    """上海黄金交易所现货日线（官方）— 2016-12 至今。

    instrument 例: 'Au99.99' / 'Au(T+D)' / 'mAu(T+D)' / 'Ag(T+D)' / 'Ag99.99' / 'Pt99.95'。
    黄金单位 元/克，白银 元/千克。无成交日交易所填 0，这里剔除；代码不存在时上金所返回全 0，抛 ValueError。
    少数日子收盘价略超出高低区间是原始数据如此，日期列在 attrs['ohlc_anomaly_dates']。
    """
    response = _v39_http(SGE_DAILY_URL, method="POST", data={"instid": instrument},
                         headers={"Referer": "https://www.sge.com.cn/"})
    payload = _v39_json(response)
    series = payload.get("time") if isinstance(payload, dict) else None
    if not isinstance(series, list):
        raise RuntimeError("上金所日线返回结构改变")
    rows = []
    for rec in series:
        if not isinstance(rec, list) or len(rec) != 5:
            raise RuntimeError(f"上金所日线字段数不对: {rec}")
        prices = [_v39_num(v) for v in rec[1:]]
        # 实测 7 个品种约 1.5 万条全是数字，无成交填 0；空值 / NaN 说明格式变了，不能当无成交跳过
        if None in prices:
            raise RuntimeError(f"上金所日线出现空值或非有限数值: {rec}")
        if not all(prices):
            continue
        open_, close, low, high = prices
        rows.append({"date": _v39_src_date(rec[0]), "instrument": instrument, "open": open_,
                     "high": high, "low": low, "close": close})
    if not rows:
        raise ValueError(f"上金所没有 {instrument} 的有效行情（代码不存在时返回全 0）")
    # 实测 Au99.99 在 2017–2018 年有 17 天收盘价略超出当日高低区间（上金所原始数据如此，
    # 不是高低列颠倒）。个别日子保留原值、记在 attrs；大面积不成立才说明字段顺序变了。
    bad = [r["date"] for r in rows if not r["low"] <= min(r["open"], r["close"]) <= max(r["open"], r["close"]) <= r["high"]]
    if len(bad) > 0.05 * len(rows):
        raise RuntimeError(f"上金所日线 {len(bad)}/{len(rows)} 天高低开收关系不成立，字段顺序可能已变")
    frame = _v39_frame(rows, "sge", response.url)
    frame.attrs["ohlc_anomaly_dates"] = bad
    return frame


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="macro-data-", suffix=".json", delete=False) as stream:
            stage = Path(stream.name)
            stream.write(encoded + "\n")
        if output is None:
            result, stage = stage, None
            return result.resolve()
        # 优先原子发布；仅链接能力受限时降级，不掩盖目标冲突、磁盘满等错误。
        import errno
        import shutil
        try:
            os.link(stage, output)
        except (OSError, NotImplementedError) as exc:
            unsupported = {errno.EPERM, errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP}
            if isinstance(exc, OSError) and exc.errno not in unsupported:
                raise
            created = None
            try:
                # xb 使用独占创建，目标在此刻出现（含悬空符号链接）也不会覆盖。
                # 此兼容路径写完前目标可见；消费者须等待 CLI 成功再读取。
                with Path(output).open("xb") as destination:
                    created = os.fstat(destination.fileno())
                    with stage.open("rb") as source:
                        shutil.copyfileobj(source, destination)
            except BaseException:
                # 清理自己创建的半成品；不要删除已被其他进程替换的文件。
                if created is not None:
                    try:
                        current = Path(output).lstat()
                    except FileNotFoundError:
                        pass
                    else:
                        if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                            Path(output).unlink()
                raise
        return Path(output).resolve()
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)


def _json_safe(value):
    """保留缺失值、非有限值和日期类型，不使用 default=str。"""
    from datetime import date, datetime
    import math
    import pandas as pd

    if value is pd.NA:
        return {"$missing": "NA"}
    if value is pd.NaT:
        return {"$missing": "NaT"}
    if isinstance(value, (datetime, date)):
        return {"$date_type": type(value).__name__, "iso": value.isoformat()}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {"$float": "NaN" if math.isnan(value) else
                                                   "Infinity" if value > 0 else "-Infinity"}
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON 对象键必须为字符串")
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return _json_safe(value.item())
    raise TypeError(f"无法无歧义地序列化 {type(value).__name__}")


def _index_payload(index):
    """保存 表格多层列名及其层级编码。"""
    if isinstance(index, pd.CategoricalIndex):
        raise TypeError("CLI 暂不支持分类索引，请用 Python API")
    result = {"type": type(index).__name__}
    if isinstance(index, pd.MultiIndex):
        result.update(names=list(index.names), levels=[_index_payload(level) for level in index.levels],
                      codes=[list(code) for code in index.codes], sortorder=index.sortorder)
    else:
        result.update(name=index.name, dtype=str(index.dtype), values=list(index))
        if isinstance(index, pd.RangeIndex):
            result.update(start=index.start, stop=index.stop, step=index.step)
        elif isinstance(index, pd.DatetimeIndex):
            result.update(tz=str(index.tz) if index.tz is not None else None, freq=index.freqstr)
    return result


def _frame_payload(frame):
    if any(isinstance(dtype, pd.CategoricalDtype) for dtype in frame.dtypes):
        raise TypeError("CLI 暂不支持分类列，请用 Python API")
    return _json_safe({"type": "DataFrame", "columns": list(frame.columns),
                       "columns_index": _index_payload(frame.columns),
                       "dtypes": [str(dtype) for dtype in frame.dtypes], "index": _index_payload(frame.index),
                       "attrs": dict(frame.attrs), "data": list(frame.itertuples(index=False, name=None))})


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description='期货、期权、持仓与现货完整数据')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('daily', 'options', 'rank'):
        command = commands.add_parser(name)
        command.add_argument('date')
        command.add_argument('exchange')
        if name == 'rank':
            command.add_argument('--symbol')
        command.add_argument('--output', type=Path)
    realtime = commands.add_parser('realtime')
    realtime.add_argument('symbols', nargs='+')
    realtime.add_argument('--output', type=Path)
    kline = commands.add_parser('kline')
    kline.add_argument('symbol')
    kline.add_argument('--start')
    kline.add_argument('--end')
    kline.add_argument('--output', type=Path)
    a50 = commands.add_parser('a50')
    a50.add_argument('--output', type=Path)
    spot = commands.add_parser('spot')
    spot.add_argument('--instrument', default='Au99.99')
    spot.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error('输出路径已存在，请指定新路径')
    try:
        if args.command == 'daily':
            frame = futures_daily(args.date, args.exchange)
        elif args.command == 'options':
            frame = options_daily(args.date, args.exchange)
        elif args.command == 'rank':
            frame = futures_position_rank(args.date, args.exchange, args.symbol)
        elif args.command == 'realtime':
            frame = futures_realtime(args.symbols)
        elif args.command == 'kline':
            frame = futures_kline(args.symbol, args.start, args.end)
        elif args.command == 'a50':
            frame = a50_futures()
        else:
            frame = sge_spot(args.instrument)
        payload = _frame_payload(frame)
        preview = _frame_payload(frame.head(3))
        path = _save_payload(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2), args.output)
        print(json.dumps({'output': str(path), 'row_count': len(frame), 'preview_only': True,
                          'preview': preview}, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
