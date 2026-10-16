#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""03_filter_rank.py —— 从清洗后的岗位表里筛出「技能匹配」的候选并排序。

输入：data/processed/岗位记录-清洗版.csv
输出：data/processed/技能匹配排名.json、outputs/海投第1批50家.json

口径：
  · 必过：届次含 2027 届
  · 正向词（数据/分析/商业/运营/产品/管培…）计分，负向词（工程师/算法/研发/土木…）扣分
  · ★ = JD 中明确出现「数据分析/商业分析/数据科学/数据挖掘/经营分析/统计分析/数据运营/数据产品/数据治理」
  · 按公司去重（公司名规范化），同公司取最高分那条
"""
import csv
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, '..', 'data', 'processed', '岗位记录-清洗版.csv')
OUT_DIR = os.path.join(HERE, '..', 'data', 'processed')
OUTPUTS = os.path.join(HERE, '..', 'outputs')

GBA = ['香港', '澳门', '深圳', '广州', '东莞', '珠海', '佛山', '中山', '惠州', '江门', '肇庆']
POS = ['数据分析', '商业分析', '数据科学', '数据挖掘', '数据运营', '数据产品', '数据治理', '经营分析',
       '商业策略', '统计分析', '财务分析', '市场分析', '用户研究', '咨询', '管培', '培训生', '运营',
       '产品经理', '战略', '研究', '风控', '建模', '量化', '审计', '分析师']
NEG = ['研发管培', '工艺', '生产管培', '设备管培', '质量管培', '有机合成', '制剂', '试剂', '芯片',
       '结构设计', '机械', '电气', '土木', '材料', '化工', '生物', '医药', '焊接', '冶金', '采矿',
       '地质', '测绘', '临床', '护理', '光学', '暖通', '管道', 'BIM', '硬件', '嵌入式', '算法']
STRONG = re.compile(r'数据分析|商业分析|数据科学|数据挖掘|经营分析|统计分析|数据运营|数据产品|数据治理')


def norm_co(co):
    co = re.sub(r'\s+', '', co or '')
    co = re.sub(r'（.*?）|\(.*?\)|\[.*?\]', '', co)
    return re.sub(r'中国区$|中国$|集团$|股份有限公司$|有限公司$', '', co)


def loc(t):
    parts = [x.strip() for x in re.split(r'[|｜/、]', t or '') if x.strip()]
    g = [p for p in parts if any(k in p for k in GBA)]
    return '、'.join(g[:3]) if g else '、'.join(parts[:3])


def main():
    rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig')))
    cand = []
    for r in rows:
        if '2027届' not in (r.get('届次') or ''):
            continue
        job = r.get('招聘岗位') or ''
        p = sum(job.count(k) for k in POS)
        n = sum(job.count(k) for k in NEG)
        if p < 2 or p - 2 * n < 1:
            continue
        r['_net'] = p - 2 * n
        r['_key'] = bool(STRONG.search(job))
        cand.append(r)

    byco = {}
    for r in cand:
        k = norm_co(r.get('公司名称'))
        if not k:
            continue
        r['_score'] = r['_net'] + (6 if r['_key'] else 0) + \
            (2 if any(c in (r.get('工作地点') or '') for c in ['香港', '澳门', '深圳', '广州', '东莞']) else 0)
        if k not in byco or r['_score'] > byco[k]['_score']:
            byco[k] = r

    ranked = sorted(byco.values(), key=lambda r: (-r['_score'], r.get('公司名称') or ''))
    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump(ranked, open(os.path.join(OUT_DIR, '技能匹配排名.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('候选公司 %d 家' % len(ranked))
    print('性质分布:', Counter(r.get('企业性质') or '空' for r in ranked).most_common(6))

    # 第一批 50 家（剔 8 家不匹配 + 7 家过期 + 1 家关联公司）
    DROP = {'腾讯光子工作室群', 'DeepSeek', '华为公共开发部', '联想-AI专项', '中国科学院空间应用工程与技术中心',
            '煤炭科学研究总院有限公司', '创维集团', '领益智造', 'Joyin玩聚星球'}
    EXPIRED = {'电力规划总院有限公司（电规总院）', 'Sea', '工银瑞信', '申万宏源研究', '中国银行',
               '神州信息', '天健会计师事务所'}
    pick = [r for r in ranked if r.get('公司名称') not in DROP and r.get('公司名称') not in EXPIRED][:50]

    RULES = [('V4', r'风控策略|信用风险|授信|风险模型|风控模型|信用评级|PAYDEX|信贷|贷款|风险策略'),
             ('V2', r'AI ?产品|AI ?应用|大模型|智能体|Agent|数据产品|AI ?数据|AI ?解决'),
             ('V3', r'增长|商业化|投放|转化率|GMV|电商运营|用户增长|市场策略|渠道运营|直播运营')]

    def version(job):
        for v, pat in RULES:
            if re.search(pat, job or '', re.I):
                return v
        return 'V1'

    out = []
    for i, r in enumerate(pick, 1):
        out.append({'#': i, '公司': r.get('公司名称'), '性质': r.get('企业性质') or '—',
                    '地点': loc(r.get('工作地点')), '岗位': (r.get('招聘岗位') or '').replace('\n', ' '),
                    '学历': r.get('学历要求') or '—', '截止': r.get('截止时间') or '尽快投递',
                    '链接': r.get('投递链接') or '', '版本': version(r.get('招聘岗位')),
                    '重点': bool(r.get('_key'))})
    os.makedirs(OUTPUTS, exist_ok=True)
    json.dump(out, open(os.path.join(OUTPUTS, '海投第1批50家.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('第 1 批 %d 家' % len(out))
    print('版本分布:', Counter(o['版本'] for o in out).most_common())


if __name__ == '__main__':
    main()
