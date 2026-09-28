# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""官方宏观数据，保留源单位与日期解析规则。"""
import _runtime  # noqa: F401  须在第三方库之前导入
import io
import re
from typing import Optional

import pandas as pd
import requests

_UA = {"User-Agent": "Mozilla/5.0"}
PBC_BASE = "https://www.pbc.gov.cn"
PBC_INDEX = f"{PBC_BASE}/diaochatongjisi/116219/116319/index.html"


def _macro_get(url: str, timeout: int = 30) -> str:
    r = requests.get(url, headers=_UA, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def _abs_pbc(href: str) -> str:
    return href if href.startswith("http") else PBC_BASE + href


def pboc_social_financing(year: Optional[int] = None) -> pd.DataFrame:
    """人民银行「社会融资规模增量统计表」— 月度，单位亿元；year=None 取最新年"""
    idx = _macro_get(PBC_INDEX)
    years = re.findall(r"""href=["']([^"']+)["'][^>]*>\s*(\d{4})年统计数据\s*</a>""", idx)
    if not years:
        raise RuntimeError("人民银行索引页未找到「XXXX年统计数据」链接，页面结构可能已变更")
    table = {int(y): href for href, y in years}
    target = max(table) if year is None else year
    if target not in table:
        raise ValueError(f"人民银行无 {target} 年数据，可选年份: {sorted(table, reverse=True)[:8]}")

    ypage = _macro_get(_abs_pbc(table[target]))
    topics = re.findall(r"""href=["']([^"']+)["'][^>]*>\s*(社会融资规模)\s*</a>""", ypage)
    if not topics:
        raise RuntimeError(f"{target} 年页未找到「社会融资规模」专题链接")

    tpage = _macro_get(_abs_pbc(topics[0][0]))
    books = re.findall(r"""href=["']([^"']+\.xlsx?)["']""", tpage)
    if not books:
        raise RuntimeError(f"{target} 年社融专题页未找到 xls/xlsx 附件")

    content = requests.get(_abs_pbc(books[0]), headers=_UA, timeout=60).content
    raw = pd.read_excel(io.BytesIO(content), header=None)

    start = None                      # 表头是中英双行 + 单位说明，用「月份」列定位数据起点
    for i in range(len(raw)):
        if str(raw.iloc[i, 0]).strip() == "月份":
            start = i
            break
    if start is None:
        raise RuntimeError(
            f"{target} 年社融表没有独立的「月份」表头单元格。"
            "**2020 及更早采用旧版式**（表头与项目名合并在同一单元格，且附表含 2017 年以来的历史区），"
            "本端点仅支持 **2021 年起**（2026-08-19 实测 2021~2026 全部可解析）。"
        )

    cols = ["month", "afre_total", "rmb_loans", "fx_loans", "entrusted_loans",
            "trust_loans", "undiscounted_bankers_acceptance", "corporate_bonds",
            "government_bonds", "equity_financing", "abs_by_depository", "loans_written_off"]
    df = raw.iloc[start + 3:].copy().iloc[:, :len(cols)]
    df.columns = cols
    df = df[df["month"].astype(str).str.match(r"^\d{4}\.\d{1,2}$", na=False)].copy()
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    def _month_label(v):
        """`2026.01` → 2026-01；`2026.1` → 2026-10。

        Excel 把 `2026.10` 的尾零吃掉读成浮点 `2026.1`，与 1 月的 `2026.01` 撞车。
        1 月在表里始终写作两位 `.01`，因此**单个小数位必然是被吃了尾零的 x0 月**。
        按单元格逐行解析（而不是按行序编号），跨年工作簿也不会错位。
        """
        m = re.match(r"^(\d{4})\.(\d{1,2})$", str(v).strip())
        if not m:
            return None
        year_s, mon_s = m.group(1), m.group(2)
        if len(mon_s) == 1:
            mon_s += "0"
        return f"{year_s}-{int(mon_s):02d}"

    df["month"] = [_month_label(v) for v in df["month"]]
    df = df[df["month"].notna()]
    # 旧工作簿底部会附「表1：2017年以来各月…」的历史区，只保留目标年，防跨年污染
    df = df[df["month"].str.startswith(f"{target}-")].reset_index(drop=True)

    # 未发布月份整行为空 —— 必须丢掉，否则调用方会把 12 行当成 12 个月的真数据。
    df = df.dropna(subset=["afre_total"]).reset_index(drop=True)
    if df.empty:
        raise RuntimeError(f"社融表解析后无有效月份（{target} 年），格式可能已变更")
    return df



import re

import requests

NBS_INDEX = "https://www.stats.gov.cn/sj/zxfb/"
_UA = {"User-Agent": "Mozilla/5.0"}


def _macro_get(url: str, timeout: int = 30) -> str:
    """与 §11.1 同名同实现 —— 本块按「端点路由速查」单独取用时也能独立跑，
    不必先执行 §11.1。两处同时执行时后定义覆盖前者，行为一致，无副作用。"""
    r = requests.get(url, headers=_UA, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def nbs_pmi() -> dict:
    """国家统计局最新 PMI — 制造业 / 非制造业商务活动 / 综合产出 + 大中小型企业"""
    idx = _macro_get(NBS_INDEX)
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>\s*([^<]{6,80}?)\s*</a>', idx)
    hit = next(((u, t) for u, t in links if "采购经理指数" in t), None)
    if not hit:
        raise RuntimeError("国家统计局最新发布页未找到「采购经理指数」条目")
    href, title = hit
    url = href if href.startswith("http") else NBS_INDEX + href.lstrip("./")

    html = _macro_get(url)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    # 🔴 正文是全角括号且**括号内带空格**（`（ PMI ）为 49.2%`）。
    #    必须把空白**整个删掉**；只做「压成单个空格」会一条都匹配不到。
    text = re.sub(r"[\s\u3000\xa0]+", "", text)

    def grab(pat):
        m = re.search(pat, text)
        return float(m.group(1)) if m else None

    ym = re.search(r"(\d{4})年(\d{1,2})月", title)

    # 分档措辞统计局用过三种版式，逐层回退；解析不到留 None（属可选字段）。
    #   ① 全合并：大、中、小型企业PMI分别为 A%、B%和C%
    #   ② 半拆：  大型企业PMI为 A%…；中、小型企业PMI分别为 B%和C%
    #   ③ 全拆：  大型企业PMI为 A%…；中型企业PMI为 B%…；小型企业PMI为 C%
    # 注：③ 的单条正则要求「…企业PMI为」，不会误匹配 ①② 里的「…企业PMI分别为」。
    large = medium = small = None
    combined = re.search(r"大、中、小型企业PMI分别为([\d.]+)%、([\d.]+)%和([\d.]+)%", text)
    if combined:
        large, medium, small = (float(x) for x in combined.groups())
    else:
        m_ms = re.search(r"中、小型企业PMI分别为([\d.]+)%和([\d.]+)%", text)
        if m_ms:                            # ② 中小型合并一句
            medium, small = (float(x) for x in m_ms.groups())
        for _name, _pat in (("large", r"大型企业PMI为([\d.]+)%"),
                            ("medium", r"中型企业PMI为([\d.]+)%"),
                            ("small", r"小型企业PMI为([\d.]+)%")):
            _m = re.search(_pat, text)      # ③ 各自单独成句
            if _m:
                _v = float(_m.group(1))
                if _name == "large":
                    large = _v
                elif _name == "medium" and medium is None:
                    medium = _v
                elif _name == "small" and small is None:
                    small = _v

    result = {
        "title": title.strip(),
        "period": f"{ym.group(1)}-{int(ym.group(2)):02d}" if ym else None,
        "manufacturing_pmi": grab(r"(?<!非)制造业采购经理指数（PMI）为([\d.]+)%"),
        "non_manufacturing_pmi": grab(r"非制造业商务活动指数为([\d.]+)%"),
        "composite_pmi": grab(r"综合PMI产出指数为([\d.]+)%"),
        "pmi_large": large,
        "pmi_medium": medium,
        "pmi_small": small,
        "source_url": url,
    }
    # 三个主指标是本端点的承诺输出，解析不到必须 fail-fast ——
    # 统计局改一次措辞就静默返回一串 None，调用方会当成「本月没数据」。
    core = ("manufacturing_pmi", "non_manufacturing_pmi", "composite_pmi")
    absent = [k for k in core if result[k] is None]
    if absent:
        raise RuntimeError(
            f"PMI 正文措辞可能已变更，无法解析 {absent}；请核对页面：{url}"
        )
    return result




from _market_common import _v39_contract, _v39_date, _v39_src_date, _v39_http, _v39_num, _v39_frame

import re
from datetime import date, datetime, timedelta

CHINABOND_HISTORY_URL = "https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/historyQuery"
CHINABOND_CURVES = {"all": "ycqx", "treasury": "hzsylqx", "bank_aaa": "syyhsylqx", "mtn_aaa": "zdqpjsylqx"}
_CHINABOND_HEADER = ["曲线名称", "日期", "3月", "6月", "1年", "3年", "5年", "7年", "10年", "30年"]
_CHINABOND_TENORS = ["3m", "6m", "1y", "3y", "5y", "7y", "10y", "30y"]
CHINABOND_CURVE_NAMES = {"treasury": "中债国债收益率曲线", "bank_aaa": "中债商业银行普通债收益率曲线(AAA)",
                         "mtn_aaa": "中债中短期票据收益率曲线(AAA)"}
# 官网上各曲线的第一天（2026-09-20 实测）；all 模式按日期核对当天应有的曲线是否齐全
CHINABOND_FIRST_DAY = {"treasury": "2006-03-01", "mtn_aaa": "2006-12-25", "bank_aaa": "2009-12-24"}


@_v39_contract
def chinabond_yield_curve(start, end=None, curve="all"):
    """中债收益率曲线（中央结算公司官方）— 国债 / 商业银行普通债 AAA / 中短期票据 AAA。

    curve: 'all' / 'treasury'（国债）/ 'bank_aaa' / 'mtn_aaa'。收益率单位为 %。
    期限 3 月到 30 年共 8 档；中短期票据曲线没有 30 年，该列为 None。
    官网单次查询超过 1 年会静默返回 0 行，本函数按 360 天切片。
    各曲线起点：国债 2006-03-01、中短期票据 2006-12-25、商业银行 2009-12-24；
    start 早于起点时从起点开始取。all 模式下 2006-03-01 至 2006-12-24 每天只有国债一条，
    2006-12-25 至 2009-12-23 每天两条（国债 + 中短期票据），2009-12-24 起三条；
    返回的每一天都按这个规则核对曲线是否齐全，缺一条抛 RuntimeError。
    中债不公布债券市场交易日历，页面也没有总条数，所以整天缺失（某个交易日一条都没返回）
    无法判定，只有整段切片 7 天以上 0 行才报错；需要严格逐日核对请自备交易日历比对 date 列。
    """
    if curve not in CHINABOND_CURVES:
        raise ValueError("curve 只能是 " + " / ".join(CHINABOND_CURVES))
    first = datetime.strptime(_v39_date(start), "%Y-%m-%d").date()
    last = datetime.strptime(_v39_date(end), "%Y-%m-%d").date() if end else date.today()
    if first > last:
        raise ValueError("start 不能晚于 end")
    wanted = [k for k in CHINABOND_CURVE_NAMES if curve in ("all", k)]
    begin = datetime.strptime(min(CHINABOND_FIRST_DAY[k] for k in wanted), "%Y-%m-%d").date()
    if last < begin:
        raise ValueError(f"中债 {curve} 曲线从 {begin} 起才有数据")
    first = max(first, begin)
    by_name = {CHINABOND_CURVE_NAMES[k]: k for k in wanted}
    rows, cursor, url, seen = [], first, CHINABOND_HISTORY_URL, {}
    while cursor <= last:
        stop = min(cursor + timedelta(days=359), last)
        response = _v39_http(CHINABOND_HISTORY_URL,
                             params={"startDate": cursor.isoformat(), "endDate": stop.isoformat(),
                                     "gjqx": 0, "qxId": CHINABOND_CURVES[curve], "locale": "cn_ZH"})
        text = re.sub(r"<!--.*?-->", "", response.content.decode("utf-8", "replace"), flags=re.S)
        tables = text.split("<table")
        table_rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tables[-1], re.S) if len(tables) > 2 else []
        cells = [[re.sub(r"<[^>]+>|\s+", "", c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
                 for r in table_rows]
        if not cells or cells[0] != _CHINABOND_HEADER:
            raise RuntimeError("中债收益率页面表头改变，不能按原列序解析")
        chunk = 0
        for rec in cells[1:]:
            if len(rec) != len(_CHINABOND_HEADER):
                raise RuntimeError(f"中债收益率行列数不对: {rec}")
            day = _v39_src_date(rec[1])
            if not cursor.isoformat() <= day <= stop.isoformat():
                raise RuntimeError(f"中债 请求 {cursor}~{stop} 却返回了 {day} 的曲线，结果不可信")
            if rec[0] not in by_name:
                raise RuntimeError(f"中债 返回了未请求的曲线「{rec[0]}」（请求的是 {curve}）")
            seen.setdefault(day, set()).add(by_name[rec[0]])
            row = {"date": day, "curve": rec[0]}
            row.update({k: _v39_num(v) for k, v in zip(_CHINABOND_TENORS, rec[2:])})
            rows.append(row)
            chunk += 1
        if chunk == 0 and (stop - cursor).days >= 6:
            raise RuntimeError(f"中债 {cursor}~{stop} 一周以上却 0 行，接口口径可能变了")
        url = response.url
        cursor = stop + timedelta(days=1)
    if not rows:
        raise ValueError(f"{first}~{last} 没有中债收益率（区间内无交易日）")
    for day, keys in seen.items():
        expected = {k for k in wanted if CHINABOND_FIRST_DAY[k] <= day}
        if keys != expected:
            raise RuntimeError(f"中债 {day} 缺少曲线 {sorted(expected - keys)}，结果不完整")
    frame = _v39_frame(rows, "chinabond", url)
    frame = frame.sort_values(["date", "curve"]).reset_index(drop=True)
    if frame.duplicated(["date", "curve"]).any():
        raise RuntimeError("中债收益率出现重复的 日期+曲线")
    return frame


from _market_common import _v39_req_num

CHINAMONEY_FIXING_URL = "https://www.chinamoney.com.cn/r/cms/www/chinamoney/data/currency/{name}-chrt.csv"


@_v39_contract
def repo_fixing_rates(kind="FR"):
    """银行间回购定盘利率（中国货币网 / 外汇交易中心官方）。

    kind='FR'：全市场回购定盘利率 FR001/FR007/FR014（约近 3 年）；
    kind='FDR'：银银间回购定盘利率 FDR001/FDR007/FDR014（约近 1 年）。单位 %。
    """
    names = {"FR": "frr", "FDR": "fdr"}
    kind = str(kind).upper()
    if kind not in names:
        raise ValueError("kind 只能是 'FR' 或 'FDR'")
    url = CHINAMONEY_FIXING_URL.format(name=names[kind])
    response = _v39_http(url, headers={"Referer": "https://www.chinamoney.com.cn/chinese/bkfrr/"})
    rows = []
    for line in response.content.decode("utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts = line.split(",")
        # 每行是「日期,,,,,,隔夜,7天,14天」：中间 5 列恒为空，不为空说明格式改了
        if len(parts) != 9 or any(p.strip() for p in parts[1:6]):
            raise RuntimeError(f"货币网定盘利率 CSV 格式改变: {line[:60]}")
        # 三个期限都是核心指标：整行为空（'2026-09-18,,,,,,,,'）列数照样是 9，
        # 用 _v39_num 会返回日期有效、利率全 None 的行。实测 FR 748 行 / FDR 249 行零空值。
        rows.append({"date": _v39_src_date(parts[0]),
                     kind + "001": _v39_req_num(parts[6], f"{kind}001"),
                     kind + "007": _v39_req_num(parts[7], f"{kind}007"),
                     kind + "014": _v39_req_num(parts[8], f"{kind}014")})
    if not rows:
        raise RuntimeError(f"货币网 {kind} 定盘利率为空")
    frame = _v39_frame(rows, "chinamoney", url).sort_values("date").reset_index(drop=True)
    if frame.duplicated(["date"]).any():
        raise RuntimeError("定盘利率日期重复")
    return frame


from _eastmoney import _em_datacenter_strict, DATACENTER_URL

@_v39_contract
def lpr_history():
    """贷款市场报价利率 LPR 全历史。单位 %。
    2013-10 至 2019-08 为旧机制的逐日 1 年期 LPR（lpr_5y 为 None，5 年期品种 2019-08-20 才设立）；
    2019-08 改革后每月 20 日报价。东财同一报表里还混着旧贷款基准利率调整行（实测最早 1991-04-21、最晚 2015-10-24，共 38 行），
    LPR 字段为空，已剔除；不为空却认不出的值会报错，不会返回空的 lpr_1y。"""
    rows = _em_datacenter_strict("RPTA_WEB_RATE", sort_columns="TRADE_DATE", sort_types="1",
                                 columns="TRADE_DATE,LPR1Y,LPR5Y")
    out = [{"date": _v39_src_date(str(r["TRADE_DATE"])[:10]), "lpr_1y": _v39_req_num(r["LPR1Y"], "LPR 1 年期"),
            "lpr_5y": _v39_num(r.get("LPR5Y"))}
           for r in rows if r.get("LPR1Y") is not None]
    if not out:
        raise RuntimeError("东财 LPR 报表里没有 LPR 数据")
    return _v39_frame(out, "eastmoney", DATACENTER_URL + "?reportName=RPTA_WEB_RATE")


from _market_common import _v39_json

from datetime import datetime, timedelta, timezone

WSCN_MACRO_URL = "https://api-one-wscn.awtmt.com/apiv1/finance/macrodatas"
_CN_TZ = timezone(timedelta(hours=8))


def _blank_none(value):
    """空串 → None；数值 0 与字符串 '0' 原样保留（`value or None` 会把数值 0 变成缺失）。"""
    return None if value is None or value == "" else value


@_v39_contract
def macro_calendar(start, end=None, country=None, min_importance=1):
    """全球宏观日历（华尔街见闻）— 经济数据公布值/预期/前值 + 重要事件。

    start/end: 'YYYY-MM-DD'（北京时间，含两端）；end 默认 start 后 6 天；区间含两端最多 92 天。
    接口单次只允许一周，本函数按 7 天切片。country 例: '中国' / '美国'；
    importance 1–4，数字越大越重要（实测 4 = 工业增加值、社零这类头条数据），min_importance 按它过滤。
    kind: data=经济数据，event=事件。
    满 7 天且已开始的窗口 0 条抛 RuntimeError（实测过去任一周都有 150 条以上）；
    单日、周末或三周以后的日期可能确实为空（2026-09-19 周六 0 条），整个区间都没有条目时抛 ValueError；
    min_importance 只收 1–4，区间有条目但按 country / min_importance 筛完为空也抛 ValueError（不返回空表）。
    """
    first = datetime.strptime(_v39_date(start), "%Y-%m-%d").date()
    last = datetime.strptime(_v39_date(end), "%Y-%m-%d").date() if end else first + timedelta(days=6)
    if first > last or (last - first).days > 91:
        raise ValueError("区间需满足 start ≤ end 且含两端不超过 92 天")
    if isinstance(min_importance, bool) or str(min_importance) not in ("1", "2", "3", "4"):
        raise ValueError("min_importance 只能是 1–4（数字越大越重要）")
    rows, cursor, url = {}, first, WSCN_MACRO_URL
    today = datetime.now(_CN_TZ).date()
    while cursor <= last:
        stop = min(cursor + timedelta(days=6), last)
        begin = int(datetime(cursor.year, cursor.month, cursor.day, tzinfo=_CN_TZ).timestamp())
        finish = int(datetime(stop.year, stop.month, stop.day, 23, 59, 59, tzinfo=_CN_TZ).timestamp())
        response = _v39_http(WSCN_MACRO_URL, params={"start": begin, "end": finish})
        payload = _v39_json(response)
        if not isinstance(payload, dict) or payload.get("code") != 20000:
            raise RuntimeError(f"华尔街见闻宏观日历返回错误: {str(payload)[:200]}")
        items = payload.get("data").get("items") if isinstance(payload.get("data"), dict) else None
        if items is None:
            items = []
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise RuntimeError("华尔街见闻宏观日历的 items 不是由对象组成的列表，格式可能已变")
        if not items and stop - cursor == timedelta(days=6) and cursor <= today:
            raise RuntimeError(f"华尔街见闻 {cursor}~{stop} 宏观日历 0 条（整周不该为空），接口可能改了")
        for item in items:
            stamp = item.get("public_date")
            if "id" not in item or isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
                raise RuntimeError(f"华尔街见闻宏观日历条目缺 id 或 public_date 格式改变: "
                                   f"id={item.get('id')!r} public_date={stamp!r}")
            try:
                when = datetime.fromtimestamp(stamp, _CN_TZ)
            except (ValueError, OverflowError, OSError) as exc:
                raise RuntimeError(f"华尔街见闻宏观日历时间戳无效: {stamp!r}") from exc
            # 每段只接受段内日期：接口若回了别的时间段（缓存 / 忽略参数），按 id 去重会把缺掉的几段静默吞掉
            if not cursor <= when.date() <= stop:
                raise RuntimeError(f"华尔街见闻 请求 {cursor}~{stop} 却返回了 {when:%Y-%m-%d} 的条目，结果不可信")
            # 各段互不重叠，2026-09-20 实测 31 周 5976 条没有重复 id；重复了按 id 存会静默丢掉一条
            level = item.get("importance")
            if isinstance(level, bool) or not isinstance(level, int) or level not in (1, 2, 3, 4):
                # 不校验的话 importance=True/99 会照常出表，"2" 还会让下面的筛选漏出原生 TypeError
                raise RuntimeError(f"华尔街见闻宏观日历 importance 超出 1–4: {level!r}")
            if item["id"] in rows:
                raise RuntimeError(f"华尔街见闻宏观日历 id {item['id']!r} 出现两次，结果不可信")
            rows[item["id"]] = {
                "time": when.strftime("%Y-%m-%d %H:%M"),
                "country": item.get("country"), "title": item.get("title"),
                "kind": {"FD": "data", "FE": "event"}.get(item.get("calendar_type"), item.get("calendar_type")),
                "importance": level, "actual": _blank_none(item.get("actual")),
                "forecast": _blank_none(item.get("forecast")), "previous": _blank_none(item.get("previous")),
                "revised": _blank_none(item.get("revised")), "unit": item.get("unit") or None,
                "period": item.get("period") or None}
        url = response.url
        cursor = stop + timedelta(days=1)
    if not rows:
        raise ValueError(f"{first}~{last} 没有宏观日历条目（单日、周末或较远的未来日期可能确实没有）")
    frame = _v39_frame(sorted(rows.values(), key=lambda r: r["time"]), "wallstreetcn", url)
    if country:
        frame = frame[frame["country"] == country]
    frame = frame[frame["importance"].fillna(0) >= int(min_importance)].reset_index(drop=True)
    if frame.empty:     # 整个区间是有条目的，筛完没了：country 写错 / 重要度门槛太高
        raise ValueError(f"{first}~{last} 有条目，但 country={country!r} / min_importance={min_importance} "
                         "筛完是空的（country 例: '中国' / '美国'）")
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

    parser = argparse.ArgumentParser(description='官方宏观数据：完整JSON保存')
    commands = parser.add_subparsers(dest='command', required=True)
    social = commands.add_parser('social-financing')
    social.add_argument('--year', type=int, default=None)
    social.add_argument('--output', type=Path)
    pmi = commands.add_parser('pmi')
    pmi.add_argument('--output', type=Path)
    yields = commands.add_parser('yield-curve')
    yields.add_argument('start')
    yields.add_argument('--end')
    yields.add_argument('--curve', default='all', choices=tuple(CHINABOND_CURVES))
    yields.add_argument('--output', type=Path)
    repo = commands.add_parser('repo-fixing')
    repo.add_argument('--kind', default='FR')
    repo.add_argument('--output', type=Path)
    lpr = commands.add_parser('lpr')
    lpr.add_argument('--output', type=Path)
    calendar = commands.add_parser('calendar')
    calendar.add_argument('start')
    calendar.add_argument('--end')
    calendar.add_argument('--country')
    calendar.add_argument('--min-importance', type=int, default=1)
    calendar.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error('输出文件已存在，请指定新路径')
    try:
        if args.command in ('social-financing', 'yield-curve', 'repo-fixing', 'lpr', 'calendar'):
            if args.command == 'social-financing':
                frame = pboc_social_financing(args.year)
            elif args.command == 'repo-fixing':
                frame = repo_fixing_rates(args.kind)
            elif args.command == 'lpr':
                frame = lpr_history()
            elif args.command == 'calendar':
                frame = macro_calendar(args.start, args.end, args.country, args.min_importance)
            else:
                frame = chinabond_yield_curve(args.start, args.end, args.curve)
            payload = _frame_payload(frame)
            preview = _frame_payload(frame.head(3))
        else:
            payload = preview = _json_safe(nbs_pmi())
        path = _save_payload(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2), args.output)
        summary = {'output': str(path), 'preview_only': True, 'preview': preview}
        if args.command in ('social-financing', 'yield-curve', 'repo-fixing', 'lpr', 'calendar'):
            summary['row_count'] = len(frame)
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
