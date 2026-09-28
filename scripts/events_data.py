# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""东财事件与可转债：严格分页及返回校验。"""
import _runtime  # noqa: F401  须在第三方库之前导入
import pandas as pd
from _ticker import get_prefix, norm_ticker
from _eastmoney import DATACENTER_URL, _em_datacenter_strict
from _market_common import _v39_contract, _v39_date, _v39_src_date, _v39_frame, _v39_num, _em_day

import json


def _v39_limit(limit, upper=5000):
    limit = int(limit)
    if not 1 <= limit <= upper:
        raise ValueError(f"limit 范围 1–{upper}")
    return limit


def _em_event_filter(code=None, date_field=None, start=None, end=None, extra=""):
    """拼东财 datacenter filter：个股代码 + 公告日期区间 + 额外条件。start 晚于 end 在请求前抛 ValueError。"""
    if start and end and _v39_date(start) > _v39_date(end):
        raise ValueError("start 不能晚于 end")
    parts = [extra] if extra else []
    if code is not None:
        parts.append(f'(SECURITY_CODE="{norm_ticker(code, stock_only=True)}")')
    if start:
        parts.append(f"({date_field}>='{_v39_date(start)}')")
    if end:
        parts.append(f"({date_field}<='{_v39_date(end)}')")
    return "".join(parts)


def _em_event_rows(report, filter_str, sort_columns, sort_types, limit, narrowed, extra=None,
                   equal=None, dates=None):
    """narrowed=False（全市场、不带任何条件）时 0 行说明接口坏了，直接抛错；
    带了个股 / 日期条件时 0 行是「确实没有」，返回空表。

    排序字段必须能唯一确定一行：东财按页切片，排序有并列时翻页会重复一行、同时漏掉另一行
    （实测质押表只按质押比例排序时 2212 行里重复 1 行、漏 1 行）。出现完全相同的行就直接抛错。

    服务端筛选只是请求：equal={字段: 值}、dates={日期字段: (起, 止)} 逐行核对返回的行，
    接口忽略筛选或回了别的缓存页时抛 RuntimeError，不把别的标的 / 报告期 / 日期当结果返回。"""
    rows = _em_datacenter_strict(report, filter_str, sort_columns, sort_types,
                                 page_size=min(limit, 500), max_rows=limit, extra=extra)
    if not rows and not narrowed:
        raise RuntimeError(f"东财 {report} 全市场返回 0 行，接口可能改了")
    if len({json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows}) != len(rows):
        raise RuntimeError(f"东财 {report} 翻页返回了重复行（排序不唯一），结果不完整")
    for r in rows:
        for field, value in (equal or {}).items():
            if r.get(field) != value:
                raise RuntimeError(f"东财 {report} 请求 {field}={value}，却返回了 {r.get(field)!r}，结果不可信")
        for field, (lo, hi) in (dates or {}).items():
            day = _v39_src_date(str(r.get(field) or "")[:10])
            if (lo and day < lo) or (hi and day > hi):
                raise RuntimeError(f"东财 {report} 请求 {field} 在 {lo or ''}~{hi or ''}，却返回了 {day}，结果不可信")
    return rows


_FORECAST_COLUMNS = ["code", "name", "notice_date", "report_date", "indicator", "forecast_type",
                     "amount_lower", "amount_upper", "change_pct_lower", "change_pct_upper",
                     "prior_year_amount", "content", "reason"]


@_v39_contract
def earnings_forecast(code=None, report_date=None, limit=500):
    """业绩预告（东财数据中心，沪深京全市场）。

    code 不给 = 全市场最新 limit 条（按公告日倒序）；report_date 为报告期，如 '2026-09-30'。
    一次预告会拆成多行：indicator 是预告指标（归母净利润 / 扣非净利润 / 营业收入…）。
    金额单位 元，change_pct 为同比变动 %。
    """
    limit = _v39_limit(limit)
    period = _v39_date(report_date) if report_date else None
    extra = f"(REPORT_DATE='{period}')" if period else ""
    filter_str = _em_event_filter(code, extra=extra)
    rows = _em_event_rows("RPT_PUBLIC_OP_NEWPREDICT", filter_str,
                          "NOTICE_DATE,SECURITY_CODE,REPORT_DATE,PREDICT_FINANCE_CODE", "-1,1,-1,1",
                          limit, narrowed=bool(code or report_date),
                          equal={} if code is None else {"SECURITY_CODE": norm_ticker(code, stock_only=True)},
                          dates={"REPORT_DATE": (period, period)} if period else None)
    out = [{"code": r["SECURITY_CODE"], "name": r.get("SECURITY_NAME_ABBR"),
            "notice_date": _em_day(r.get("NOTICE_DATE")), "report_date": _em_day(r.get("REPORT_DATE")),
            "indicator": r.get("PREDICT_FINANCE"), "forecast_type": r.get("PREDICT_TYPE"),
            "amount_lower": _v39_num(r.get("PREDICT_AMT_LOWER")),
            "amount_upper": _v39_num(r.get("PREDICT_AMT_UPPER")),
            "change_pct_lower": _v39_num(r.get("ADD_AMP_LOWER")),
            "change_pct_upper": _v39_num(r.get("ADD_AMP_UPPER")),
            "prior_year_amount": _v39_num(r.get("PREYEAR_SAME_PERIOD")),
            "content": r.get("PREDICT_CONTENT"), "reason": r.get("CHANGE_REASON_EXPLAIN")}
           for r in rows]
    return _v39_frame(out, "eastmoney", DATACENTER_URL + "?reportName=RPT_PUBLIC_OP_NEWPREDICT",
                      _FORECAST_COLUMNS)


_SURVEY_COLUMNS = ["code", "name", "notice_date", "survey_date", "survey_end", "org_count",
                   "survey_way", "place", "receptionist"]


@_v39_contract
def institution_survey(code=None, start=None, end=None, detail=False, limit=500):
    """机构调研（东财数据中心，汇总自上市公司投资者关系活动记录表）。

    detail=False：一次调研一行，org_count 为参与机构家数；
    detail=True：一家机构一行，多出 org_name / org_type / investigators（很多记录表不写机构类型和人名，为 None）。
    start / end 按公告日（notice_date）筛选；survey_date 是实际接待日，通常早于公告日几天。
    """
    limit = _v39_limit(limit)
    extra = '(IS_SOURCE="1")' + ("" if detail else '(NUMBERNEW="1")')
    filter_str = _em_event_filter(code, "NOTICE_DATE", start, end, extra)
    sort = (("NOTICE_DATE,SECURITY_CODE,RECEIVE_START_DATE,NUMBERNEW", "-1,1,-1,1") if detail
            else ("NOTICE_DATE,SECURITY_CODE,RECEIVE_START_DATE", "-1,1,-1"))
    equal = {"IS_SOURCE": "1"} if detail else {"IS_SOURCE": "1", "NUMBERNEW": "1"}
    if code is not None:
        equal["SECURITY_CODE"] = norm_ticker(code, stock_only=True)
    rows = _em_event_rows("RPT_ORG_SURVEYNEW", filter_str, sort[0], sort[1], limit,
                          narrowed=bool(code or start or end), equal=equal,
                          dates={"NOTICE_DATE": (start and _v39_date(start), end and _v39_date(end))}
                          if start or end else None)
    out = []
    for r in rows:
        row = {"code": r["SECURITY_CODE"], "name": r.get("SECURITY_NAME_ABBR"),
               "notice_date": _em_day(r.get("NOTICE_DATE")), "survey_date": _em_day(r.get("RECEIVE_START_DATE")),
               "survey_end": _em_day(r.get("RECEIVE_END_DATE")), "org_count": _v39_num(r.get("SUM")),
               "survey_way": r.get("RECEIVE_WAY_EXPLAIN"), "place": r.get("RECEIVE_PLACE"),
               "receptionist": r.get("RECEPTIONIST")}
        if detail:
            row.update({"org_name": r.get("RECEIVE_OBJECT"), "org_type": r.get("ORG_TYPE"),
                        "investigators": r.get("INVESTIGATORS")})
        out.append(row)
    columns = _SURVEY_COLUMNS + (["org_name", "org_type", "investigators"] if detail else [])
    return _v39_frame(out, "eastmoney", DATACENTER_URL + "?reportName=RPT_ORG_SURVEYNEW", columns)


_HOLDER_COLUMNS = ["code", "name", "holder", "direction", "change_shares_10k", "change_pct_total",
                   "change_pct_float", "after_shares_10k", "after_pct_total", "after_float_shares_10k",
                   "after_pct_float", "avg_price", "channel", "start_date", "end_date", "notice_date"]


@_v39_contract
def holder_trades(code=None, direction=None, start=None, end=None, limit=500):
    """股东增减持（东财数据中心，重要股东二级市场 / 大宗交易等变动公告）。

    direction: None / '增持' / '减持'。start / end 按公告日筛选。
    股数单位 万股；change_shares_10k 带符号（减持为负）；*_pct_total 占总股本 %，*_pct_float 占流通股 %。
    avg_price 为公告披露的成交均价，很多公告不披露，为 None。channel 为变动方式（二级市场 / 大宗交易 / 协议转让…）。
    """
    limit = _v39_limit(limit)
    if direction not in (None, "增持", "减持"):
        raise ValueError("direction 只能是 None / '增持' / '减持'")
    extra = f'(DIRECTION="{direction}")' if direction else ""
    filter_str = _em_event_filter(code, "NOTICE_DATE", start, end, extra)
    equal = {"DIRECTION": direction} if direction else {}
    if code is not None:
        equal["SECURITY_CODE"] = norm_ticker(code, stock_only=True)
    rows = _em_event_rows("RPT_SHARE_HOLDER_INCREASE", filter_str,
                          "NOTICE_DATE,SECURITY_CODE,HOLDER_NAME,START_DATE,END_DATE", "-1,1,1,1,1",
                          limit, narrowed=bool(code or start or end), equal=equal,
                          dates={"NOTICE_DATE": (start and _v39_date(start), end and _v39_date(end))}
                          if start or end else None)
    out = []
    for r in rows:
        signed = _v39_num(r.get("CHANGE_NUM_SYMBOL"))
        if signed is not None and r.get("DIRECTION") in ("增持", "减持") and (signed < 0) != (r["DIRECTION"] == "减持"):
            raise RuntimeError(f"东财增减持方向与变动股数符号不一致: {r['SECURITY_CODE']} {r['HOLDER_NAME']}")
        out.append({"code": r["SECURITY_CODE"], "name": r.get("SECURITY_NAME_ABBR"),
                    "holder": r.get("HOLDER_NAME"), "direction": r.get("DIRECTION"),
                    "change_shares_10k": signed,
                    # 东财字段名 AFTER_CHANGE_RATE 实为「本次变动占总股本比例」（与变动股数 / 总股本对得上）
                    "change_pct_total": _v39_num(r.get("AFTER_CHANGE_RATE")),
                    "change_pct_float": _v39_num(r.get("CHANGE_FREE_RATIO")),
                    "after_shares_10k": _v39_num(r.get("AFTER_HOLDER_NUM")),
                    "after_pct_total": _v39_num(r.get("HOLD_RATIO")),
                    "after_float_shares_10k": _v39_num(r.get("FREE_SHARES")),
                    "after_pct_float": _v39_num(r.get("FREE_SHARES_RATIO")),
                    "avg_price": _v39_num(r.get("TRADE_AVERAGE_PRICE")), "channel": r.get("MARKET"),
                    "start_date": _em_day(r.get("START_DATE")), "end_date": _em_day(r.get("END_DATE")),
                    "notice_date": _em_day(r.get("NOTICE_DATE"))})
    return _v39_frame(out, "eastmoney", DATACENTER_URL + "?reportName=RPT_SHARE_HOLDER_INCREASE",
                      _HOLDER_COLUMNS)


_BUYBACK_PROGRESS = {"001": "董事会预案", "002": "股东大会通过", "003": "股东大会否决",
                     "004": "实施中", "005": "停止实施", "006": "完成实施"}
_BUYBACK_COLUMNS = ["code", "name", "progress", "progress_code", "plan_start", "plan_end", "price_cap",
                    "shares_lower", "shares_upper", "amount_lower", "amount_upper",
                    "pct_total_lower", "pct_total_upper", "done_shares", "done_amount",
                    "done_price_low", "done_price_high", "latest_notice", "objective"]


@_v39_contract
def share_buyback(code=None, progress=None, limit=500):
    """股票回购（东财数据中心）— 回购方案与实施进度，一个方案一行、按最新公告日倒序。

    progress: None 或 '董事会预案' / '股东大会通过' / '股东大会否决' / '实施中' / '停止实施' / '完成实施'。
    股数单位 股，金额单位 元，pct_total_* 为占公告前一日总股本 %。done_* 为已回购部分（未开始实施为 None）。
    东财另有 007 / 008 两个进度码（2026-09-20 实测 5516 条里共 13 条），它自己的页面也不显示名称，
    这里 progress 为 None、progress_code 保留原码。
    """
    limit = _v39_limit(limit)
    codes = {v: k for k, v in _BUYBACK_PROGRESS.items()}
    if progress is not None and progress not in codes:
        raise ValueError("progress 只能是 " + " / ".join(codes))
    equal = {}
    if code is not None:
        equal["DIM_SCODE"] = norm_ticker(code, stock_only=True)     # 这张表的代码字段叫 DIM_SCODE
    if progress:
        equal["REPURPROGRESS"] = codes[progress]
    filter_str = "".join(f'({field}="{value}")' for field, value in equal.items())
    rows = _em_event_rows("RPTA_WEB_GETHGLIST_NEW", filter_str, "UPD,DIM_SCODE,REPURCODE", "-1,1,1",
                          limit, narrowed=bool(equal), equal=equal)
    out = []
    for r in rows:
        out.append({"code": r["DIM_SCODE"], "name": r.get("SECURITYSHORTNAME"),
                    "progress": _BUYBACK_PROGRESS.get(r.get("REPURPROGRESS")),
                    "progress_code": r.get("REPURPROGRESS"),
                    "plan_start": _em_day(r.get("REPURSTARTDATE")), "plan_end": _em_day(r.get("REPURENDDATE")),
                    "price_cap": _v39_num(r.get("REPURPRICECAP")),
                    "shares_lower": _v39_num(r.get("REPURNUMLOWER")), "shares_upper": _v39_num(r.get("REPURNUMCAP")),
                    "amount_lower": _v39_num(r.get("REPURAMOUNTLOWER")),
                    "amount_upper": _v39_num(r.get("REPURAMOUNTLIMIT")),
                    "pct_total_lower": _v39_num(r.get("ZSZXX")), "pct_total_upper": _v39_num(r.get("ZSZSX")),
                    "done_shares": _v39_num(r.get("REPURNUM")), "done_amount": _v39_num(r.get("REPURAMOUNT")),
                    "done_price_low": _v39_num(r.get("REPURPRICELOWER1")),
                    "done_price_high": _v39_num(r.get("REPURPRICECAP1")),
                    "latest_notice": _em_day(r.get("UPDATEDATE")), "objective": r.get("REPUROBJECTIVE")})
    return _v39_frame(out, "eastmoney", DATACENTER_URL + "?reportName=RPTA_WEB_GETHGLIST_NEW", _BUYBACK_COLUMNS)


_PLEDGE_COLUMNS = ["date", "code", "name", "industry", "pledge_ratio_pct", "pledged_shares_10k",
                   "pledged_mktcap_10k", "pledge_count", "unrestricted_pledged_10k", "restricted_pledged_10k"]


@_v39_contract
def equity_pledge(code=None, date=None, limit=5000):
    """股权质押比例（中国结算每周统计，经东财数据中心）。

    code 给了：该股历次统计（按日期倒序）；date 给了：该统计日全市场；都不给：最近一个统计日全市场；
    两个都给抛 ValueError（不会静默丢掉其中一个）。
    中国结算按周发布（通常为周五），date 不是统计日会得到 ValueError。
    pledge_ratio_pct 为质押股数占总股本 %；股数单位 万股，市值单位 万元。
    只覆盖沪深（2026-09-20 实测全市场 2212 条没有北交所），北交所代码直接抛 ValueError，不返回空表。
    """
    limit = _v39_limit(limit)
    if code is not None and date is not None:
        raise ValueError("code 与 date 只能给一个：code 取该股历次统计，date 取该统计日全市场")
    if code is not None and get_prefix(code) == "bj":
        raise ValueError(f"{code} 是北交所证券；中国结算质押统计只覆盖沪深，没有北交所数据")
    report = "RPT_CSDC_LIST"
    url = DATACENTER_URL + "?reportName=" + report
    if code is not None:
        rows = _em_event_rows(report, _em_event_filter(code), "TRADE_DATE", "-1", limit, narrowed=True,
                              equal={"SECURITY_CODE": norm_ticker(code, stock_only=True)})
    else:
        if date is None:
            latest = _em_event_rows(report, "", "TRADE_DATE", "-1", 1, narrowed=False)
            date = latest[0]["TRADE_DATE"]
        day = _v39_date(str(date)[:10])
        rows = _em_event_rows(report, f"(TRADE_DATE='{day}')", "PLEDGE_RATIO,SECURITY_CODE", "-1,1",
                              limit, narrowed=True, dates={"TRADE_DATE": (day, day)})
        if not rows:
            raise ValueError(f"{day} 不是中国结算质押统计日（按周发布，通常为周五）")
    out = []
    for r in rows:
        total = _v39_num(r.get("REPURCHASE_BALANCE"))
        free, locked = _v39_num(r.get("REPURCHASE_UNLIMITED_BALANCE")), _v39_num(r.get("REPURCHASE_LIMITED_BALANCE"))
        if None not in (total, free, locked) and abs(free + locked - total) > max(1.0, total * 0.001):
            raise RuntimeError(f"东财质押数据 无限售 + 限售 ≠ 合计: {r['SECURITY_CODE']} {r['TRADE_DATE']}")
        out.append({"date": _em_day(r.get("TRADE_DATE")), "code": r["SECURITY_CODE"],
                    "name": r.get("SECURITY_NAME_ABBR"), "industry": r.get("INDUSTRY"),
                    "pledge_ratio_pct": _v39_num(r.get("PLEDGE_RATIO")), "pledged_shares_10k": total,
                    "pledged_mktcap_10k": _v39_num(r.get("PLEDGE_MARKET_CAP")),
                    "pledge_count": _v39_num(r.get("PLEDGE_DEAL_NUM")),
                    "unrestricted_pledged_10k": free, "restricted_pledged_10k": locked})
    frame = _v39_frame(out, "eastmoney", url, _PLEDGE_COLUMNS)
    if frame.duplicated(["date", "code"]).any():
        raise RuntimeError("东财质押数据 日期+代码 重复")
    return frame


_IPO_COLUMNS = ["code", "name", "apply_code", "exchange", "board", "apply_date", "ballot_date", "pay_date",
                "listing_date", "issue_price", "issue_pe", "industry_pe", "issue_shares_10k",
                "online_shares", "apply_upper_shares", "top_apply_mktcap_10k", "win_rate_pct",
                "first_close", "first_close_chg_pct"]


@_v39_contract
def ipo_calendar(limit=100):
    """新股申购日历（东财数据中心，沪深京）— 按申购日倒序，包含尚未申购的排期。

    issue_price 在定价前为 None。issue_shares_10k 单位万股；online_shares / apply_upper_shares 单位股；
    top_apply_mktcap_10k 为顶格申购需配市值（万元）；win_rate_pct 为网上中签率 %；
    first_close_chg_pct 为上市首日收盘涨幅 %（未上市为 None）。
    """
    limit = _v39_limit(limit)
    rows = _em_event_rows("RPTA_APP_IPOAPPLY", "", "APPLY_DATE,SECURITY_CODE", "-1,-1", limit, narrowed=False)
    out = [{"code": r["SECURITY_CODE"], "name": r.get("SECURITY_NAME"), "apply_code": r.get("APPLY_CODE"),
            "exchange": r.get("TRADE_MARKET"),
            # MARKET 是「深交所主板 / 深交所创业板」这类准确板块；MARKET_TYPE_NEW 会把未上市的标成「深交所其他」，
            # 但北交所新股只有后者
            "board": r.get("MARKET") or r.get("MARKET_TYPE_NEW"),
            "apply_date": _em_day(r.get("APPLY_DATE")), "ballot_date": _em_day(r.get("BALLOT_NUM_DATE")),
            "pay_date": _em_day(r.get("BALLOT_PAY_DATE")), "listing_date": _em_day(r.get("LISTING_DATE")),
            "issue_price": _v39_num(r.get("ISSUE_PRICE")) or None,     # 定价前东财填 null 或 0
            "issue_pe": _v39_num(r.get("AFTER_ISSUE_PE")), "industry_pe": _v39_num(r.get("INDUSTRY_PE")),
            "issue_shares_10k": _v39_num(r.get("ISSUE_NUM")), "online_shares": _v39_num(r.get("ONLINE_ISSUE_NUM")),
            "apply_upper_shares": _v39_num(r.get("ONLINE_APPLY_UPPER")),
            "top_apply_mktcap_10k": _v39_num(r.get("TOP_APPLY_MARKETCAP")),
            "win_rate_pct": _v39_num(r.get("ONLINE_ISSUE_LWR")),
            "first_close": _v39_num(r.get("CLOSE_PRICE")),
            "first_close_chg_pct": _v39_num(r.get("LD_CLOSE_CHANGE"))}
           for r in rows]
    frame = _v39_frame(out, "eastmoney", DATACENTER_URL + "?reportName=RPTA_APP_IPOAPPLY", _IPO_COLUMNS)
    if frame.duplicated(["code"]).any():
        raise RuntimeError("东财新股日历代码重复")
    return frame


from datetime import datetime, timedelta, timezone

_CB_QUOTES = ("f2~01~CONVERT_STOCK_CODE~CONVERT_STOCK_PRICE,f235~10~SECURITY_CODE~TRANSFER_PRICE,"
              "f236~10~SECURITY_CODE~TRANSFER_VALUE,f2~10~SECURITY_CODE~CURRENT_BOND_PRICE,"
              "f237~10~SECURITY_CODE~TRANSFER_PREMIUM_RATIO")
_CB_COLUMNS = ["code", "name", "status", "stock_code", "stock_name", "rating", "issue_size_100m",
               "apply_date", "apply_code", "listing_date", "delist_date", "expire_date", "convert_start",
               "initial_convert_price", "convert_price", "bond_price", "stock_price", "convert_value",
               "premium_pct"]


@_v39_contract
def convertible_bonds(include_delisted=False):
    """可转债全表（东财数据中心）— 基本条款 + 最新转股价 / 债价 / 正股价 / 转股价值 / 溢价率。

    status: 'upcoming'（已发行未上市）/ 'listed'（交易中）/ 'delisted'（已摘牌，include_delisted=True 才返回）/
    'unknown'（交易市场不认识，或既没有上市日也没有申购日，不猜）。
    退市板块的转债（代码 404xxx、TRADE_MARKET=STAS00，如 404005 普利退债）东财不填上市日和摘牌日，按 delisted 处理。
    行情类字段由东财服务端按最新报价填入：盘中为实时价，停牌或未上市为 None。
    转股价值 = 100 / 转股价 × 正股价；premium_pct = 债价 / 转股价值 − 1（%）。issue_size_100m 单位亿元。
    """
    rows = _em_datacenter_strict("RPT_BOND_CB_LIST", "", "PUBLIC_START_DATE,SECURITY_CODE", "-1,1",
                                 page_size=500, max_rows=20000,
                                 extra={"quoteColumns": _CB_QUOTES, "quoteType": "0"})
    if not rows:
        raise RuntimeError("东财可转债列表为空，接口可能改了")
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()   # 按北京时间，不看本机时区
    out = []
    for r in rows:
        listing, delist = _em_day(r.get("LISTING_DATE")), _em_day(r.get("DELIST_DATE"))
        market = r.get("TRADE_MARKET")
        # 东财在发布赎回/到期公告后就会填上未来的摘牌日，摘牌日之前仍在交易；
        # 上市日同理可能提前填上，上市日之前算 upcoming
        if (delist and delist <= today) or market == "STAS00":     # STAS00 = 退市板块，已从沪深摘牌
            status = "delisted"
        elif market not in ("CNSESH", "CNSESZ"):
            status = "unknown"
        elif listing and listing <= today:
            status = "listed"
        elif listing or r.get("PUBLIC_START_DATE"):
            status = "upcoming"
        else:
            status = "unknown"
        if status == "delisted" and not include_delisted:
            continue
        out.append({"code": r["SECURITY_CODE"], "name": r.get("SECURITY_NAME_ABBR"), "status": status,
                    "stock_code": r.get("CONVERT_STOCK_CODE"), "stock_name": r.get("SECURITY_SHORT_NAME"),
                    "rating": r.get("RATING"), "issue_size_100m": _v39_num(r.get("ACTUAL_ISSUE_SCALE")),
                    "apply_date": _em_day(r.get("PUBLIC_START_DATE")), "apply_code": r.get("CORRECODE"),
                    "listing_date": listing, "delist_date": delist, "expire_date": _em_day(r.get("EXPIRE_DATE")),
                    "convert_start": _em_day(r.get("TRANSFER_START_DATE")),
                    "initial_convert_price": _v39_num(r.get("INITIAL_TRANSFER_PRICE")),
                    "convert_price": _v39_num(r.get("TRANSFER_PRICE")),
                    "bond_price": _v39_num(r.get("CURRENT_BOND_PRICE")),
                    "stock_price": _v39_num(r.get("CONVERT_STOCK_PRICE")),
                    "convert_value": _v39_num(r.get("TRANSFER_VALUE")),
                    "premium_pct": _v39_num(r.get("TRANSFER_PREMIUM_RATIO"))})
    frame = _v39_frame(out, "eastmoney", DATACENTER_URL + "?reportName=RPT_BOND_CB_LIST", _CB_COLUMNS)
    if frame.duplicated(["code"]).any():
        raise RuntimeError("东财可转债列表代码重复")
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

    parser = argparse.ArgumentParser(description='东财事件数据：完整JSON保存')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('forecast', 'survey', 'holder-trades', 'buyback', 'pledge', 'ipo'):
        command = commands.add_parser(name)
        command.add_argument('--limit', type=int, default=5000 if name == 'pledge' else 100 if name == 'ipo' else 500)
        command.add_argument('--output', type=Path)
        if name != 'ipo':
            command.add_argument('--code')
        if name == 'forecast':
            command.add_argument('--report-date')
        if name in ('survey', 'holder-trades'):
            command.add_argument('--start')
            command.add_argument('--end')
        if name == 'survey':
            command.add_argument('--detail', action='store_true')
        if name == 'holder-trades':
            command.add_argument('--direction', choices=('增持', '减持'))
        if name == 'buyback':
            command.add_argument('--progress', choices=tuple(_BUYBACK_PROGRESS.values()))
        if name == 'pledge':
            command.add_argument('--date')
    bonds = commands.add_parser('bonds')
    bonds.add_argument('--include-delisted', action='store_true')
    bonds.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error('输出路径已存在，请指定新路径')
    try:
        if args.command == 'bonds':
            frame = convertible_bonds(args.include_delisted)
        elif args.command == 'forecast':
            frame = earnings_forecast(args.code, args.report_date, args.limit)
        elif args.command == 'survey':
            frame = institution_survey(args.code, args.start, args.end, args.detail, args.limit)
        elif args.command == 'holder-trades':
            frame = holder_trades(args.code, args.direction, args.start, args.end, args.limit)
        elif args.command == 'buyback':
            frame = share_buyback(args.code, args.progress, args.limit)
        elif args.command == 'pledge':
            frame = equity_pledge(args.code, args.date, args.limit)
        else:
            frame = ipo_calendar(args.limit)
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
