#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 仓库创建 + 推送（自动化）

用法：
    python tools/publish.py <github用户名> <仓库名> [token]
    python tools/publish.py Hamster7-g wisdom-library ghp_xxxxx

token 也可通过环境变量提供：
    set GITHUB_TOKEN=ghp_xxxxx
    python tools/publish.py Hamster7-g wisdom-library

注意：
  - api.github.com 走代理可达；github.com 网页在本机被代理阻断，
    所以建仓走 API、推送走 SSH（SSH 通道已验证可用）。
  - token 只在内存中使用，不写入任何文件、不进 git 历史。
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

API = 'https://api.github.com'


def api(method, path, token, body=None):
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('X-GitHub-Api-Version', '2022-11-28')
    req.add_header('User-Agent', 'wisdom-library-publisher')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode('utf-8')
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'ignore')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:400]}
    except Exception as e:
        return 0, {'error': str(e)}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    user = sys.argv[1]
    repo = sys.argv[2]
    token = sys.argv[3] if len(sys.argv) > 3 else os.environ.get('GITHUB_TOKEN', '')

    if not token:
        print('缺少 token。用法：python tools/publish.py <用户名> <仓库名> <token>')
        print('或设置环境变量 GITHUB_TOKEN')
        return 2

    # ── 1. 校验 token ──────────────────────────────────
    print('[1/4] 校验 token ...')
    code, data = api('GET', '/user', token)
    if code != 200:
        print('  ✗ token 无效或权限不足：', data.get('message', data))
        return 1
    login = data.get('login')
    print('  ✓ token 有效，账号：%s' % login)
    if login.lower() != user.lower():
        print('  ! 注意：token 账号是 %s，与指定的 %s 不同，将使用 %s' % (login, user, login))
        user = login

    # ── 2. 建仓 ───────────────────────────────────────
    print('[2/4] 创建仓库 %s/%s ...' % (user, repo))
    code, data = api('GET', '/repos/%s/%s' % (user, repo), token)
    if code == 200:
        print('  ✓ 仓库已存在，跳过创建')
    else:
        body = {
            'name': repo,
            'description': '个人知识库：Markdown 卡片 + 双层索引体系（目录管归属，标签管检索）',
            'private': False,
            'auto_init': False,      # 本地已有提交，不要让它建初始 commit
            'has_issues': True,
            'has_wiki': False,
        }
        code, data = api('POST', '/user/repos', token, body)
        if code not in (200, 201):
            print('  ✗ 创建失败(%s)：%s' % (code, data.get('message', data)))
            return 1
        print('  ✓ 创建成功：%s' % data.get('html_url'))

    # ── 3. 配置远程并推送 ─────────────────────────────
    print('[3/4] 配置远程并推送（SSH）...')
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ssh_url = 'git@github.com:%s/%s.git' % (user, repo)

    def git(*args, **kw):
        return subprocess.run(['git'] + list(args), cwd=root,
                              capture_output=True, text=True, **kw)

    r = git('remote', 'get-url', 'origin')
    if r.returncode == 0:
        git('remote', 'set-url', 'origin', ssh_url)
    else:
        git('remote', 'add', 'origin', ssh_url)
    print('  origin -> %s' % ssh_url)

    r = git('push', '-u', 'origin', 'main')
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        print('\n  ✗ 推送失败。常见原因：')
        print('    · 代理/网络挡住了 git 的 SSH 通道')
        print('    · SSH key 未添加到账号：cat ~/.ssh/id_ed25519.pub')
        return 1

    # ── 4. 验证 ───────────────────────────────────────
    print('[4/4] 验证远程内容 ...')
    code, data = api('GET', '/repos/%s/%s' % (user, repo), token)
    if code == 200:
        print('  ✓ 仓库地址：%s' % data.get('html_url'))
        print('  ✓ 默认分支：%s' % data.get('default_branch'))
        print('  ✓ 可见性：%s' % ('private' if data.get('private') else 'public'))
    code, data = api('GET', '/repos/%s/%s/contents/README.md' % (user, repo), token)
    if code == 200:
        print('  ✓ README.md 已上传')

    print()
    print('完成 → https://github.com/%s/%s' % (user, repo))
    return 0


if __name__ == '__main__':
    sys.exit(main())
