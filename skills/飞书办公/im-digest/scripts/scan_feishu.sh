#!/usr/bin/env bash
# 按时间窗只读采集飞书消息、邮件、日历、任务、审批、文档痕迹。
# 全部使用 --as user。不发送消息，不回复日程，不改他人文档。
#
# 用法：
#   export LARK_CLI=lark-cli
#   export FS_SINCE='2026-11-24T13:00:00+08:00'
#   export FS_END='2026-11-24T18:00:00+08:00'
#   export FS_MY_NAME='你的姓名'          # 用于搜被提到但没 @ 的消息
#   export FS_MY_OPEN_ID='ou_xxx'        # 可选，用于搜本人发出的承诺
#   export FS_OUT=./raw/feishu-1800
#   bash scan_feishu.sh
set -euo pipefail

L="${LARK_CLI:-lark-cli}"
OUT="${FS_OUT:?set FS_OUT to an output directory}"
S="${FS_SINCE:?set FS_SINCE like 2026-11-24T13:00:00+08:00}"
E="${FS_END:?set FS_END like 2026-11-24T18:00:00+08:00}"
NAME="${FS_MY_NAME:-}"
ME="${FS_MY_OPEN_ID:-}"
CAL_END="${FS_CAL_END:-}"

mkdir -p "$OUT"
echo "start $S .. $E" > "$OUT/_start.txt"

# 若本机有 HTTPS 代理导致 CLI 异常，可先 export LARK_CLI_NO_PROXY=1
as_user() { "$L" "$@" --as user; }

as_user im +chat-list --types p2p,group --sort active_time --page-size 100 --page-all --page-limit 3 \
  > "$OUT/chat-list.json" 2> "$OUT/chat-list.err" || true

as_user im +messages-search --is-at-me --start "$S" --end "$E" --page-size 50 --page-all --no-reactions \
  > "$OUT/at-me.json" 2> "$OUT/at-me.err" || true

as_user im +messages-search --chat-type p2p --start "$S" --end "$E" --page-size 50 --page-all --no-reactions \
  > "$OUT/p2p.json" 2> "$OUT/p2p.err" || true

# 群消息窗口可能被活跃大群刷满 has_more；若为 true，按第一段最早时间再设 --end 补拉
as_user im +messages-search --chat-type group --start "$S" --end "$E" --page-size 50 --page-all --page-limit 4 --no-reactions \
  > "$OUT/group.json" 2> "$OUT/group.err" || true

if [[ -n "$NAME" ]]; then
  as_user im +messages-search --query "$NAME" --start "$S" --end "$E" --page-size 50 --no-reactions \
    > "$OUT/mention-name.json" 2> "$OUT/mention-name.err" || true
fi

if [[ -n "$ME" ]]; then
  as_user im +messages-search --sender "$ME" --start "$S" --end "$E" --page-size 50 --page-all --no-reactions \
    > "$OUT/self.json" 2> "$OUT/self.err" || true
fi

as_user mail +triage --folder INBOX --max 60 --format table \
  > "$OUT/mail.txt" 2> "$OUT/mail.err" || true

# 日历默认看到未来 7 天（含待回复邀请）
if [[ -z "$CAL_END" ]]; then
  CAL_END="$E"
fi
as_user calendar +agenda --start "$S" --end "$CAL_END" \
  > "$OUT/calendar.json" 2> "$OUT/calendar.err" || true

as_user task +get-my-tasks --complete=false --page-all \
  > "$OUT/tasks.json" 2> "$OUT/tasks.err" || true
as_user task +get-related-tasks \
  > "$OUT/tasks-related.json" 2> "$OUT/tasks-related.err" || true

as_user approval tasks query --params '{"topic":"1","page_size":50}' \
  > "$OUT/approval.json" 2> "$OUT/approval.err" || true

as_user drive +search --opened-since 3d --sort open_time --page-size 20 \
  > "$OUT/drive-opened.json" 2> "$OUT/drive-opened.err" || true
as_user drive +search --created-since 3d --sort create_time --page-size 20 \
  > "$OUT/drive-created.json" 2> "$OUT/drive-created.err" || true

# 重点会话可在配置里列出 chat_id，按行放在 FS_KEY_CHATS 文件中，每行一个 oc_...
if [[ -n "${FS_KEY_CHATS:-}" && -f "${FS_KEY_CHATS}" ]]; then
  mkdir -p "$OUT/key-chats"
  while IFS= read -r cid; do
    [[ -z "$cid" || "$cid" == \#* ]] && continue
    as_user im +chat-messages-list --chat-id "$cid" --start "$S" --order asc --no-reactions --page-all --page-limit 4 \
      > "$OUT/key-chats/${cid}.json" 2> "$OUT/key-chats/${cid}.err" || true
  done < "$FS_KEY_CHATS"
fi

echo "done" > "$OUT/_done.txt"
echo "wrote $OUT"
