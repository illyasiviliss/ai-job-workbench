#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02_build_records.py —— 把飞书接口的原始响应拼成一张干净的表。

输入：data/raw/records_*.json(.gz) + clientvars（含 base schema）
输出：data/processed/岗位记录-清洗版.csv

做三件事：
  1. 把 base64+gzip 的 schema 解出来，拿到 fieldMap（字段 ID → 中文名）与各选项 ID → 标签
  2. 合并三个分页的 recordMap，按 recordID 去重
  3. 逐条把字段 ID 与选项 ID 还原成人看得懂的文本
"""
import base64
import csv
import datetime
import glob
import gzip
import json
import os

RAW = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')


def load_schema():
    """base schema 是 base64+gzip；fieldMap 里有字段名与选项标签。"""
    src = os.path.join(RAW, 'clientvars.json')
    op = gzip.open if os.path.exists(src + '.gz') else open
    with op(src + '.gz' if os.path.exists(src + '.gz') else src, 'rt', encoding='utf-8') as f:
        d = json.load(f)['data']
    txt = gzip.decompress(base64.b64decode(d['table'])).decode('utf-8')
    return json.loads(txt)['fieldMap']


def load_records():
    """合并所有分页，按 recordID 去重。"""
    seen, rows = set(), []
    for p in sorted(glob.glob(os.path.join(RAW, 'records_*.json*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt', encoding='utf-8') as f:
            rm = json.load(f).get('recordMap', {})
        for rid, rec in rm.items():
            if rid in seen:
                continue
            seen.add(rid)
            rows.append((rid, rec))
    return rows


def main():
    fmap = load_schema()
    opt = {fid: {o['id']: o.get('name', '') for o in (f.get('property') or {}).get('options', [])}
           for fid, f in fmap.items()}
    name = {fid: f.get('name', fid) for fid, f in fmap.items()}

    def cell(rec, fid):
        v = (rec.get(fid) or {}).get('value')
        if v is None:
            return ''
        if isinstance(v, str):
            return opt.get(fid, {}).get(v, v)
        if isinstance(v, list):
            out = []
            for x in v:
                if isinstance(x, str):
                    out.append(opt.get(fid, {}).get(x, x))
                elif isinstance(x, dict):
                    out.append(x.get('text') or x.get('link') or '')
            return ' | '.join(y for y in out if y)
        if isinstance(v, (int, float)):
            if fmap[fid].get('type') == 5:  # 日期字段（毫秒时间戳）
                try:
                    return datetime.datetime.fromtimestamp(v / 1000).strftime('%Y-%m-%d')
                except Exception:
                    pass
            return str(v)
        return str(v)

    rows = load_records()
    fields = [fid for fid in fmap]
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, '岗位记录-清洗版.csv')
    with open(dst, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['recordID'] + [name[fid] for fid in fields])
        for rid, rec in rows:
            w.writerow([rid] + [cell(rec, fid) for fid in fields])
    print('写入 %s（%d 条记录、%d 个字段）' % (dst, len(rows), len(fields)))


if __name__ == '__main__':
    main()
