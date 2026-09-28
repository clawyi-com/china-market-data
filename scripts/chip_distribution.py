# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""本地筹码分布计算，输入 CSV/records JSON，不联网。"""
try:
    import _runtime  # noqa: F401  须在第三方库之前导入
except ModuleNotFoundError:  # 单文件复制安装时没有 helper
    pass
import numpy as np
import pandas as pd


def _triangular_weights(grid: np.ndarray, low: float, high: float, avg: float) -> np.ndarray:
    """当日筹码在价格网格上的三角分布权重（峰值在均价，面积归一）"""
    w = np.zeros_like(grid)
    if not np.isfinite([low, high, avg]).all() or high < low:
        return w
    if high - low < 1e-9:                       # 一字板：全部堆在一个价位
        w[np.argmin(np.abs(grid - low))] = 1.0
        return w
    avg = min(max(avg, low), high)              # 均价必须落在当日区间内
    left = (grid >= low) & (grid <= avg)
    right = (grid > avg) & (grid <= high)
    if avg - low > 1e-9:
        w[left] = (grid[left] - low) / (avg - low)
    else:
        w[left] = 1.0
    if high - avg > 1e-9:
        w[right] = (high - grid[right]) / (high - avg)
    else:
        w[right] = 1.0
    total = w.sum()
    if total > 0:
        return w / total
    # 🔴 兜底：当日振幅窄于网格步长时，可能一个网格点都没落进 [low, high]，
    #    权重会全为 0。若就此跳过该日，连它的换手衰减也会一并丢失 ——
    #    低波动标的（银行股等）+ 长窗口下这会累积成很大的偏差。映射到最近网格点。
    w[np.argmin(np.abs(grid - avg))] = 1.0
    return w


def chip_distribution(df: pd.DataFrame, grid_size: int = 300, decay: float = 1.0) -> dict:
    """筹码分布 — df 需含 high/low/close/turn（turn 为百分数，0.31 表示 0.31%）

    decay: 换手衰减系数。1.0=按真实换手率换手；同花顺口径常用 1.5~2.0 加快历史筹码消散。
    """
    # 🔴 必须带 date 并按时间升序：换手衰减是有方向的时序递推，
    #    若传入常见的「最新在前」倒序，衰减会反向推、且 close.iloc[-1] 会把最老的
    #    收盘价当成现价 —— 结果完全错却不会报错。这里强制要求 date 并自行排序。
    need = {"date", "high", "low", "close", "turn"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"chip_distribution 缺少列: {sorted(missing)}（date 用于强制时间升序）")
    d = df.dropna(subset=["high", "low", "close", "turn"]).copy()
    d = d[d["high"] > 0]
    if d.empty:
        raise ValueError("chip_distribution: 有效行数为 0（检查是否全是停牌日，或字段类型不对）")
    d = d.sort_values("date").reset_index(drop=True)

    lo, hi = float(d["low"].min()), float(d["high"].max())
    pad = (hi - lo) * 0.02 or max(lo * 0.02, 0.01)
    grid = np.linspace(lo - pad, hi + pad, grid_size)

    # 🔴 初始筹码必须播种成「首日全部流通盘」，不能从全零开始。
    #    从零起步等于假设窗口之前没有任何持仓，再把窗口内的少量换手归一化成 100%：
    #    两个 1% 换手日（价 10 和 100）会被算成约 50/50，而真实情况是约 99% 仍在 10 附近。
    chips = None
    for row in d.itertuples(index=False):
        t = float(row.turn) / 100.0 * decay
        t = min(max(t, 0.0), 1.0)               # 换手率兜到 [0,1]，防异常值把筹码一次清零
        avg = (float(row.high) + float(row.low) + float(row.close)) / 3.0
        w = _triangular_weights(grid, float(row.low), float(row.high), avg)
        if w.sum() <= 0:
            continue
        if chips is None:
            chips = w.copy()                    # 首日分布 = 期初全部流通筹码
            continue
        chips = chips * (1.0 - t) + w * t
    if chips is None:
        raise RuntimeError("chip_distribution: 所有交易日的价格区间都无效，无法构建分布")

    total = chips.sum()
    if total <= 0:
        raise RuntimeError("chip_distribution: 筹码总量为 0，无法计算指标")
    chips = chips / total

    price = float(d["close"].iloc[-1])
    cum = np.cumsum(chips)

    def price_at(q: float) -> float:
        return float(np.interp(q, cum, grid))

    p05, p15, p85, p95 = (price_at(q) for q in (0.05, 0.15, 0.85, 0.95))
    peak_i = int(np.argmax(chips))
    return {
        "price": price,
        "profit_ratio": float(chips[grid <= price].sum()),      # 获利比例
        "avg_cost": float((grid * chips).sum()),                # 平均成本
        "cost_90": (p05, p95),
        "cost_70": (p15, p85),
        "concentration_90": float((p95 - p05) / (p95 + p05)) if p95 + p05 else None,
        "concentration_70": float((p85 - p15) / (p85 + p15)) if p85 + p15 else None,
        "peak_price": float(grid[peak_i]),                      # 筹码峰
        "histogram": [(float(pp), float(cc)) for pp, cc in zip(grid, chips) if cc > 1e-6],
    }



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
    # numpy 标量转为等值 Python 标量；筹码结果字段没有任意对象列。
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
                                         prefix="chip-distribution-", suffix=".json", delete=False) as stream:
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
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description="本地筹码分布：CSV/records JSON 输入，完整结果落盘。")
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("csv", "json"), help="默认按 .csv/.json 后缀推断")
    parser.add_argument("--grid-size", type=int, default=300)
    parser.add_argument("--decay", type=float, default=1.0)
    parser.add_argument("--output", type=Path, help="完整结果新文件，不覆盖")
    args = parser.parse_args(argv)
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("输出文件已存在，请指定新路径")
    kind = args.format or args.input.suffix.lower().lstrip(".")
    if kind not in ("csv", "json"):
        parser.error("请提供 .csv/.json 文件或指定 --format")
    try:
        if kind == "csv":
            frame = pd.read_csv(args.input, encoding="utf-8")
        else:
            records = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
                raise ValueError("JSON 输入须为对象数组（records）")
            frame = pd.DataFrame.from_records(records)
        result = chip_distribution(frame, args.grid_size, args.decay)
        payload = _json_safe(result)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        path = _save_payload(encoded, args.output)
        print(json.dumps({"output": str(path), "histogram_points": len(payload["histogram"]),
                          "preview_only": True, "preview": {**payload, "histogram": payload["histogram"][:3]}},
                         ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
