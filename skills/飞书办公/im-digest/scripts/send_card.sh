#!/usr/bin/env bash
# 用机器人身份把卡片只发给当前 lark-cli 登录的用户本人。不要改成群或他人。
# 用法：bash send_card.sh daily-2026-11-24.json
set -euo pipefail
L="${LARK_CLI:-lark-cli}"
CARD="${1:?usage: send_card.sh <card.json>}"
OID="$("$L" auth status | python3 -c "import json,sys; print(json.load(sys.stdin)['identities']['user']['openId'])")"
"$L" im +messages-send --as bot --user-id "$OID" --msg-type interactive --content @"$CARD"
echo "sent card to current user only"
