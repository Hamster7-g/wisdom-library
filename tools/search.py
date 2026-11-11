#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智慧库检索工具
================
在库内做全文与标签检索，直接在终端给出结果，不依赖任何外部工具。

用法：
    python tools/search.py 关键词              # 全文搜索（标题/正文/标签）
    python tools/search.py 关键词 --tag        # 只按标签精确匹配
    python tools/search.py 情绪 --list         # 列出所有标签及其篇数
    python tools/search.py --stats             # 统计各分类卡片数

选项：
    -n, --num N       最多显示 N 条结果（默认 20）
    -f, --file PATTERN 只在文件名含 PATTERN 的文件中搜索
    -c, --category D  只搜索某个分类目录
    --tag             把关键词当作标签精确匹配
    --list            列出全部标签
    --stats           分类统计
"""

import argparse
import os
import re
import sys
import collections

SKIP_DIRS = {'90_索引', '99_归档', '.git', 'tools', '.obsidian', '原始资料'}
TAG_RE = re.compile(r'#([^\s#，。、；：）)\]】]+)')


def iter_md(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fn in sorted(filenames):
            if fn.endswith('.md'):
                full = os.path.join(dirpath, fn)
                yield full, os.path.relpath(full, root).replace(os.sep, '/')


def extract_tags(text):
    seen = set()
    out = []
    for m in TAG_RE.finditer(text):
        t = m.group(1).strip().rstrip('`')
        if t and len(t) > 1 and not t.isdigit() and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def highlight(line, kw, width=120):
    line = line.strip()
    idx = line.lower().find(kw.lower())
    if idx < 0:
        return line[:width]
    start = max(0, idx - 30)
    end = min(len(line), idx + len(kw) + 60)
    frag = line[start:end]
    return ('…' if start > 0 else '') + frag + ('…' if end < len(line) else '')


def cmd_list(root):
    tag_map = collections.defaultdict(list)
    for full, rel in iter_md(root):
        text = open(full, encoding='utf-8', errors='ignore').read()
        for t in extract_tags(text):
            tag_map[t].append(rel)
    print('共 %d 个标签：\n' % len(tag_map))
    for t, files in sorted(tag_map.items(), key=lambda x: (-len(x[1]), x[0])):
        print('  #%-18s %3d 篇' % (t, len(files)))
    return 0


def cmd_stats(root):
    by_cat = collections.Counter()
    total = 0
    for full, rel in iter_md(root):
        by_cat[rel.split('/')[0] if '/' in rel else '（根目录）'] += 1
        total += 1
    print('共 %d 个 Markdown 文件：\n' % total)
    for c, n in sorted(by_cat.items()):
        print('  %-22s %3d' % (c, n))
    return 0


def do_search(root, kw, by_tag, num, filepat, category):
    hits = []
    for full, rel in iter_md(root):
        if category and not rel.startswith(category):
            continue
        if filepat and filepat.lower() not in os.path.basename(rel).lower():
            continue
        text = open(full, encoding='utf-8', errors='ignore').read()
        tags = extract_tags(text)
        title = ''
        for ln in text.splitlines():
            if ln.startswith('# '):
                title = ln[2:].strip()
                break

        if by_tag:
            if kw not in tags:
                continue
            hits.append((rel, title, '标签匹配：' + ', '.join(tags[:8])))
            continue

        if kw.lower() in text.lower():
            # 找到首个命中行作为上下文
            ctx = ''
            for ln in text.splitlines():
                if kw.lower() in ln.lower():
                    ctx = highlight(ln, kw)
                    break
            hits.append((rel, title, ctx))

    if not hits:
        print('未找到：%s' % kw)
        return 1

    print('找到 %d 条结果：\n' % len(hits))
    for rel, title, ctx in hits[:num]:
        print('  %s' % (title or os.path.basename(rel)))
        print('    %s' % rel)
        if ctx:
            print('    > %s' % ctx)
        print()
    if len(hits) > num:
        print('  …… 另有 %d 条，用 -n 调整显示数量' % (len(hits) - num))
    return 0


def main():
    ap = argparse.ArgumentParser(description='智慧库检索工具')
    ap.add_argument('keyword', nargs='*', help='搜索关键词')
    ap.add_argument('-n', '--num', type=int, default=20, help='最多显示条数')
    ap.add_argument('-f', '--file', dest='filepat', default='', help='只搜文件名含此串的文件')
    ap.add_argument('-c', '--category', default='', help='只搜某个分类目录')
    ap.add_argument('--tag', action='store_true', help='按标签精确匹配')
    ap.add_argument('--list', action='store_true', help='列出全部标签')
    ap.add_argument('--stats', action='store_true', help='分类统计')
    ap.add_argument('--root', default='', help='库根目录（默认为当前目录）')
    args = ap.parse_args()

    root = os.path.abspath(args.root) if args.root else os.path.abspath('.')
    if not os.path.isdir(root):
        print('目录不存在：', root)
        return 2

    if args.list:
        return cmd_list(root)
    if args.stats:
        return cmd_stats(root)
    if not args.keyword:
        ap.print_help()
        return 2

    kw = ' '.join(args.keyword)
    return do_search(root, kw, args.tag, args.num, args.filepat, args.category)


if __name__ == '__main__':
    sys.exit(main())
