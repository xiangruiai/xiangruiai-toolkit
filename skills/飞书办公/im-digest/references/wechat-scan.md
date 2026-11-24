# 微信侧采集（vchat）

在已登录微信桌面版的那台电脑上运行。建议版本 vchat 2.1.0。vchat 在本工具箱的 `cli/vchat`，安装和免责声明见 [vchat README](../../../cli/vchat/README.md)（公开地址：https://github.com/xiangruiai/xiangruiai-toolkit/tree/main/cli/vchat）。

## 开跑前

1. 微信桌面版保持开着并已登录
2. `export TZ=Asia/Shanghai`（机器时区若不是东八区，时间窗会错位）
3. 需要增量解密时先 `vchat decrypt`，再 `vchat doctor` 确认本地库可用
4. 把 `vchat` 放到 `PATH`（常见位置 `~/.local/bin/vchat`）

## 本 skill 实际用到的命令

全局都加 `--json`。部分子命令是原生 JSON，其余可能包在 `{output_text}` 里，脚本会自动拆开。

| 目的 | 命令 | 注意 |
|---|---|---|
| 最近会话 | `vchat --json ls 400` | 顶层是 `{"sessions":[...]}`，用 `last_timestamp` 筛时间窗 |
| 某会话历史 | `vchat --json history <username> --since "YYYY-MM-DD HH:MM" -n 800 --asc` | **必须用 username**（如 `123@chatroom`），不要只用显示名，显示名可能和公众号撞名 |
| 全库搜索 | `vchat --json search "关键词"` | 不按时间排序，窗口内 @你 更宜在扫描摘要里检索 |
| 群资料 | `vchat --json group-info <群>` | 需要公告或成员背景时再用 |
| 朋友圈 | `vchat --json sns-ls -n 150` | 数字必须用 `-n`，`sns-ls 40` 会被当成 target |
| 朋友圈评论提示 | `vchat --json sns-mentions -n 50` | 通常只有评论人和时间，读不到评论正文 |
| 公众号/服务通知 | `vchat --json biz-ls -n 30` | 支付提醒可能出现完全相同的多条，合并后再报 |
| 健康检查 | `vchat doctor` | 开跑前确认 |

不要把整条命令（如 `sns-ls 30`）放进一个引号里传给 vchat，子命令和参数要分开。`fav-ls` 不接受数字位置参数。

## 推荐扫描流程

使用 `scripts/scan_wechat.py`：

```bash
export TZ=Asia/Shanghai
python3 scripts/scan_wechat.py --since "$SINCE" -o "$OUT/wd_MMDD_HHMM.txt"
```

脚本会：列出最近会话 → 按 `last_timestamp` 筛窗 → 对窗内会话拉 `history --since --asc` → 抽出卡片 XML 的 title / des / url 和引用回复。输出是给人（或 Agent）读的摘要，不要提交到 git。

若上一档机器离线，本档连通后把 `--since` 设成状态文件里的 `last_scan_until.wechat`，一次补扫。

## 解析时的坑

- 群消息 `content` 可能带 `wxid:` 前缀，要去掉再读正文
- `local_type` 为 49 的卡片要从 XML 抽 `title` / `des` / `url`，并把 `&amp;` 还原成 `&`
- 消息时间字段是 `create_time`（unix 秒），发送人是 `sender_name`；引用原文在 `<refermsg><content>`
- 隔夜后 `sns-ls` 可能还停在前一晚，早盘朋友圈不要当成已经覆盖到早上
- 原始输出不要放在系统 `/tmp` 再跨机器拷贝（有的远程工具不允许）；写到用户主目录下的工作目录再取回
- 本机 zsh 里不要用 `[ == ]` 判断，也不要让 `echo` 以 `==` 开头
