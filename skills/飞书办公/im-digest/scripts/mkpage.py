#!/usr/bin/env python3
"""从小时情报状态文件生成 Cursor / Grok Page 的 TSX 源码。可选输出。"""
import argparse, json
from pathlib import Path

def q(s):
    return json.dumps(s, ensure_ascii=False)

def ls(x):
    return '[' + ', '.join(f'[{q(l["label"])}, {q(l["url"])}]' for l in x.get('links', []) if l.get('url')) + ']'

def srctext(x):
    return f"{x.get('source','')} · {x.get('session','')} · {x.get('time','')}".replace('【', '').replace('】', ' · ')

def src(x):
    return f'<Source text={{{q(srctext(x))}}}' + (f' ls={{{ls(x)}}}' if any(l.get('url') for l in x.get('links') or []) else '') + ' />'

tone = {'高': 'danger', '中': 'warning'}
stage_tone = {'等回款': 'warning', '交付': 'success', '等确认': 'warning'}

def join_rows(rows):
    if not rows:
        return '[]'
    return '[\n            ' + ',\n            '.join(rows) + ',\n          ]'

def render(d):
    md = d['date'][5:]
    rows_todo = []
    for t in d.get('todo') or []:
        if t.get('status') == '已解决':
            continue
        p = t.get('priority') or ''
        pc = f'{{ text: {q(p)}, tone: {q(tone[p])} }}' if p in tone else q(p)
        has_links = any(l.get('url') for l in t.get('links') or [])
        lk = f'links({ls(t)})' if has_links else '""'
        rows_todo.append(f'[{pc}, {q(t.get("title") or t.get("text",""))}, {q(srctext(t))}, {lk}]')
    rows_cl = []
    for c in d.get('clients') or []:
        name = c.get('client', '') + (f"（{c['contact']}）" if c.get('contact') else '')
        st = c.get('stage') or ''
        sc = f'{{ text: {q(st)}, tone: {q(stage_tone[st])} }}' if st in stage_tone else q(st)
        rows_cl.append(f'[{q(name)}, {q(c.get("project",""))}, {sc}, {q(c.get("blocker") or c.get("next",""))}, {src(c)}]')
    def two(k):
        return [f'[{q(x.get("title") or x.get("text",""))}, {src(x)}]' for x in d.get(k) or []]
    tsx = f'''import {{ Page, Section, Table, useGrokTheme }} from "grok/canvas";

type L = [string, string];

function links(ls: L[]) {{
  return (
    <span>
      {{ls.map((l: L, i: number) => (
        <span key={{i}}>
          {{i > 0 ? " · " : ""}}
          <a href={{l[1]}} target="_blank" rel="noreferrer">{{l[0]}}</a>
        </span>
      ))}}
    </span>
  );
}}

function Source({{ text, ls }}: {{ text: string; ls?: L[] }}) {{
  const theme = useGrokTheme();
  return (
    <span>
      <span style={{{{ color: theme.text.tertiary, fontSize: theme.font.caption.fontSize, lineHeight: theme.font.caption.lineHeight }}}}>{{text}}</span>
      {{ls && ls.length > 0 ? (<span>{{" "}}{{links(ls)}}</span>) : null}}
    </span>
  );
}}

export default function App() {{
  return (
    <Page title={{{q("小时情报 · "+md)}}} summary={{{q("最要紧："+d.get("top","")+"。")}}} width="wide" lang="zh-Hans">
      <Section heading="要处理的">
        <Table
          columns={{["优先级", "事项", "来源 · 会话 · 时间", "附带链接"]}}
          rows={{{join_rows(rows_todo)}}}
        />
      </Section>
      <Section heading="客户与商单">
        <Table
          columns={{["客户", "项目", "阶段", "下一步", "来源 · 会话 · 时间"]}}
          rows={{{join_rows(rows_cl)}}}
        />
      </Section>
      <Section heading="值得知道的">
        <Table columns={{["事情", "来源"]}} rows={{{join_rows(two("know"))}}} />
      </Section>
      <Section heading="可写的选题">
        <Table columns={{["选题", "来源"]}} rows={{{join_rows(two("topics"))}}} />
      </Section>
      <Section heading="今日已解决">
        <Table columns={{["事情", "来源"]}} rows={{{join_rows(two("resolved"))}}} />
      </Section>
    </Page>
  );
}}
'''
    if any(ch in tsx for ch in '「」『』'):
        raise SystemExit('output contains CJK corner quotes; rewrite titles or session names first')
    return tsx

def main():
    p = argparse.ArgumentParser(description="Render a Cursor/Grok Page TSX from digest state JSON.")
    p.add_argument('--state', required=True, help='Path to the day state JSON')
    p.add_argument('--output', '-o', required=True, help='Write TSX here')
    args = p.parse_args()
    d = json.loads(Path(args.state).read_text(encoding='utf-8'))
    Path(args.output).write_text(render(d), encoding='utf-8')
    print('wrote', args.output)

if __name__ == '__main__':
    main()
