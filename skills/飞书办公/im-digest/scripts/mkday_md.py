#!/usr/bin/env python3
"""从小时情报状态文件生成飞书日节点用的 Markdown。"""
import argparse, json, sys
from pathlib import Path

def src(x):
    s = f"{x.get('source','')} · {x.get('session','')} · {x.get('time','')}"
    ls = ' · '.join(f"[{l['label']}]({l['url']})" for l in x.get('links', []) if l.get('url'))
    return s + (' · ' + ls if ls else '')

def render(d):
    o = [f"**最要紧**：{d['top']}", '', '## 要处理的']
    todos = [t for t in d.get('todo') or [] if t.get('status') != '已解决']
    if not todos:
        o.append("- 今天没有条目。")
    for t in todos:
        o.append(f"- [{t.get('priority','')}] {t.get('title') or t.get('text','')}（{src(t)}）")
    o += ['', '## 客户与商单']
    clients = d.get('clients') or []
    if not clients:
        o.append("- 今天没有进行中的客户或商单。")
    for c in clients:
        ls = ' · '.join(f"[{l['label']}]({l['url']})" for l in c.get('links', []) if l.get('url'))
        contact = f"（{c['contact']}）" if c.get('contact') else ''
        o.append(
            f"- **{c.get('client','')}{contact}**｜{c.get('project','')}｜{c.get('stage','')}｜"
            f"{c.get('blocker') or c.get('next','')}（{c.get('source','')} · {c.get('session','')} · {c.get('time','')}"
            f"{' · ' + ls if ls else ''}）"
        )
    for k, h in [('know', '值得知道的'), ('topics', '可写的选题'), ('resolved', '今日已解决')]:
        o += ['', f'## {h}']
        items = d.get(k) or []
        if not items:
            o.append("- 今天没有条目。")
        for x in items:
            o.append(f"- {x.get('title') or x.get('text','')}（{src(x)}）")
    parked = d.get('todo_parked') or []
    if parked:
        o += ['', '## 待跟进（已收起）', f"- 另有 {len(parked)} 条低优先级或暂无新进展的欠回复仍收在待跟进，本轮不逐条展开。"]
    text = '\n'.join(o) + '\n'
    if any(ch in text for ch in '「」『』'):
        raise SystemExit('output contains CJK corner quotes; rewrite before writing the wiki node')
    return text

def main():
    p = argparse.ArgumentParser(description="Render Feishu day-node Markdown from digest state JSON.")
    p.add_argument('--state', required=True, help='Path to the day state JSON')
    p.add_argument('--output', '-o', help='Write Markdown here (default: stdout)')
    args = p.parse_args()
    d = json.loads(Path(args.state).read_text(encoding='utf-8'))
    text = render(d)
    if args.output:
        Path(args.output).write_text(text, encoding='utf-8')
    else:
        sys.stdout.write(text)

if __name__ == '__main__':
    main()
