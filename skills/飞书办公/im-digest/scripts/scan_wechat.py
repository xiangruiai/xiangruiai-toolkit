#!/usr/bin/env python3
"""在已登录微信桌面版的那台机器上，按时间窗扫描会话并写出可读摘要。

依赖本机已安装的 vchat CLI（本工具箱 cli/vchat，建议 2.1.0+）。只读本地已解密数据库，不发送消息。

用法：
  export TZ=Asia/Shanghai
  python3 scan_wechat.py --since "2026-11-24 13:00" -o wd_1124_1800.txt

环境变量备选：WD_SINCE、WD_OUT、VCHAT（vchat 可执行文件路径）。
"""
import argparse, json, os, re, subprocess, sys
from datetime import datetime
from pathlib import Path

def parse_args():
    p = argparse.ArgumentParser(description="Scan WeChat sessions in a time window via vchat.")
    p.add_argument('--since', default=os.environ.get('WD_SINCE'), help='Start time YYYY-MM-DD HH:MM')
    p.add_argument('--output', '-o', default=os.environ.get('WD_OUT'), help='Output text path')
    p.add_argument('--ls-n', type=int, default=400, help='How many recent sessions to list (default 400)')
    p.add_argument('--history-n', type=int, default=800, help='Max messages per session (default 800)')
    p.add_argument('--vchat', default=os.environ.get('VCHAT', 'vchat'), help='vchat executable')
    p.add_argument('--tz', default=os.environ.get('TZ', 'Asia/Shanghai'), help='Timezone for parsing and display')
    return p.parse_args()

def run(args, env, timeout=180):
    r = subprocess.run(args, capture_output=True, text=True, env=env, timeout=timeout)
    return r.returncode, r.stdout, r.stderr

def vchat_json(vchat, argv, env, timeout=180):
    code, out, err = run([vchat, '--json'] + argv, env, timeout=timeout)
    if not out.strip():
        return None, err or ('exit %s' % code)
    try:
        data = json.loads(out)
    except Exception as e:
        return None, 'json error: %s out=%s' % (e, out[:300])
    if isinstance(data, dict) and 'output_text' in data and len(data) == 1:
        try:
            return json.loads(data['output_text']), err
        except Exception:
            return data, err
    return data, err

def parse_ts(s, fallback_year):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        v = float(s)
        if v > 1e12:
            v = v / 1000.0
        try:
            return datetime.fromtimestamp(v)
        except Exception:
            return None
    s = str(s).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%m-%d %H:%M:%S', '%m-%d %H:%M'):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=fallback_year)
            return dt
        except Exception:
            pass
    if s.isdigit():
        v = int(s)
        if v > 1e12:
            v = v / 1000
        try:
            return datetime.fromtimestamp(v)
        except Exception:
            return None
    return None

def extract_card(content):
    if not content:
        return content
    t = str(content).replace('&amp;', '&')
    t = t.replace('<![CDATA[', '').replace(']]>', '')
    refs = re.findall(r'<refermsg>.*?</refermsg>', t, flags=re.S)
    ref_bits = []
    for r in refs:
        rc = re.search(r'<content>(.*?)</content>', r, flags=re.S)
        dn = re.search(r'<displayname>(.*?)</displayname>', r, flags=re.S)
        if rc:
            ref_bits.append(((dn.group(1) if dn else '') + ': ' + rc.group(1))[:200])
    title = re.search(r'<title>(.*?)</title>', t, flags=re.S)
    des = re.search(r'<des>(.*?)</des>', t, flags=re.S)
    urlm = re.search(r'<url>(.*?)</url>', t, flags=re.S)
    url_s = urlm.group(1) if urlm else ''
    if not url_s:
        um = re.search(r'https?://[^\s<>]+', t)
        url_s = um.group(0) if um else ''
        if url_s:
            url_s = url_s.rstrip(")>'")
    if title or des or url_s:
        parts = ['[卡片]']
        if title:
            parts.append(title.group(1).strip())
        if des:
            parts.append(des.group(1).strip()[:200])
        if url_s:
            parts.append(url_s.strip())
        if ref_bits:
            parts.append('引用:' + ' | '.join(ref_bits))
        return ' '.join(parts)
    if 'VoIPBubbleMsg' in t or 'voipmsg' in t.lower():
        m = re.search(r'通话时长[^<\]]+', t)
        return '[通话] ' + (m.group(0) if m else '语音/视频通话')
    if t.strip().startswith('<?xml') or t.strip().startswith('<msg'):
        m = re.search(r'<content>(.*?)</content>', t, flags=re.S)
        if m and not m.group(1).startswith('<'):
            base = m.group(1)
            if ref_bits:
                base += ' 引用:' + ' | '.join(ref_bits)
            return base[:500]
        if '<img ' in t:
            return '[图片]'
        return t[:300]
    if ref_bits:
        return t[:300] + ' 引用:' + ' | '.join(ref_bits)
    return t

def session_list(data):
    if isinstance(data, dict):
        return data.get('sessions') or data.get('data') or data.get('items') or []
    if isinstance(data, list):
        return data
    return []

def message_list(hist):
    if isinstance(hist, dict):
        return hist.get('messages') or hist.get('data') or []
    if isinstance(hist, list):
        return hist
    return []

def main():
    args = parse_args()
    if not args.since or not args.output:
        sys.exit('need --since and --output (or WD_SINCE / WD_OUT)')
    env = os.environ.copy()
    env['TZ'] = args.tz
    # 保证能找到用户安装在 ~/.local/bin 的 vchat
    env['PATH'] = os.path.expanduser('~/.local/bin') + ':' + env.get('PATH', '')

    since_dt = datetime.strptime(args.since, '%Y-%m-%d %H:%M')
    year = since_dt.year
    data, err = vchat_json(args.vchat, ['ls', str(args.ls_n)], env, timeout=120)
    sessions = session_list(data)
    if not sessions and err:
        sys.exit('vchat ls failed: %s' % err)
    fields = list(sessions[0].keys()) if sessions else []
    in_window = []
    oldest = None
    for s in sessions:
        t = s.get('last_timestamp') or s.get('last_time') or s.get('time') or s.get('last_msg_time') or s.get('update_time')
        dt = parse_ts(t, year)
        if dt is None:
            last = s.get('last_message') or {}
            if isinstance(last, dict):
                dt = parse_ts(last.get('create_time') or last.get('time') or last.get('timestamp'), year)
        if dt and (oldest is None or dt < oldest):
            oldest = dt
        if dt and dt >= since_dt:
            in_window.append((s, dt))

    lines = []
    lines.append('sessions_total=%s since=%s ls_n=%s fields=%s' % (len(sessions), args.since, args.ls_n, fields))
    lines.append('in_window=%s oldest_ls=%s' % (len(in_window), oldest.strftime('%m-%d %H:%M') if oldest else 'NA'))
    lines.append('')

    total_msgs = 0
    errors = []
    for s, dt in in_window:
        name = s.get('display_name') or s.get('nickname') or s.get('name') or s.get('remark') or ''
        username = s.get('username') or s.get('user_name') or s.get('wxid') or s.get('id') or name
        unread = s.get('unread') or s.get('unread_count') or 0
        # history 必须用 username，不要只用显示名（显示名可能和公众号撞名）
        hist, herr = vchat_json(
            args.vchat,
            ['history', str(username), '--since', args.since, '-n', str(args.history_n), '--asc'],
            env,
            timeout=180,
        )
        msgs = message_list(hist)
        if herr and not msgs:
            errors.append('%s: %s' % (username, herr[:200]))
        kept = []
        for m in msgs:
            mdt = parse_ts(m.get('create_time') or m.get('time') or m.get('timestamp'), year)
            if mdt is None or mdt >= since_dt:
                kept.append(m)
        total_msgs += len(kept)
        lines.append('### %s (%s) n=%s unread=%s last=%s' % (name, username, len(kept), unread, dt.strftime('%m-%d %H:%M')))
        if not kept:
            lines.append('(no messages in window or empty history)')
            lines.append('')
            continue
        for m in kept:
            mdt = parse_ts(m.get('create_time') or m.get('time') or m.get('timestamp'), year)
            tstr = mdt.strftime('%m-%d %H:%M') if mdt else str(m.get('create_time') or '')
            sender = m.get('sender_name') or m.get('sender') or m.get('from') or ''
            is_me = m.get('is_me') or m.get('me') or (m.get('is_sender') == 1)
            who = 'me' if (sender in ('me', '我') or is_me is True) else str(sender)
            content = m.get('content') or m.get('text') or m.get('msg') or ''
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False)
            content = str(content)
            content = re.sub(r'^[a-zA-Z0-9_@.-]+: *', '', content, count=1)
            content = extract_card(content)
            content = re.sub(r'[ \t\n\r]+', ' ', content).strip()
            if len(content) > 600:
                content = content[:600] + '...'
            typ = m.get('local_type') or m.get('type') or ''
            extra = (' type=%s' % typ) if typ and typ not in (1, '1') else ''
            lines.append('%s %s:%s %s' % (tstr, who, extra, content))
        lines.append('')

    lines.append('TOTAL_MSGS=%s IN_WINDOW_SESSIONS=%s' % (total_msgs, len(in_window)))
    if errors:
        lines.append('ERRORS:')
        lines.extend(errors)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines), encoding='utf-8')
    print('WROTE %s bytes=%s sessions=%s msgs=%s' % (out, out.stat().st_size, len(in_window), total_msgs))

if __name__ == '__main__':
    main()
