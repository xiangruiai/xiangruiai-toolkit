#!/usr/bin/env python3
# 从小时情报状态文件生成飞书互动卡片（Card 2.0）。
# 用法：python3 gen_card.py --state YYYY-MM-DD.json --output daily-YYYY-MM-DD.json
# 可选：--aliases client_aliases.json --project-shortcuts shortcuts.json --open-label 打开日节点
# Cursor Page 的表格样式见 references/page-style.md，不要把本文件的 200 元素回退逻辑套到 Page 上。
# 本文件只生成卡片 JSON。发送时用机器人身份，且只发给当前登录用户本人，不发群、不代用户发：
#   OID=$(lark-cli auth status | python3 -c "import json,sys; print(json.load(sys.stdin)['identities']['user']['openId'])")
#   lark-cli im +messages-send --as bot --user-id "$OID" --msg-type interactive --content @daily-YYYY-MM-DD.json
# 飞书 Card 2.0 的 table 只能放在卡片根 body.elements，不能放进 collapsible_panel。
# 因此客户与商单在折叠面板里用 column_set 做伪表格。
import argparse, json, time, re, sys
from collections import OrderedDict
from pathlib import Path

def parse_args():
    p = argparse.ArgumentParser(description="Generate a Feishu interactive card from an hourly digest state file.")
    p.add_argument("--state", required=True, help="Path to the day state JSON")
    p.add_argument("--output", "-o", help="Output card JSON path (default: daily-<date>.json in cwd)")
    p.add_argument("--aliases", help="Optional client alias JSON (see examples/client_aliases.example.json)")
    p.add_argument("--project-shortcuts", help="Optional JSON object {substring: short_label}")
    p.add_argument("--open-label", default="打开日节点", help="Footer button label when a day-node URL exists")
    p.add_argument("--open-url", help="Override footer button URL (default: feishu_day_node.url or page_url)")
    return p.parse_args()

ARGS = parse_args()
SRC = Path(ARGS.state)
D = json.load(open(SRC, encoding="utf-8"))
# 发卡前去掉已解决的待办，避免它们再出现在要处理的区块里。
D["todo"] = [t for t in (D.get("todo") or []) if t.get("status") != "已解决"]
for key in ("know", "topics", "resolved", "clients"):
    D.setdefault(key, [])
ALIAS_PATH = Path(ARGS.aliases) if ARGS.aliases else None
PROJECT_SHORTCUTS = []
if ARGS.project_shortcuts:
    raw = json.load(open(ARGS.project_shortcuts, encoding="utf-8"))
    if isinstance(raw, dict):
        PROJECT_SHORTCUTS = list(raw.items())
node = D.get("feishu_day_node") or {}
OPEN_URL = ARGS.open_url or node.get("url") or D.get("page_url") or ""
OPEN_LABEL = ARGS.open_label
OUT = Path(ARGS.output) if ARGS.output else Path("daily-%s.json" % D["date"])

IC={"文档":("file-link-docx_outlined","blue"),"腾讯文档":("file-link-docx_outlined","blue"),"文章":("chat-news_outlined","green"),
    "报名表":("bitableform_outlined","orange"),"报名页":("bitableform_outlined","orange"),"飞书表格":("file-link-sheet_outlined","purple"),"产品页":("web-card_outlined","grey")}
pc={"高":"red","中":"orange","低":"neutral"}
STAGE_COLOR={"执行中":"blue","等确认":"orange","等回款":"red","已完成":"green","已到账":"green","暂停":"neutral"}

def load_aliases():
    to_canon, meta={}, {}
    if ALIAS_PATH and ALIAS_PATH.exists():
        raw=json.load(open(ALIAS_PATH, encoding="utf-8"))
        for canon, info in (raw.get('clients') or {}).items():
            meta[canon]=info or {}
            to_canon[canon]=canon
            if info.get('display'):
                to_canon[info['display']]=canon
            for a in info.get('aliases') or []:
                to_canon[a]=canon
    return to_canon, meta

def canon_of(d, to_canon):
    name=(d.get('client') or d.get('canonical') or '').strip()
    sess=(d.get('session') or '').strip()
    return to_canon.get(name) or to_canon.get(sess) or name

def nxt(d):
    b=(d.get('blocker') or d.get('next') or '').strip()
    if '下一步' in b:
        b=b.split('下一步',1)[1]
        b=re.sub(r'^[是的：:，, ]+','',b)
    return b.strip('。；; ')

def short_proj(name):
    name = name or ''
    for key, short in PROJECT_SHORTCUTS:
        if key in name:
            return short
    return name

def expand_projects(row):
    if row.get('projects'):
        out=[]
        for p in row['projects']:
            q=dict(p)
            q.setdefault('client', row.get('client',''))
            q.setdefault('contact', row.get('contact',''))
            out.append(q)
        return out
    return [row]

def merge_clients(items):
    to_canon, meta=load_aliases()
    groups=OrderedDict()
    for d in items:
        groups.setdefault(canon_of(d, to_canon), []).append(d)
    out=[]
    for key, rows in groups.items():
        info=meta.get(key) or {}
        display=info.get('display') or key
        contact=info.get('contact') or next((r.get('contact') for r in rows if r.get('contact')), '') or ''
        projs, seen=[], set()
        for r in rows:
            for p in expand_projects(r):
                sig=(p.get('project',''), p.get('session',''), p.get('time',''), p.get('stage',''))
                if sig in seen: continue
                seen.add(sig)
                projs.append(p)
        out.append({'client': display, 'canonical': key, 'contact': contact, 'projects': projs})
    return out

CL=merge_clients(D.get('clients') or [])

def md(c,size=None,**kw):
    e={"tag":"markdown","content":c,**kw}
    if size: e["text_size"]=size
    return e
def btn(l):
    k,txt=l['label'].split("：",1); txt=re.sub(r'（[^）]*）','',txt).strip(); t,col=IC.get(k,("link-copy_outlined","grey"))
    return {"tag":"button","text":{"tag":"plain_text","content":txt},"type":"primary_text","size":"tiny","icon":{"tag":"standard_icon","token":t,"color":col},"behaviors":[{"type":"open_url","default_url":l['url']}]}
def link_label(l):
    txt=l.get('label') or ''
    if '：' in txt: txt=txt.split('：',1)[1]
    return re.sub(r'（[^）]*）','',txt).strip() or '链接'
def inline_links(links):
    return ' '.join(f"[{link_label(l)}]({l['url']})" for l in links if l.get('url'))
def split_links(d, max_btns):
    links=[l for l in (d.get('links') or []) if l.get('url')]
    if max_btns is None or max_btns>=len(links):
        return links, []
    return links[:max_btns], links[max_btns:]
def btnrow(buttons):
    if not buttons: return []
    # 每个按钮一个 auto 列，横排在一行；间距尽量小
    return [{"tag":"column_set","flex_mode":"none","horizontal_spacing":"4px","margin":"0px","columns":[
        {"tag":"column","width":"auto","padding":"0px","vertical_align":"top","elements":[btn(l)]} for l in buttons
    ]}]
def channel_of(d):
    s=(d.get('source') or '微信').strip()
    return '飞书' if s in ('飞书','lark','feishu','Feishu') else '微信'
def meta(d):
    parts=[channel_of(d)]+[x for x in [short_session(d.get('session') or ''), (d.get('time') or '').strip()] if x]
    return f" <font color='grey'>{' · '.join(parts)}</font>"
def item_title(d):
    # 优先用短句 title；没有则用原文 text。不做省略号截断。
    return (d.get('title') or d.get('text') or '').strip()
def source_line(d):
    # 第二行：灰色小字来源（微信/飞书 · 会话 · 时间），后面跟蓝色短链接，用 · 分隔。
    parts=[channel_of(d)]+[x for x in [short_session(d.get('session') or ''), (d.get('time') or '').strip()] if x]
    line=f"<font color='grey'>{' · '.join(parts)}</font>" if parts else ''
    links=' · '.join(f"[{link_label(l)}]({l['url']})" for l in (d.get('links') or []) if l.get('url'))
    if links:
        line=(line+' '+links).strip() if line else links
    return line
def item_md(d, with_priority=False):
    # 同一段 markdown 里两行：第一行标签+加粗短句，第二行灰色来源和蓝字链接。
    # 不拆成两个元素，以免超过 200。用 \n 换行，不用 br。
    title=item_title(d)
    head=f"**{title}**"
    if with_priority and d.get('priority'):
        head=f"<text_tag color='{pc[d['priority']]}'>{d['priority']}</text_tag> {head}"
    second=source_line(d)
    return head+('\n'+second if second else '')
def item_line(d, extra):
    line=(d.get('text') or '')+meta(d)
    if extra: line+=' '+inline_links(extra)
    return line
def todo_columns(elems, margin="0px", header=False, three=True):
    # 与客户与商单同款：灰底表头、白底、行间细线、垂直居中。优先级 1 : 事情 4 : 来源 3。
    widths=(("weighted",1),("weighted",4),("weighted",3)) if three else (("weighted",5),("weighted",3))
    cols=[{"tag":"column","width":w,"weight":wt,"vertical_align":"center","padding":"4px 0","elements":[el]} for (w,wt),el in zip(widths,elems)]
    return {"tag":"column_set","flex_mode":"none","horizontal_spacing":"8px","margin":margin,
            "background_style":"grey" if header else "default","columns":cols}
def todo_table(items, three=True):
    if not items:
        return [md("今天没有条目。","notation")]
    def h(t): return md(f"<font color='grey'>{t}</font>","notation")
    rows=[todo_columns([h("优先级"),h("事情"),h("来源")] if three else [h("事情"),h("来源")], header=True, three=three)]
    for i,d in enumerate(items):
        if i: rows.append(thin_hr())
        pr=d.get('priority') or ''
        tag=f"<text_tag color='{pc.get(pr,'neutral')}'>{pr}</text_tag>" if pr else ''
        title=item_title(d)
        src=source_md(d.get('session') or '', d.get('time') or '', d.get('links'), d.get('source'))
        if three:
            cells=[md(tag), md(title,"normal"), src]
        else:
            cells=[md((tag+' ' if tag else '')+title,"normal"), src]
        rows.append(todo_columns(cells, three=three))
    return rows
def todo_block(items, mode="lines", max_btns=0):
    if mode in ("table3","table2"):
        return todo_table(items, mode=="table3")
    if not items:
        return [md("今天没有条目。","notation")]
    lines=[item_md(d, True) for d in items]
    if mode=="one":
        return [md("\n\n".join(lines),"normal")]
    out=[]
    for i,line in enumerate(lines):
        out.append(md(line,"normal",margin="0px" if i==0 else "8px 0 0 0"))
    return out
def know_item(d, max_btns=None):
    buttons, extra=split_links(d, max_btns)
    return [md(item_line(d, extra),"notation",margin="4px 0 0 0")]+btnrow(buttons)
def md_cell(s):
    return (s or '').replace('|', '&#124;').replace('\n', ' ')
def know_link_text(links):
    parts=[]
    for l in links or []:
        if l.get('url'):
            parts.append(f"[{link_label(l)}]({l['url']})")
    return '、'.join(parts)

# 来源列：一行灰色小字“微信/飞书 · 会话 · 时间”，颜色只用飞书已生效的 <font color='grey'>，字号 notation。
# 会话名若带【】前缀，去掉方括号写成“前缀 · 其余”，不改用词。值得知道的蓝色链接仍在下一行。
def short_session(session):
    s=(session or '').strip()
    m=re.match(r'^【([^】]+)】(.*)$', s)
    if m:
        prefix, rest=m.group(1).strip(), m.group(2).strip()
        return f"{prefix} · {rest}" if rest else prefix
    return s

def source_md(session='', time='', links=None, source='微信'):
    # 来源列一行灰色小字：微信/飞书 · 会话 · 时间。优先纯文字，不加额外标签，以免超过 200 元素。
    ch='飞书' if (source or '').strip() in ('飞书','lark','feishu','Feishu') else '微信'
    parts=[ch]+[x for x in [short_session(session), (time or '').strip()] if x]
    lines=[]
    if parts:
        lines.append(f"<font color='grey'>{' · '.join(parts)}</font>")
    link_text=know_link_text(links) if links else ''
    if link_text:
        lines.append(link_text)
    return md('\n'.join(lines),"notation") if lines else md("","notation")

def know_columns(elems, margin="0px", header=False, pad="4px 0"):
    # 与客户表同款：灰底表头、白底面板、列垂直居中、无竖线。来源栏加宽（事情 5 : 来源 4），避免长会话名折行。
    widths=(("weighted",5),("weighted",4))
    cols=[]
    for (w,wt), el in zip(widths, elems):
        c={"tag":"column","width":w,"weight":wt,"vertical_align":"center","padding":pad,"elements":[el]}
        cols.append(c)
    return {"tag":"column_set","flex_mode":"none","horizontal_spacing":"8px","margin":margin,
            "background_style":"grey" if header else "default","columns":cols}

def know_header(first="事情"):
    def h(s): return md(f"<font color='grey'>{s}</font>","notation")
    return know_columns([h(first), h("来源")], margin="0px", header=True)

def know_row(d, margin="0px"):
    # 每行一个 column_set，每栏只放一个 markdown；来源和蓝色短链接合并在同一个 markdown。
    return know_columns([
        md(item_title(d),"normal"),
        source_md(d.get('session') or '', d.get('time') or '', d.get('links'), d.get('source')),
    ], margin=margin)

def know_section(items, max_btns=None, with_hr=True, first="事情"):
    # 值得知道的 / 可写的选题 / 今日已解决 共用：两栏细线表（事情或选题、来源），白底、灰底表头、行间 hr。
    if not items:
        return [md("今天没有条目。","notation")]
    rows=[know_header(first)]
    for i,d in enumerate(items):
        if i and with_hr:
            rows.append(thin_hr())
        rows.append(know_row(d, margin="0px"))
    return rows

def md_table_cell(s):
    # markdown 表格单元格：不能换行、不能有竖线字符；不截断。
    return (s or '').replace('|','&#124;').replace('\n',' ').strip()

def md_table_section(items, first="事情"):
    # 降级用（元素超 200 时）：整块只用 1 个 markdown 组件，里面是 markdown 表格语法，两栏 事情/选题、来源。
    # 每块单张 markdown 表格。飞书文档：除标题行外最多展示 5 行，超出分页展示（带翻页控件，不截断），每页行数不支持自定义。
    # 来源栏：浅灰小字 微信/飞书 · 会话 · 时间，蓝色短链接跟在后面，用 · 分隔。
    if not items:
        return [md("今天没有条目。","notation")]
    rows=[]
    for d in items:
        parts=[channel_of(d)]+[x for x in [short_session(d.get('session') or ''), (d.get('time') or '').strip()] if x]
        src=f"<font color='grey'>{' · '.join(parts)}</font>"
        links=' · '.join(f"[{link_label(l)}]({l['url']})" for l in (d.get('links') or []) if l.get('url'))
        if links: src+=' '+links
        rows.append(f"| {md_table_cell(item_title(d))} | {md_table_cell(src)} |")
    # 每块只出一张表、一个表头，不切分。超过 5 行由飞书自带分页（右下角 1/2 和上下翻页按钮）。
    table="\n".join([f"| {first} | 来源 |","| :--- | :--- |"]+rows)
    return [md(table,"notation")]

def small_with_links(L):
    # 与要处理的同款两行：短句加粗，下一行灰色来源和蓝字链接。合并成一个 markdown 以控制元素数。
    if not L:
        return [md("今天没有条目。","notation")]
    return [md("\n\n".join(item_md(d, False) for d in L),"normal")]
def panel(name,n,expanded,color,elements,vs,bg=None):
    e={"tag":"collapsible_panel","expanded":expanded,
      "header":{"title":{"tag":"markdown","content":f"**{name}**（{n}）"},"icon":{"tag":"standard_icon","token":"down-small-ccm_outlined","color":color},"icon_position":"right","icon_expanded_angle":-180},
      "border":{"color":"grey","corner_radius":"6px"},"vertical_spacing":vs,"elements":elements}
    if bg:
        e["background_color"]=bg
    return e
def small(L):
    if not L:
        return [md("今天没有条目。","notation")]
    return [md("\n\n".join(item_md(d, False) for d in L),"normal")]
def num(v,l,c):
    return {"tag":"column","width":"weighted","weight":1,"padding":"8px 4px","vertical_align":"center","elements":[md(f"<font color='{c}'>**{v}**</font>","heading",text_align="center",margin="0px"),md(f"<font color='grey'>{l}</font>","notation",text_align="center",margin="0px")]}

def client_cell(name, contact):
    s=f"**{name}**"
    if contact:
        s+=f"\n<font color='grey'>{contact}</font>"
    return md(s,"normal")

def next_cell(text):
    return md(text or '',"normal")

def source_cell(d):
    return source_md(d.get('session') or '', d.get('time') or '', source=d.get('source'))

# 表头和数据行必须同一套列宽。四列权重 客户 2 : 阶段 1 : 下一步 3 : 来源 3，全部垂直居中。
CLIENT_HS="8px"
def client_columns(elems, margin="0px", header=False):
    widths=(("weighted",2),("weighted",1),("weighted",3),("weighted",3))
    cols=[]
    for (w,wt), el in zip(widths, elems):
        c={"tag":"column","width":w,"weight":wt,"vertical_align":"center","padding":"4px 0","elements":[el]}
        cols.append(c)
    return {"tag":"column_set","flex_mode":"none","horizontal_spacing":CLIENT_HS,"margin":margin,
            "background_style":"grey" if header else "default","columns":cols}

def thin_hr():
    # hr 没有颜色字段，用很小的上下边距做出细浅的行线
    return {"tag":"hr","margin":"2px 0"}

def client_row(name, contact, stage, step, src):
    return client_columns([
        client_cell(name, contact),
        md(f"<text_tag color='{STAGE_COLOR.get(stage,'neutral')}'>{stage}</text_tag>") if stage else md(""),
        next_cell(step),
        source_cell(src),
    ], margin="0px")

def client_header():
    def h(t): return md(f"<font color='grey'>{t}</font>","notation")
    return client_columns([h("客户"), h("阶段"), h("下一步"), h("来源")], margin="0px", header=True)
def count_tags(o):
    n=0
    if isinstance(o, dict):
        if 'tag' in o: n+=1
        n+=sum(count_tags(v) for v in o.values())
    elif isinstance(o, list):
        n+=sum(count_tags(v) for v in o)
    return n

def client_block(groups):
    if not groups:
        return [md("今天没有进行中的客户或商单。","notation")]
    # 灰底表头、彩色阶段标签、行间细线。表头下面不加横线；四栏垂直居中。
    rows=[client_header()]
    first=True
    for g in groups:
        projs=g.get('projects') or [g]
        multi=len(projs)>1
        for p in projs:
            step=nxt(p)
            label=short_proj(p.get('project',''))
            if multi and label and label not in (step or ''):
                step=f"{step}（{label}）" if step else label
            if not first:
                rows.append(thin_hr())
            first=False
            rows.append(client_row(g['client'], g.get('contact') or '', p.get('stage') or '', step, p))
    return rows

def build_card(todo_mode="lines", max_btns=0, know_hr=True, know_list=False, mdt=False):
    T=f"小时情报 · {D['date'][5:]} "+time.strftime('%H:%M')
    elements=[
      {"tag":"column_set","background_style":"red-50","columns":[{"tag":"column","padding":"10px","elements":[md(f"🔥 **最要紧：{D['top']}**")]}]},
      {"tag":"column_set","flex_mode":"none","background_style":"grey","horizontal_spacing":"0px","columns":[
          num(len(D['todo']),"要处理","red"),num(len(D['know']),"值得知道","blue"),
          num(len(D['topics']),"选题","green"),num(len(CL),"客户","orange")]},
      panel("要处理的",len(D['todo']),True,"red",todo_block(D['todo'], todo_mode, max_btns),"2px"),
      panel("客户与商单",len(CL),True,"orange",client_block(CL),"0px"),
      panel("值得知道的",len(D['know']),False,"blue",small_with_links(D['know']) if know_list else (md_table_section(D['know']) if mdt else know_section(D['know'], None, know_hr)),"2px" if know_list or mdt else "0px"),
      panel("可写的选题",len(D['topics']),False,"green",md_table_section(D['topics'],"选题") if mdt else know_section(D['topics'], None, True, "选题"),"2px" if mdt else "0px"),
      panel("今日已解决",len(D['resolved']),False,"grey",md_table_section(D['resolved'],"事情") if mdt else know_section(D['resolved'], None, True, "事情"),"2px" if mdt else "0px"),
    ]
    if OPEN_URL:
        elements.append({"tag":"button","text":{"tag":"plain_text","content":OPEN_LABEL},"type":"primary","width":"fill","behaviors":[{"type":"open_url","default_url":OPEN_URL}]})
    return T, {"schema":"2.0","config":{"update_multi":True},
     "header":{"title":{"tag":"plain_text","content":T},"template":"indigo"},
     "body":{"elements":elements}}

# 单卡最多 200 个 tag（column、hr、plain_text、icon 都算）。
# 值得知道的、可写的选题、今日已解决 也都是两栏细线表（事情/选题、来源），
# 与要处理的、客户与商单同款：白底、灰底表头、行间 hr、垂直居中、无竖线外框；每行 = 1 column_set + 2 column + 2 markdown。
# 飞书 table 组件不能放进 collapsible_panel，markdown 表格有竖线外框且 5 行分页，所以都不用。
# 飞书 table 组件不能放进 collapsible_panel，所以不用。
# 超 200 时的降级顺序（始终是表格、不删内容、保留全部链接）：
#   1 三块改用 markdown 表格语法，每块单张表（只占 1 个元素），超过 5 行用飞书自带翻页；有竖线和外框，列宽不能设。推荐默认用这版；
#   2 仍超限才把要处理的退到两栏表；3 最后才退到两行列表。
todo_mode="table3"; know_mode="table"
plans=[("table3",False,False),("table3",False,True),("table2",False,True),("lines",False,True)]
for tm,kl,mt in plans:
    T,C=build_card(tm, 0, True, kl, mt); n_tags=count_tags(C); todo_mode=tm; know_mode="mdtable" if mt else "table"
    if n_tags<=200: break
link_mode="inline-links"
if n_tags>200:
    raise SystemExit('card still has %d tags, Feishu limit is 200'%n_tags)
s=json.dumps(C,ensure_ascii=False,indent=1)
assert not any(x in s for x in "「」『』")
assert '"tag": "table"' not in s
# 表格单元格曾把 <br> 显示成字面字符；面板里的 markdown 用 \n 换行，不要出现 br 字样。
assert '<br' not in s.lower()
OUT.write_text(s, encoding='utf-8')
print(T)
print('wrote', OUT)
print('clients', len(CL))
print('tags', n_tags, 'todo', todo_mode, 'links', link_mode, 'three_blocks', know_mode)
