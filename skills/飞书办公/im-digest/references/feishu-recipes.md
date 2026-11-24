# 飞书侧采集与同步（lark-cli）

使用飞书官方 CLI。安装与登录见 [larksuite/cli](https://github.com/larksuite/cli) 和 npm 包 [@larksuite/cli](https://www.npmjs.com/package/@larksuite/cli)。

快速安装：`npx @larksuite/cli@latest install`，然后 `lark-cli config init`、`lark-cli auth login --recommend`，用 `lark-cli auth status` 或 `lark-cli doctor` 确认。本机若有 HTTPS 代理导致异常，命令前加 `LARK_CLI_NO_PROXY=1`。

时间参数一律带时区，例如 `2026-11-24T13:00:00+08:00`。S 为上次盘点或当天 00:00，E 为现在。

## 只读采集（全部 `--as user`）

可用 `scripts/scan_feishu.sh`，或按需单独跑：

```bash
# 会话列表（含私聊，按最近活跃）
lark-cli im +chat-list --as user --types p2p,group --sort active_time --page-size 100 --page-all --page-limit 3

# @我和 @所有人（一次跨所有群，最有用）
lark-cli im +messages-search --as user --is-at-me --start "$S" --end "$E" --page-size 50 --page-all --no-reactions

# 所有私聊（跨会话）。私聊结果里 chat_name 可能为空，要用 chat-list 的 chat_id 对照名字
lark-cli im +messages-search --as user --chat-type p2p --start "$S" --end "$E" --page-size 50 --page-all --no-reactions

# 窗口内群消息。若 has_more=true，把 --end 设成第一段最早时间再补拉
lark-cli im +messages-search --as user --chat-type group --start "$S" --end "$E" --page-size 50 --page-all --page-limit 4 --no-reactions

# 别人提到你的名字但没 @
lark-cli im +messages-search --as user --query "$MY_NAME" --start "$S" --end "$E" --page-size 50 --no-reactions

# 本人发出的话（找答应过的事：稍后、我发你、我来）
lark-cli im +messages-search --as user --sender "$MY_OPEN_ID" --start "$S" --end "$E" --page-size 50 --page-all --no-reactions

# 重点会话完整记录（search 有时会漏）
lark-cli im +chat-messages-list --as user --chat-id "$CHAT_ID" --start "$S" --order asc --no-reactions --page-all --page-limit 4

# 邮件。验证码、兑换码、卡号不要写入状态或卡片
lark-cli mail +triage --as user --folder INBOX --max 60 --format table
# 看正文：mail +message --as user --message-id <id>

# 日历（含待回复邀请）。只读，不要用 +rsvp
lark-cli calendar +agenda --as user --start "$TODAY_START" --end "$PLUS_7D"

# 任务
lark-cli task +get-my-tasks --as user --complete=false --page-all
lark-cli task +get-related-tasks --as user

# 审批：topic 1 待办，17 未读抄送
lark-cli approval tasks query --as user --params '{"topic":"1","page_size":50}'

# 近 3 天打开或新建的文档。标题在 results[].title_highlighted，链接在 result_meta
lark-cli drive +search --as user --opened-since 3d --sort open_time --page-size 20
lark-cli drive +search --as user --created-since 3d --sort create_time --page-size 20

# 合作文档评论
lark-cli drive +list-comments --as user --url "$DOC_URL" --solved-status all

# 读文档正文
lark-cli docs +fetch --as user --doc "$DOC" --doc-format markdown

# 会议不一定在日历里。可用妙记搜索（若已授权）
lark-cli minutes +search --as user --start "$TODAY" --query "$KEYWORD"
```

`im +messages-search` 依赖搜索索引，刚发出的消息可能漏掉，重点会话要用 `+chat-messages-list` 补。群里发的日程卡片（`msg_type` 为 `general_calendar`）不一定出现在自己的日历里，要单独记。实时会议若未授权 `vc:meeting.realtime:read`，会后纪要用文档或妙记接口读；无权限的纪要只挂链接，不编造正文。任务接口在没有任务时 `data.items` 可能为 `null`，不要直接遍历。私聊里的 `chat_partner` 可能是对象，抽字段前先转成文本。

可跳过的会话类型建议写在配置里：邮箱助手、账号安全中心、各类官方机器人、自己发给自己的链接会话。账号安全或授权通知建议并成一条待确认，不要展开设备或令牌细节。

## 发给自己的卡片（唯一默认写操作之一）

```bash
python3 scripts/gen_card.py --state data/YYYY-MM-DD.json -o daily-YYYY-MM-DD.json
bash scripts/send_card.sh daily-YYYY-MM-DD.json
```

`send_card.sh` 从 `lark-cli auth status` 取出当前用户的 openId，用 `--as bot` 把互动卡片只发给本人。不要发给其他人或群。不要在盘点里用 `+reply`、`+messages-send` 代用户发言。

飞书单卡最多 200 个 tag（`column`、`hr`、`plain_text`、`icon` 都算）。生成脚本会按这个顺序降级，且不删内容、不丢链接：

1. 五块都用细线伪表格（推荐）
2. 值得知道的 / 选题 / 已解决改为单张 markdown 表格（超 5 行由飞书自带翻页，会有竖线和外框）
3. 要处理的退到两栏
4. 最后才退到两行列表

不要把官方 `table` 组件放进折叠面板。单元格里用换行，不要写 `br`。

## 同步知识库日节点（可选，`--as user`）

只更新用户自己知识空间里、专门用来归档小时情报的节点。不要改别人的文档。

```bash
# 查当月子节点，避免重复建
lark-cli wiki +node-list --as user --space-id "$SPACE" --parent-node-token "$MONTH_NODE"

# 当天还没有节点时创建
python3 scripts/mkday_md.py --state data/YYYY-MM-DD.json -o /tmp/day.md
lark-cli docs +create --as user --parent-token "$MONTH_NODE" --title "YYYY-MM-DD 小时情报" --doc-format markdown --content @/tmp/day.md

# 已有节点时整页覆盖，再给优先级打彩色标签
lark-cli docs +update --as user --doc "$OBJ" --command overwrite --doc-format markdown --content @/tmp/day.md
lark-cli docs +update --as user --doc "$OBJ" --command str_replace --pattern "[高] " \
  --content '<span text-color="red" background-color="light-red"><b> 高 </b></span> '
lark-cli docs +update --as user --doc "$OBJ" --command str_replace --pattern "[中] " \
  --content '<span text-color="orange" background-color="light-orange"><b> 中 </b></span> '
lark-cli docs +update --as user --doc "$OBJ" --command str_replace --pattern "[低] " \
  --content '<span text-color="gray" background-color="light-gray"><b> 低 </b></span> '
```

某一级当天没有条目时，对应的 `str_replace` 可能返回 failed，属正常。多行内容先写临时文件再用 `@文件` 传入。每月 1 日若还没有月节点，先在父节点下建 `YYYY-MM`。把月份和 `node_token` 的对照放在本地 `months.tsv`，不要提交真实 token。
