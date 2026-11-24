# im-digest · 小时情报

> 把你自己的微信和飞书，按时间窗收成一份能动手的盘点。
> 建议一天几档（09:00、13:00、18:00），而不是下班才回忆。

这是 [xiangruiai-toolkit](https://github.com/xiangruiai/xiangruiai-toolkit) 里的一个 Skill，路径是 `skills/飞书办公/im-digest`。它提供通用步骤、脚本和模板，供别人在自己的账号上使用。真实聊天、token、openId 和知识库节点只留在本地配置，不进本目录。

输出是同一份当天状态文件，以及可选的三种呈现：Cursor / Grok Page、只发给你本人的飞书互动卡片、知识库里的日节点。没有 Page 时，只发卡片和写日节点即可。

微信数据走本仓库已有的 [vchat CLI](../../../cli/vchat)（`cli/vchat`）。公开安装只使用本工具箱的地址。

## 它解决什么，不解决什么

- 要处理的事、客户卡点、值得知道的信息、可写的选题、今天已经解决的事
- 同时读微信本地数据和飞书（私聊、@、邮件、日历、文档、任务、审批）
- 只读采集；卡片只发给你自己

和同仓库里另外两个相近 skill 的分工：

- [daily-log · 收工日志](../daily-log)：飞书单日收工复盘文档，一天结束时写成一份带链接、能 @ 人的工作文档
- [group-daily · 群日报](../../内容设计/group-daily)：把一个微信群做成杂志风 HTML / 长图
- 本 skill：跨微信和飞书的个人行动摘要，一天可以跑多档

三者可以并存，各自使用自己的版式。

## 依赖

### 1. vchat（微信本地数据 CLI）

vchat 在已登录微信桌面版的那台电脑上，只读本机数据库，不上传数据。建议 2.1.0 及以上。它就在本工具箱里，不需要另找仓库。

- 仓库：https://github.com/xiangruiai/xiangruiai-toolkit
- 组件路径：https://github.com/xiangruiai/xiangruiai-toolkit/tree/main/cli/vchat
- 本仓库说明：[cli/vchat/README.md](../../../cli/vchat/README.md)

```bash
git clone https://github.com/xiangruiai/xiangruiai-toolkit.git
cd xiangruiai-toolkit/cli/vchat
bash install.sh
pip3 install cryptography zstandard
sudo vchat setup       # macOS；Windows 见该 README
vchat doctor
```

也可以把这段话交给你的 AI Agent，让它按 `cli/vchat` 的 README 安装：

> **帮我安装 https://github.com/xiangruiai/xiangruiai-toolkit 里的 vchat CLI，路径是 cli/vchat。按它的 README 安装，装完跑 vchat doctor。**

使用前请阅读组件目录里的免责声明：只处理你自己的账号和你拥有合法访问权的数据。

### 2. lark-cli（飞书官方 CLI）

公开安装入口：

- GitHub：https://github.com/larksuite/cli
- npm：https://www.npmjs.com/package/@larksuite/cli
- 开放平台介绍：https://open.larkoffice.com/document/mcp_open_tools/feishu-cli-let-ai-actually-do-your-work-in-feishu

```bash
npx @larksuite/cli@latest install
lark-cli config init
lark-cli auth login --recommend
lark-cli auth status
```

本机若有 HTTPS 代理导致命令异常，可先 `export LARK_CLI_NO_PROXY=1`。

### 3. 本 Skill

#### 让 Agent 自动安装（推荐）

把下面这句话贴给 Codex、Claude Code 或其他支持 Skill 的 Agent：

> **帮我安装 https://github.com/xiangruiai/xiangruiai-toolkit 里的 im-digest skill，路径是 skills/飞书办公/im-digest。安装到当前 Agent 的 skills 目录。微信数据用同一仓库的 cli/vchat。缺 lark-cli 就按官方说明安装。装好后提醒我把 examples/config.example.yaml 复制成本地配置，真实值只留在本机。**

#### Codex 手动安装

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo xiangruiai/xiangruiai-toolkit \
  --path 'skills/飞书办公/im-digest'
```

安装后开启一个新对话，让 Codex 重新发现 Skill。

#### Claude Code 手动安装

```bash
git clone https://github.com/xiangruiai/xiangruiai-toolkit.git
cp -R 'xiangruiai-toolkit/skills/飞书办公/im-digest' ~/.claude/skills/
```

安装后重启 Claude Code。对 AI 说一句“小时情报”或“盘点一下微信和飞书”即可。Python 3 即可运行 `scripts/` 下的生成脚本，无额外第三方包。

## 配置

复制示例，只留在本地，不要提交真实值：

```bash
cp examples/config.example.yaml config.local.yaml
cp examples/client_aliases.example.json config/client_aliases.json
# 按需新建 config/key-chats.txt、config/months.tsv
```

至少要改：

- 时区和每天几档
- 状态文件、原始扫描的本地目录
- 你的姓名（用来搜被提到但没 @ 的消息）
- 飞书知识空间、小时情报父节点（若启用日节点）
- 重点会话和需要跳过的机器人会话（本地列表，不要写进 skill）
- 是否启用 Page、卡片、日节点，以及没有变化时是否安静跳过

字段含义见 `examples/config.example.yaml` 和 `references/state-schema.md`。

建议的默认值都写在配置里，脚本不会把它们写成死上限：要处理的大约 12 条，低优先级超过大约 3 天没有新进展就收起，日程建议 09:00 / 13:00 / 18:00，窗口内没有变化时 `quiet_if_no_change` 跳过重复卡片。

## Skill 和本地配置分别放什么

**Skill（`skills/飞书办公/im-digest`）**负责怎么采集、怎么去重、五个板块怎么写、卡片和日节点长什么样、以及只读与隐私边界。这些是通用配方，别人拿去也能用。

**本地配置 / 定时 routine**负责：

- 几点跑、在哪台已登录微信的机器上跑
- 你的知识库、Page、客户别名、重点会话
- 条目上限、收起规则、安静档这些个人偏好

不要把聊天原文、客户名单或 token 写进 skill，也不要写进可分享的 routine 正文。

## 一档盘点怎么跑

完整判断流程以 [`SKILL.md`](SKILL.md) 为准。命令层面通常是：

```bash
export TZ=Asia/Shanghai
# 1. 微信扫描（必须在已登录微信的机器上）
python3 scripts/scan_wechat.py --since "YYYY-MM-DD HH:MM" -o raw/wd_MMDD_HHMM.txt

# 2. 飞书扫描（--as user，只读）
export FS_SINCE='YYYY-MM-DDTHH:MM:00+08:00'
export FS_END='YYYY-MM-DDTHH:MM:00+08:00'
export FS_MY_NAME='你的姓名'
export FS_OUT=raw/feishu-HHMM
bash scripts/scan_feishu.sh

# 3. 由 Agent 根据 SKILL.md 更新当天状态文件（不要把原始聊天写进去）

# 4. 可选：生成 Page 源码后写入当天 Page
python3 scripts/mkpage.py --state data/YYYY-MM-DD.json -o page-MMDD.tsx

# 5. 生成并只发给自己的飞书卡片
python3 scripts/gen_card.py --state data/YYYY-MM-DD.json -o daily-YYYY-MM-DD.json
bash scripts/send_card.sh daily-YYYY-MM-DD.json

# 6. 可选：覆盖同步知识库日节点
python3 scripts/mkday_md.py --state data/YYYY-MM-DD.json -o /tmp/day.md
# 随后按 references/feishu-recipes.md 创建或 overwrite 日节点，并替换优先级彩色标签
```

## 适配到你自己的飞书和微信

1. 飞书知识库：先建一个专门放小时情报的父节点，按月建子节点，再按天建日节点。`space_id` 和 token 只放本地配置。日节点标题默认是 `{date} 小时情报`，可改
2. 飞书卡片：保持 `card_target: self`。`send_card.sh` 会读取当前登录用户的 openId，不要改成群 ID
3. 微信：用会话的 username 拉历史，不要只用显示名。把活跃大群、机器人通知是否进入盘点的规则写在自己的配置里
4. 板块可以增删，但若改了字段，需要同步改 `mkpage.py` / `mkday_md.py` / `gen_card.py`
5. 没有 Page 的环境可以只开卡片和日节点；没有知识库的可以只开卡片

## 目录

```
skills/飞书办公/im-digest/
├── SKILL.md                         # Agent 执行配方
├── README.md
├── scripts/
│   ├── scan_wechat.py               # 时间窗扫描微信会话
│   ├── scan_feishu.sh               # 时间窗只读采集飞书
│   ├── gen_card.py                  # 状态文件 → 飞书互动卡片 JSON
│   ├── send_card.sh                 # 卡片只发给当前用户
│   ├── mkday_md.py                  # 状态文件 → 日节点 Markdown
│   └── mkpage.py                    # 状态文件 → Page TSX（可选）
├── references/
│   ├── wechat-scan.md
│   ├── feishu-recipes.md
│   ├── page-style.md
│   └── state-schema.md
└── examples/
    ├── config.example.yaml
    ├── state.example.json
    └── client_aliases.example.json
```

运行时的 `data/`、`raw/`、`config.local.yaml`、`config/key-chats.txt`、`config/months.tsv` 和日状态 JSON 已在 `.gitignore` 中忽略，不要提交。

## 免责声明

**本 skill 仅供个人学习与研究用途。**

1. 只在使用者自己的设备、自己的微信和飞书账号、自己拥有合法访问权的数据上操作。严禁未经他人同意访问、解析他人数据，严禁任何商业目的的批量采集，严禁监控、跟踪、骚扰他人，以及违反《中华人民共和国网络安全法》《个人信息保护法》《数据安全法》和微信、飞书 / Lark 用户协议的任何行为。
2. 本 skill 不提供任何形式的明示或暗示担保，一切使用后果由使用者自行承担。
3. 微信、WeChat、飞书、Lark 等名称归其各自持有人所有。本项目与之无任何关联，亦未获授权或背书。
4. vchat 与 lark-cli 各有自己的许可证和声明，使用时以它们的目录或上游仓库为准。
5. 一旦下载或使用，即视为接受本声明和工具箱根目录的使用边界。若不接受，请立即停止使用并删除。

完整边界见仓库根目录 [README](../../../README.md) 的使用说明。

## License

本目录不另附许可证，适用工具箱根目录 [LICENSE](../../../LICENSE)：MIT，版权归 xiangruiai（李祥瑞 / 万涂幻象），并附个人学习用途条款。
