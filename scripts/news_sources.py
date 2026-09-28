# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""华尔街见闻与央视新闻联播；完整 DataFrame 输出。"""
import _runtime  # noqa: F401  须在第三方库之前导入
import pandas as pd
from _market_common import _v39_http, _v39_json, _v39_date, _v39_rows, _v39_labels, _v39_contract, _v39_frame
import re
from datetime import datetime, timedelta, timezone

WSCN_LIVES_URL = "https://api-one-wscn.awtmt.com/apiv1/content/lives"
_CN_TZ = timezone(timedelta(hours=8))


@_v39_contract
def wallstreetcn_lives(channel="global-channel", limit=50, cursor=None):
    """华尔街见闻 7×24 快讯（新闻层第三来源，与 §5.2 财联社 / §5.3 东财互备）。

    channel: global-channel（要闻，默认）/ a-stock-channel（A 股）等频道名。
    limit ≤ 100。翻页：把返回表的 attrs['next_cursor'] 传给下一次的 cursor。
    importance 取见闻的 score 字段：实测只有 1 / 2，100 条里约 6 条为 2（头条级快讯）。时间为北京时间。
    """
    if not re.fullmatch(r"[a-z0-9-]+-channel", str(channel)):
        raise ValueError("channel 形如 'global-channel' / 'a-stock-channel'")
    if not 1 <= int(limit) <= 100:
        raise ValueError("limit 范围 1–100")
    params = {"channel": channel, "limit": int(limit)}
    if cursor:
        params["cursor"] = cursor
    response = _v39_http(WSCN_LIVES_URL, params=params)
    payload = _v39_json(response)
    if not isinstance(payload, dict) or payload.get("code") != 20000 or not isinstance(payload.get("data"), dict):
        raise RuntimeError(f"华尔街见闻返回错误: {str(payload)[:200]}")
    items = _v39_rows(payload["data"].get("items"), "华尔街见闻快讯的 items")
    rows = []
    try:
        for item in items:
            stamp = item["display_time"]
            if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
                raise TypeError(f"display_time={stamp!r}")
            rows.append({"id": item["id"],
                         "time": datetime.fromtimestamp(stamp, _CN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                         "title": item.get("title") or "",
                         "content": (item.get("content_text") or "").strip(),
                         "importance": item.get("score"),
                         "channels": ",".join(_v39_labels(item.get("channels"), "快讯 channels")),
                         "url": item.get("uri") or ""})
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError, OSError) as exc:
        raise RuntimeError(f"华尔街见闻快讯条目格式改变: {type(exc).__name__}: {exc}") from exc
    if not rows:
        raise RuntimeError(f"华尔街见闻 {channel} 返回 0 条（频道名可能不存在）")
    frame = _v39_frame(rows, "wallstreetcn", response.url)
    frame.attrs["next_cursor"] = payload["data"].get("next_cursor")
    return frame

import html as _html
import re
import time

CCTV_DAY_URL = "https://tv.cctv.com/lm/xwlb/day/{ymd}.shtml"


def _cctv_body(url):
    text = _v39_http(url).content.decode("utf-8", "replace")
    if len(text) < 1000 and "error.html" in text:
        return None                         # 单条视频已被央视下架（页面只剩跳错误页的脚本）
    match = (re.search(r'<div class="content_area"[^>]*>(.*?)</div>', text, re.S)
             or re.search(r'<div class="cnt_bd"[^>]*>(.*?)</div>', text, re.S))
    if not match:
        raise RuntimeError(f"新闻联播正文页结构改变: {url}")
    body = re.sub(r"</p>|<br\s*/?>", "\n", match.group(1))
    body = _html.unescape(re.sub(r"<[^>]+>", "", body))
    body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
    return re.sub(r"^央视网消息\s*[（(]新闻联播[)）]\s*[：:]", "", body)


@_v39_contract
def cctv_news(date, with_content=True):
    """央视《新闻联播》当日条目（央视网官方页面）— 标题 + 文字稿。

    with_content=True 会逐条打开详情页取正文（约 15 次请求）；False 只要标题和链接。
    个别老视频已被下架，其 content 为 None（标题仍在）。
    内容以时政为主：可用于政策信号研究，**做短视频文案时不要引用**。
    """
    ymd = _v39_date(date).replace("-", "")
    url = CCTV_DAY_URL.format(ymd=ymd)
    response = _v39_http(url, allow_status=(404,))
    if response.status_code == 404:
        raise ValueError(f"{date} 没有新闻联播页面（日期过早或尚未发布，当晚约 20:00 后更新）")
    text = response.content.decode("utf-8", "replace")
    rows = []
    # 央视网改版过三次：2016 标题是 <a> 的文本，2019–2020 在 <div class="title">，
    # 2021 起在 <a title="">。逐个 <li> 按这三种位置依次找。
    for chunk in text.split("<li")[1:]:
        link = re.search(r'href="([^"]*/VIDE[^"]+)"', chunk)
        if not link:
            continue
        href = link.group(1)
        title = (re.search(r'title="([^"]+)"', chunk) or re.search(r'class="title">(.*?)</div>', chunk, re.S)
                 or re.search(r"<a[^>]*>(.*?)</a>", chunk, re.S))
        title = _html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else ""
        if not title or re.match(r"《新闻联播》\s*\d{8}|新闻联播完整版", title):
            continue                        # 第一条是整期节目视频，不是单条新闻
        title = re.sub(r"^\[视频\]", "", title).strip()
        rows.append({"date": _v39_date(ymd), "title": title,
                     "url": ("https:" + href) if href.startswith("//") else href})
    if not rows:
        raise RuntimeError(f"新闻联播 {ymd} 页面没有解析出条目，结构可能已变")
    if with_content:
        for row in rows:
            row["content"] = _cctv_body(row["url"])
            time.sleep(0.2)
    return _v39_frame(rows, "cctv", url)

def _save_payload(encoded, output):
    """先写临时文件；优先硬链接发布，不支持时独占创建并复制，均不覆盖。"""
    import os
    from pathlib import Path
    import tempfile

    parent = Path(output).parent if output is not None else Path.cwd()
    stage = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix="news-sources-", suffix=".json", delete=False) as stream:
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

    parser = argparse.ArgumentParser(description="华尔街见闻/新闻联播：完整表格保存，仅三行预览。")
    commands = parser.add_subparsers(dest="command", required=True)
    wscn = commands.add_parser("wscn", help="华尔街见闻快讯")
    wscn.add_argument("--channel", default="global-channel")
    wscn.add_argument("--limit", type=int, default=50)
    wscn.add_argument("--cursor")
    cctv = commands.add_parser("cctv", help="央视新闻联播")
    cctv.add_argument("date")
    cctv.add_argument("--titles-only", action="store_true", help="只取标题与链接，不请求正文")
    for command in (wscn, cctv):
        command.add_argument("--output", type=Path, help="完整 JSON 新文件，不覆盖")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        frame = (wallstreetcn_lives(args.channel, args.limit, args.cursor) if args.command == "wscn"
                 else cctv_news(args.date, not args.titles_only))
        payload, preview = _frame_payload(frame), _frame_payload(frame.head(3))
        path = _save_payload(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2), args.output)
        print(json.dumps({"output": str(path), "row_count": len(frame), "preview_only": True,
                          "preview": preview}, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
