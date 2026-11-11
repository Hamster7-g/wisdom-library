# -*- coding: utf-8 -*-
"""智慧库开源前全面校验。"""
import os
import re
import subprocess
import sys

ROOT = os.path.abspath('.')
PY = sys.executable
errors = []
warnings = []

# ── 1. Markdown 内部链接可达性 ───────────────────────────
link_re = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
md_files = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in {'.git', 'tools', '原始资料'}]
    for f in fn:
        if f.endswith('.md'):
            md_files.append(os.path.join(dp, f))

broken = 0
for path in md_files:
    rel = os.path.relpath(path, ROOT)
    text = open(path, encoding='utf-8', errors='ignore').read()
    for label, target in link_re.findall(text):
        if target.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        t = target.split('#')[0]
        if not t:
            continue
        # 相对本文件的绝对路径
        abs_t = os.path.normpath(os.path.join(os.path.dirname(path), t))
        if not os.path.exists(abs_t):
            broken += 1
            errors.append('断链 [%s] -> %s (%s)' % (rel, target, label))

print('Markdown 文件数: %d' % len(md_files))
print('断链数: %d' % broken)

# ── 2. 卡片必备字段 ────────────────────────────────────
CARD_DIRS = ['01_身心健康', '02_效率与习惯', '03_学习与科研', '04_沟通与人际', '06_摘录卡片']
REQ = ['## 来源', '## 一句话总结', '## 核心观点', '## 可以实践的小动作', '## 边界与提醒', '## 标签']
cards = 0
for d in CARD_DIRS:
    dp = os.path.join(ROOT, d)
    if not os.path.isdir(dp):
        continue
    for f in sorted(os.listdir(dp)):
        if not f.endswith('.md'):
            continue
        fp = os.path.join(dp, f)
        if '英语词汇' in fp or f in ('README.md', '卡片模板.md'):
            continue
        text = open(fp, encoding='utf-8', errors='ignore').read()
        cards += 1
        for r in REQ:
            if r not in text:
                warnings.append('%s 缺字段 %s' % (f, r))
        if not re.search(r'#\S+', text):
            errors.append('%s 无标签' % f)

print('卡片数(参与校验): %d' % cards)

# ── 3. 版权素材绝不入库 ────────────────────────────────
tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
bad = [t for t in tracked if re.search(r'原始资料|\.docx$|\.pdf$|\.jpg$|\.jpeg$|\.png$|\.webp$', t)]
print('已跟踪文件数: %d' % len(tracked))
print('版权素材误入库: %d' % len(bad))
for b in bad:
    errors.append('版权素材入库: %s' % b)

# ── 4. 脚本可运行 ──────────────────────────────────────
for script in ['tools/build_index.py', 'tools/search.py']:
    r = subprocess.run([PY, script, '--help'], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        errors.append('%s 无法运行: %s' % (script, r.stderr[:200]))
    else:
        print('%s --help OK' % script)

# ── 5. 索引与实际一致 ──────────────────────────────────
r = subprocess.run([PY, 'tools/build_index.py'], cwd=ROOT, capture_output=True, text=True)
print('索引生成: %s' % (r.stdout.strip().splitlines()[0] if r.stdout else r.stderr[:120]))
if r.returncode != 0:
    errors.append('索引生成失败')
git_status = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
if git_status:
    warnings.append('索引刷新后有未提交改动（正常，需 git add）')

# ── 报告 ────────────────────────────────────────────────
print()
print('=' * 50)
if errors:
    print('错误 %d 项：' % len(errors))
    for e in errors:
        print('  ✗', e)
else:
    print('✓ 无错误')
if warnings:
    print('提示 %d 项：' % len(warnings))
    for w in warnings:
        print('  ·', w)
sys.exit(1 if errors else 0)
