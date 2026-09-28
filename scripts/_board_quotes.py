# Part of china-market-data, derived from a-stock-data (Copyright 2026 Simon Lin).
# Modified/added by china-market-data contributors; see ../UPSTREAM.md and ../NOTICE.
# SPDX-License-Identifier: Apache-2.0
"""Validated board price rankings; shared Eastmoney throttling, bounded pagination."""
import math
from datetime import datetime, timezone
from _eastmoney import em_get, UA


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def board_quotes(board_type='industry', period='today', top_n=20, source='push2'):
    if board_type not in ('industry', 'concept') or period not in ('today', '5d'):
        raise ValueError('支持 industry/concept 和 today/5d')
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n <= 0:
        raise ValueError('top_n 必须为正整数')
    if source not in ('push2', 'dataapi'):
        raise ValueError('source 须为 push2/dataapi')
    fid = 'f3' if period == 'today' else 'f109'
    fs = 'm:90+t:' + ('2' if board_type == 'industry' else '3')
    url = ('https://push2.eastmoney.com/api/qt/clist/get' if source == 'push2'
           else 'https://data.eastmoney.com/dataapi/bkzj/getbkzj')
    items, seen, total = [], set(), None
    for pn in range(1, 51):
        params = ({'pn': str(pn), 'pz': '100', 'po': '1', 'np': '1',
                   'fltt': '2', 'invt': '2', 'fid': fid, 'fs': fs,
                   'fields': f'f12,f14,{fid},f104,f105,f140,f136'}
                  if source == 'push2' else {'key': fid, 'code': fs})
        response = em_get(url, params=params, headers={
            'User-Agent': UA, 'Referer': 'https://data.eastmoney.com/bkzj/'}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if str(payload.get('rc', 0)) != '0':
            raise ValueError('板块接口业务错误')
        data = payload.get('data')
        if not isinstance(data, dict) or 'total' not in data:
            raise ValueError('板块接口缺少 data/total，无法确认覆盖范围')
        page_total = int(data['total'])
        if page_total == 0:
            raise ValueError('板块接口返回 0 个板块，无法确认覆盖范围')
        if page_total < 0 or (total is not None and page_total != total):
            raise ValueError('分页期间板块总数变化，请稍后重试')
        total = page_total
        diff = data.get('diff')
        if isinstance(diff, dict):
            diff = list(diff.values())
        if not isinstance(diff, list):
            raise ValueError('板块接口缺少 diff')
        for item in diff:
            code = item.get('f12')
            if not code or code in seen:
                raise ValueError('板块分页重复或代码缺失，拒绝发布不完整排名')
            seen.add(code)
            items.append(item)
        if len(items) == total:
            break
        if len(items) > total or not diff or source == 'dataapi':
            raise ValueError('板块数据不完整，拒绝发布全市场排名')
    else:
        raise ValueError('板块分页超过 50 页上限')
    rows, missing = [], []
    for item in items:
        value = number(item.get(fid))
        daily_fields = source == 'push2' and period == 'today'
        row = {'code': item['f12'], 'name': item.get('f14', ''),
               'change_pct': value / 100 if value is not None and source == 'dataapi' else value,
               'up_count': item.get('f104') if daily_fields else None,
               'down_count': item.get('f105') if daily_fields else None,
               'leader': item.get('f140') if daily_fields else None,
               'leader_change': number(item.get('f136')) if daily_fields else None}
        if value is None:
            row['change_pct_raw'] = item.get(fid)
            # Nonfinite floats cannot be emitted as strict JSON; preserve their text.
            if isinstance(row['change_pct_raw'], float) and not math.isfinite(row['change_pct_raw']):
                row['change_pct_raw'] = str(row['change_pct_raw'])
        (missing if value is None else rows).append(row)
    rows.sort(key=lambda row: (-row['change_pct'], row['code']))
    for rank, row in enumerate(rows, 1):
        row['rank'] = rank
    return {'board_type': board_type, 'period': period, 'source': url,
            'fetched_at': datetime.now(timezone.utc).isoformat(), 'quote_time': None,
            'total': total, 'fetched_count': len(items), 'ranked_count': len(rows),
            'complete': True, 'ranking_complete': not missing,
            'missing_count': len(missing), 'missing': missing, 'unit': 'percent',
            'top': rows[:top_n], 'bottom': rows[-top_n:]}
