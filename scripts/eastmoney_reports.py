# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""东财个股/行业研报与 PDF；请求共享 _eastmoney 的会话和限流。"""
import _runtime  # noqa: F401  须在第三方库之前导入
from _ticker import norm_ticker
from _eastmoney import em_get

import requests
import re
import time
from datetime import date, timedelta   # 注意用 date/timedelta，不要 import datetime 模块：
                                       # 本 SKILL 多处有 `from datetime import datetime`，会把模块名遮蔽掉
from pathlib import Path
from typing import Optional            # 3.9 兼容：不能写 `str | None`（那是 3.10+ 语法）

REPORT_API = "https://reportapi.eastmoney.com/report/list"
PDF_TPL = "https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

def eastmoney_reports(code: str, max_pages: int = 5) -> list[dict]:
    """拉取指定股票的研报列表。

    code 支持 600519 / SH600519 / 600519.SH 等写法（内部归一化为纯 6 位）。
    ⚠️ reportapi 只认纯 6 位数字：传 "SH600519" 会返回 hits=0，
       看起来像「这只票没研报」，实际是格式没归一化——务必先过 norm_ticker()。
    返回 [] 仅表示东财确无该标的研报覆盖（格式错误已在上游抛 ValueError）。
    """
    code = norm_ticker(code, stock_only=True)   # 格式错/显式指数码直接抛错，不静默返回 []
    all_records = []
    for page in range(1, max_pages + 1):
        params = {
            "industryCode": "*", "pageSize": "100", "industry": "*",
            "rating": "*", "ratingChange": "*",
            "beginTime": "2000-01-01", "endTime": "2030-01-01",
            "pageNo": str(page), "fields": "", "qType": "0",
            "orgCode": "", "code": code, "rcode": "",
            "p": str(page), "pageNum": str(page), "pageNumber": str(page),
        }
        r = em_get(REPORT_API, params=params,
                   headers={"Referer": "https://data.eastmoney.com/"}, timeout=30)  # 已内置限流
        d = r.json()
        rows = d.get("data") or []
        if not rows:
            break
        all_records.extend(rows)
        if page >= (d.get("TotalPage", 1) or 1):
            break
    # 正向识别「查无结果」的真实原因，不把废码静默当成「无研报覆盖」
    if not all_records and code[:2] in ("43", "83", "87"):
        raise ValueError(
            f"{code} 属北交所老号段（43/83/87），东财研报库已不再按老码索引。"
            f"北交所存量标的已基本迁至 920xxx（如 832982→920982）；"
            f"请按股票名称反查现行 920 代码后重试。详见「北交所老号段」警告。"
        )
    return all_records

def download_pdf(record: dict, target_dir: str = "./reports") -> Optional[str]:
    """下载单份研报PDF，返回保存路径或None"""
    info_code = record.get("infoCode", "")
    if not info_code:
        return None
    date = (record.get("publishDate") or "")[:10]
    org = re.sub(r'[\\/:*?"<>|]', "_", record.get("orgSName") or "未知")[:40]
    title = re.sub(r'[\\/:*?"<>|]', "_", record.get("title", ""))[:80]
    fname = f"{date}_{org}_{title}.pdf"
    target = Path(target_dir) / fname
    if target.exists():
        return str(target)
    url = PDF_TPL.format(info_code=info_code)
    r = em_get(url, headers={"Referer": "https://data.eastmoney.com/"}, timeout=60)
    if r.status_code == 200 and len(r.content) >= 1024:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(r.content)
        return str(target)
    return None

from datetime import date, timedelta   # 本块单独拷贝也能跑；勿写成 import datetime（会被 §3+ 的
                                       # `from datetime import datetime` 遮蔽掉模块名）

def eastmoney_industry_reports(industry_code: str = "*", max_pages: int = 5,
                               begin: str = "") -> list[dict]:
    """拉取行业研报列表（qType=1）。
    industry_code="*" = 全行业；传东财行业码（如 "1238"=IT服务Ⅱ）= 单行业。
    行业名 / 行业码在每条 record 的 industryName / industryCode 字段。
    begin 留空 = 近两年（相对今天算，避免硬编码日期越用越旧）。"""
    if not begin:
        begin = (date.today() - timedelta(days=730)).isoformat()
    all_records = []
    for page in range(1, max_pages + 1):
        params = {
            "industryCode": industry_code, "pageSize": "100", "industry": "*",
            "rating": "*", "ratingChange": "*",
            "beginTime": begin, "endTime": "2030-01-01",
            "pageNo": str(page), "fields": "", "qType": "1",
        }
        r = em_get(REPORT_API, params=params,
                   headers={"Referer": "https://data.eastmoney.com/"}, timeout=30)  # 已内置限流
        d = r.json()
        rows = d.get("data") or []
        if not rows:
            break
        all_records.extend(rows)
        if page >= (d.get("TotalPage", 1) or 1):
            break
    return all_records


def _json_safe(value):
    """显式保存缺失/非有限值；不使用 default=str 静默改变类型。"""
    import math

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return {"$float": "NaN" if math.isnan(value) else
                ("Infinity" if value > 0 else "-Infinity")}
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    # numpy 标量转为等值 Python 标量；研报 JSON 字段没有任意对象列。
    if hasattr(value, "item"):
        return _json_safe(value.item())
    raise TypeError(f"无法无歧义地序列化 {type(value).__name__}")


def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="eastmoney-reports-", suffix=".json", delete=False) as stream:
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


def main(argv=None):
    import argparse
    from contextlib import redirect_stdout
    import json
    import math
    import sys
    import _eastmoney

    parser = argparse.ArgumentParser(description="东财个股/行业研报全量保存及 PDF 下载；共用限流。")
    commands = parser.add_subparsers(dest="command", required=True)
    stock = commands.add_parser("stock", help="个股研报列表")
    stock.add_argument("code")
    industry = commands.add_parser("industry", help="行业研报列表")
    industry.add_argument("industry_code", nargs="?", default="*")
    industry.add_argument("--begin", default="", help="原样传 begin；省略为今天减 730 天")
    for subparser in (stock, industry):
        subparser.add_argument("--max-pages", type=int, default=5)
        subparser.add_argument("--output", type=Path, help="完整列表的新 JSON 文件；不覆盖")
    pdf = commands.add_parser("pdf", help="从单条 record JSON 下载 PDF")
    pdf.add_argument("record", type=Path, help="单个 record 对象 JSON，不是研报列表")
    pdf.add_argument("--target-dir", default="./reports")
    for subparser in (stock, industry, pdf):
        subparser.add_argument("--min-interval", type=float, help="本进程请求间隔，默认 1 秒；仅允许调大")
    args = parser.parse_args(argv)
    if getattr(args, "output", None) is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    if args.min_interval is not None:
        if not math.isfinite(args.min_interval) or args.min_interval < 1:
            parser.error("--min-interval 必须是至少 1 秒的有限数值")
    previous_interval = _eastmoney.EM_MIN_INTERVAL
    try:
        if args.min_interval is not None:
            _eastmoney.EM_MIN_INTERVAL = args.min_interval
        with redirect_stdout(sys.stderr):
            if args.command == "pdf":
                with args.record.open(encoding="utf-8") as stream:
                    record = json.load(stream)
                if not isinstance(record, dict):
                    raise ValueError("record 必须是单个 JSON 对象")
                path = download_pdf(record, args.target_dir)
                if path is None:
                    raise RuntimeError("未获得 PDF 路径：缺 infoCode 或响应未满足旧版 HTTP 200/至少 1024 字节条件")
                summary = {"pdf": str(Path(path).resolve()), "existing_file_may_be_reused": True}
            else:
                records = (eastmoney_reports(args.code, args.max_pages) if args.command == "stock" else
                           eastmoney_industry_reports(args.industry_code, args.max_pages, args.begin))
                payload = _json_safe(records)
                encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
                path = _save_payload(encoded, args.output)
                summary = {"output": str(path), "row_count": len(records), "preview_only": True,
                           "preview": payload[:3]}
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        _eastmoney.EM_MIN_INTERVAL = previous_interval


if __name__ == "__main__":
    raise SystemExit(main())
