# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""iwencai 语义搜索、数据查询及原生去重；凭据从环境读取。"""
try:
    import _runtime  # noqa: F401  须在第三方库之前导入
except ModuleNotFoundError:  # 单文件复制安装时没有 helper
    pass
import os
import json
import secrets
import requests

IWENCAI_BASE = os.environ.get("IWENCAI_BASE_URL", "https://openapi.iwencai.com")
IWENCAI_KEY = os.environ.get("IWENCAI_API_KEY", "")

def _claw_headers(call_type: str = "normal") -> dict:
    """SkillHub 2.0 必须的 X-Claw 鉴权头"""
    return {
        "X-Claw-Call-Type": call_type,
        "X-Claw-Skill-Id": "report-search",
        "X-Claw-Skill-Version": "2.0.0",
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }

def iwencai_search(query: str, channel: str = "report", size: int = 50) -> list[dict]:
    """
    iwencai 语义搜索。
    channel: "report"(研报) / "announcement"(公告) / "news"(新闻)
    size: 默认10, 实测可调到50（隐藏参数）
    """
    headers = {
        "Authorization": f"Bearer {IWENCAI_KEY}",
        "Content-Type": "application/json",
        **_claw_headers(),
    }
    payload = {
        "channels": [channel],
        "app_id": "AIME_SKILL",
        "query": query,
        "size": size,
    }
    r = requests.post(
        f"{IWENCAI_BASE}/v1/comprehensive/search",
        json=payload, headers=headers, timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"iwencai HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    if data.get("status_code", 0) != 0:
        raise RuntimeError(f"iwencai error: {data.get('status_msg', '')}")
    return data.get("data") or []

def iwencai_query(query: str, page: int = 1, limit: int = 50) -> list[dict]:
    """
    iwencai NL数据查询（结构化字段）。
    例: "贵州茅台 ROE" → DataFrame-like rows
    """
    headers = {
        "Authorization": f"Bearer {IWENCAI_KEY}",
        "Content-Type": "application/json",
        **_claw_headers(),
    }
    payload = {
        "query": query,
        "page": str(page),
        "limit": str(limit),
        "is_cache": "1",
        "expand_index": "true",
    }
    r = requests.post(
        f"{IWENCAI_BASE}/v1/query2data",
        json=payload, headers=headers, timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"iwencai HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    if data.get("status_code", 0) != 0:
        raise RuntimeError(f"iwencai error: {data.get('status_msg', '')}")
    return data.get("datas") or []

def dedup_articles(articles: list[dict]) -> list[dict]:
    """同一uid仅保留score最高的段落"""
    best = {}
    for a in articles:
        uid = a.get("uid", "") or f"{a.get('title','')}|{a.get('publish_date','')}"
        score = float(a.get("score", 0))
        if uid not in best or score > float(best[uid].get("score", 0)):
            best[uid] = a
    return sorted(best.values(), key=lambda x: x.get("publish_date", ""), reverse=True)


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
    # numpy 标量转为等值 Python 标量；iwencai JSON 字段没有任意对象列。
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
                                         prefix="iwencai-", suffix=".json", delete=False) as stream:
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


def _read_records(path):
    """读取 JSON 记录列表；还原本 CLI 的保留 $float 单键标记。"""
    def decode(value):
        if set(value) == {"$float"}:
            tags = {"NaN": float("nan"), "Infinity": float("inf"), "-Infinity": -float("inf")}
            tag = value["$float"]
            if not isinstance(tag, str) or tag not in tags:
                raise ValueError("无效 $float 标记")
            return tags[tag]
        return value
    with path.open(encoding="utf-8") as stream:
        records = json.load(stream, object_hook=decode)
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise ValueError("输入必须是 JSON 对象列表；DataFrame 请使用 Python API")
    return records


def main(argv=None):
    import argparse
    from contextlib import redirect_stdout
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description="iwencai 搜索/查询/去重；完整 JSON 保存，终端只给预览。")
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="自然语言搜索研报/公告/新闻")
    search.add_argument("query")
    search.add_argument("--channel", default="report")
    search.add_argument("--size", type=int, default=50)
    search.add_argument("--dedup", action="store_true", help="显式应用旧版 uid/score 去重，默认保留所有段落")
    query = commands.add_parser("query", help="自然语言结构化查询")
    query.add_argument("query")
    query.add_argument("--page", type=int, default=1)
    query.add_argument("--limit", type=int, default=50)
    dedup = commands.add_parser("dedup", help="对本地 JSON 对象列表去重，不联网、不需要 Key")
    dedup.add_argument("input", type=Path)
    for command in (search, query, dedup):
        command.add_argument("--output", type=Path, help="完整 JSON 新文件；不覆盖已有路径")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    try:
        if args.command != "dedup" and not IWENCAI_KEY:
            raise ValueError("未设置 IWENCAI_API_KEY；请在启动进程前配置环境变量")
        with redirect_stdout(sys.stderr):
            if args.command == "search":
                result = iwencai_search(args.query, channel=args.channel, size=args.size)
                if args.dedup:
                    result = dedup_articles(result)
            elif args.command == "query":
                result = iwencai_query(args.query, page=args.page, limit=args.limit)
            else:
                articles = _read_records(args.input)
                result = dedup_articles(articles)
        payload = _json_safe(result)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        path = _save_payload(encoded, args.output)
        is_list = isinstance(payload, list)
        print(json.dumps({"output": str(path), "row_count": len(payload) if is_list else None,
                          "preview_only": True, "preview": payload[:3] if is_list else
                          {"type": type(payload).__name__, "see_full_file": True}},
                         ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
