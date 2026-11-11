#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智慧库索引生成器
================
扫描库内所有 Markdown 卡片，提取标题、一句话总结、标签，生成：

  90_索引/总索引.md   —— 按分类列出全部卡片（带摘要）
  90_索引/标签索引.md —— 按标签反查卡片（跨分类聚合）

用法：
    python tools/build_index.py            # 在库根目录运行
    python tools/build_index.py --root D:/智慧库
"""

import os
import re
import sys
import time
import collections

# 不参与索引扫描的目录
SKIP_DIRS = {'90_索引', '99_归档', '.git', 'tools', '.obsidian', '原始资料'}

# 词汇库自带索引，由「英语词汇/README.md」单独导航，不计入卡片索引
SKIP_SUBPATHS = ('英语词汇/词汇索引',)

# 分类显示名（目录名 -> 标题）
CATEGORY_ORDER = [
    ('01_身心健康', '身心健康'),
    ('02_效率与习惯', '效率与习惯'),
    ('03_学习与科研', '学习与科研'),
    ('04_沟通与人际', '沟通与人际'),
    ('05_职业与创造', '职业与创造'),
    ('06_摘录卡片', '摘录卡片'),
]

TAG_RE = re.compile(r'#([^\s#，。、；：）)\]】]+)')


def parse_card(path):
    """提取卡片的标题、摘要、标签、所属分类。"""
    try:
        raw = open(path, encoding='utf-8', errors='ignore').read()
    except OSError:
        return None

    lines = raw.splitlines()

    title = ''
    for ln in lines:
        if ln.startswith('# '):
            title = ln[2:].strip()
            break
    if not title:
        title = os.path.splitext(os.path.basename(path))[0]

    # 一句话总结：优先取该小节下第一段非空正文
    summary = ''
    in_sum = False
    for ln in lines:
        if ln.startswith('## '):
            head = ln[3:].strip()
            in_sum = head in ('一句话总结', '摘要')
            if in_sum:
                continue
            if summary:
                break
            continue
        if in_sum:
            s = ln.strip()
            if not s:
                continue
            if s.startswith(('#', '|', '-', '*', '>', '<!--', '- [', '1.', '2.', '3.')):
                continue
            summary = s
            break
    if not summary:
        # 退路：取「核心观点」小节的第一段；再退到全文首个正文段落
        in_core = False
        for ln in lines:
            if ln.startswith('## '):
                in_core = ln[3:].strip() in ('核心观点', '核心内容', '内容')
                continue
            if in_core:
                s = ln.strip()
                if not s:
                    continue
                if s.startswith(('#', '|', '-', '*', '>', '<!--', '- [', '1.', '2.', '3.')):
                    continue
                summary = s
                break
    if not summary:
        for ln in lines:
            s = ln.strip()
            if s and not s.startswith(('#', '|', '-', '*', '>', '<!--')):
                summary = s
                break

    # 标签：优先取「## 标签」小节，否则全文收集
    tags = []
    in_tag = False
    for ln in lines:
        if ln.startswith('## '):
            in_tag = '标签' in ln
            continue
        if in_tag:
            for m in TAG_RE.finditer(ln):
                t = m.group(1).strip().rstrip('`')
                if t and len(t) > 1 and not t.isdigit():
                    tags.append(t)
    if not tags:
        for m in TAG_RE.finditer(raw):
            t = m.group(1).strip().rstrip('`')
            if t and len(t) > 1 and not t.isdigit():
                tags.append(t)

    # 去重保序
    seen = set()
    uniq = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            uniq.append(t)

    return {
        'title': title,
        'summary': summary.replace('\n', ' ').strip(),
        'tags': uniq,
        'path': path,
    }


def collect(root):
    cards = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fn in filenames:
            if not fn.endswith('.md'):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, '/')
            if any(sub in rel for sub in SKIP_SUBPATHS):
                continue
            info = parse_card(full)
            if info:
                info['rel'] = rel
                info['cat'] = rel.split('/')[0] if '/' in rel else '（根目录）'
                cards.append(info)
    return cards


def build_total_index(root, cards):
    out = []
    out.append('# 总索引\n')
    out.append('本文件由 `tools/build_index.py` 自动生成，请勿手工编辑。')
    out.append('新增卡片后重新运行脚本即可刷新。\n')

    total = len(cards)
    out.append('> 共 %d 张卡片。标签反查见 [标签索引](标签索引.md)。\n' % total)

    by_cat = collections.defaultdict(list)
    for c in cards:
        by_cat[c['cat']].append(c)

    for dirname, dispname in CATEGORY_ORDER:
        items = by_cat.get(dirname, [])
        if not items:
            continue
        out.append('## %s\n' % dispname)
        # 按标签数降序，再按标题
        items.sort(key=lambda x: (-len(x['tags']), x['title']))
        for c in items:
            rel_from_index = '../' + c['rel']
            s = c['summary']
            if len(s) > 110:
                s = s[:110] + '…'
            line = '- [%s](%s)' % (c['title'], rel_from_index)
            if s:
                line += '：' + s
            if c['tags']:
                line += '\n  <sub>`%s`</sub>' % '` `'.join(c['tags'][:6])
            out.append(line)
        out.append('')

    # 未列入固定分类的目录（如根目录文件）
    leftovers = [c for c in cards if c['cat'] not in dict(CATEGORY_ORDER)]
    if leftovers:
        out.append('## 其他\n')
        for c in sorted(leftovers, key=lambda x: x['title']):
            out.append('- [%s](../%s)：%s' % (c['title'], c['rel'], c['summary']))
        out.append('')

    # 子库入口（英语词汇等自带独立导航体系的子库）
    sublibs = [
        ('英语词汇库', '../03_学习与科研/英语词汇/README.md',
         '单词、短语、例句与易混词辨析，按主题与易混关系聚合。'),
    ]
    if sublibs:
        out.append('## 子库\n')
        for name, link, desc in sublibs:
            if os.path.exists(os.path.join(root, link.replace('../', ''))):
                out.append('- [%s](%s)：%s' % (name, link, desc))
        out.append('')

    return '\n'.join(out)


def build_tag_index(cards):
    tag_map = collections.defaultdict(list)
    for c in cards:
        for t in c['tags']:
            tag_map[t].append(c)

    out = []
    out.append('# 标签索引\n')
    out.append('本文件由 `tools/build_index.py` 自动生成，请勿手工编辑。')
    out.append('标签是跨分类的横切维度：一个标签可以横跨多个分类，')
    out.append('因此同一条知识往往能通过多条路径被找到。\n')
    out.append('> 共 %d 个标签。卡片总数见 [总索引](总索引.md)。\n' % len(tag_map))

    # 按出现次数分组：高频标签优先
    buckets = [
        ('高频标签（3 篇以上）', lambda n: n >= 3),
        ('中频标签（2 篇）', lambda n: n == 2),
        ('低频标签（1 篇）', lambda n: n == 1),
    ]
    for title, pred in buckets:
        items = [(t, v) for t, v in tag_map.items() if pred(len(v))]
        if not items:
            continue
        items.sort(key=lambda x: (-len(x[1]), x[0]))
        out.append('## %s\n' % title)
        for t, v in items:
            out.append('### #%s（%d 篇）\n' % (t, len(v)))
            for c in sorted(v, key=lambda x: x['title']):
                out.append('- [%s](../%s) — %s' % (c['title'], c['rel'], c['summary']))
            out.append('')

    return '\n'.join(out)


def write_index(path, content):
    """写索引文件。

    Windows 索引服务/搜索索引可能短暂持有刚生成的文件句柄，
    直接覆盖会报 PermissionError。这里先尝试删除旧文件再写，
    失败则退避重试。
    """
    for attempt in range(6):
        try:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except OSError:
            time.sleep(0.6 * (attempt + 1))
    # 最后手段：写到临时名再替换
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(content)
    os.replace(tmp, path)
    return True


def main():
    root = os.path.abspath('.')
    if '--root' in sys.argv:
        root = os.path.abspath(sys.argv[sys.argv.index('--root') + 1])

    idx_dir = os.path.join(root, '90_索引')
    os.makedirs(idx_dir, exist_ok=True)

    cards = collect(root)
    if not cards:
        print('未找到任何卡片，检查路径：', root)
        return 1

    write_index(os.path.join(idx_dir, '总索引.md'), build_total_index(root, cards))
    write_index(os.path.join(idx_dir, '标签索引.md'), build_tag_index(cards))

    ntags = len({t for c in cards for t in c['tags']})
    print('索引已生成：%d 张卡片 / %d 个标签' % (len(cards), ntags))
    print('  -> 90_索引/总索引.md')
    print('  -> 90_索引/标签索引.md')
    return 0


if __name__ == '__main__':
    sys.exit(main())
