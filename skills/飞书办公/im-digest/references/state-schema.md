# 状态文件字段

每天一份 JSON，建议路径：`{state_dir}/{YYYY-MM-DD}.json`。它是当天盘点的唯一事实来源，Page、飞书卡片和日节点都从这里生成。不要把原始聊天全文写进状态文件，只保留短句标题、来源和必要链接。

## 顶层字段

| 字段 | 说明 |
|---|---|
| `date` | `YYYY-MM-DD` |
| `top` | 最要紧的一句话，出现在 Page 摘要和卡片顶部 |
| `todo` | 要处理的列表 |
| `clients` | 客户与商单，一条客户（可含多个项目） |
| `know` | 值得知道的 |
| `topics` | 可写的选题 |
| `resolved` | 今日已解决 |
| `withdrawn` | 已撤下、不再追踪的条目（可选，默认不渲染） |
| `todo_parked` | 暂收起的欠回复，不要标成已解决 |
| `todo_rule` | 本次采用的条目规则（可选，便于回顾） |
| `page_url` | 当天 Page 链接（可选） |
| `feishu_day_node` | `title` / `node_token` / `obj_token` / `parent_node_token` / `url` |
| `last_scan_until` | `{wechat, feishu, sns}`，格式 `YYYY-MM-DD HH:MM`，下一轮的起点 |
| `coverage` / `coverage_log` | 本轮时间窗和扫描规模，便于补扫 |
| `skipped` | 明确跳过的源或会话及原因 |
| `last_run` | 本轮完成时间 |
| `pending_checks` | 还需人工确认的事项（不要写验证码或密钥） |

## 条目常用字段

待办、新闻、选题、已解决大致共用：

- `title`：对外短句（优先）；没有时回退 `text`
- `source`：`微信` / `飞书` / `微信+飞书`
- `session`：会话名。若显示名带【】前缀，写入前改成 `前缀 · 其余`，否则来源栏会错位
- `time`：`MM-DD HH:MM` 或时间范围
- `date`：首次进入状态文件的日期
- `links[]`：`label`（写成 `类型：文案`，如 `文档：议程`）、`kind`、`url`
- `new` / `changed` / `carried`：本轮新增、有变化、或从上轮结转，便于去重和 quiet 判断
- 待办另有：`priority`（高 / 中 / 低）、`status`、`deadline`、`calendar`
- 客户另有：`client`、`project`、`stage`、`blocker`（或 `next`）、`contact`、`amount`
- 已解决另有：`resolved_at`，`status` 为 `已解决`
- 收起另有：`parked`、`parked_at`、`parked_reason`

生成卡片前，脚本会自动忽略 `status=已解决` 的待办。链接文案不要带括号说明；全文不要使用直角引号。

阶段标签常见值：`执行中`、`交付`、`等确认`、`等回款`、`询价`、`已完成`、`已到账`、`暂停`。可按自己的业务改，但要同步卡片颜色映射。
