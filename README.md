# Loopwork Skill · Claude Code Edition

![version](https://img.shields.io/badge/version-1.5-blue) ![status](https://img.shields.io/badge/status-beta-orange) ![license](https://img.shields.io/badge/license-MIT-blue) ![claude-code](https://img.shields.io/badge/Claude_Code-%E2%89%A5_2.1.196-8A2BE2) ![lang](https://img.shields.io/badge/%E4%B8%AD%E6%96%87-first-red)

**A drop-in Claude Code skill that turns a complete beginner's idea into working, continuously-evolving software — through a guided loop workflow.**

> 🟢 **OpenAI Codex 用户**：请用姊妹版 [loopwork-skill-codex](https://github.com/EricEEEEEEE/loopwork-skill-codex)。两版方法论同源，围栏按各自平台原生机制实现。

一个拖进 Claude Code 就能用的引导型 skill：不会编程的人说出一个想法，它以向导身份带他走完「访谈 → 白话规格 → 批准计划 → 自主循环开发 → 亲手验收」的全过程，然后把项目装进永续循环——**你出方向，AI 跑圈，项目不是做完的，是转起来的。**

## Why

"Beginner-friendly AI builders" (Lovable / Bolt / Replit) and "engineering-grade Claude Code workflows" (superpowers / spec-kit / BMAD) are two lines that never crossed — the former are closed paid products, the latter assume you are an engineer, and both stop at *delivery*. Loopwork sits at the intersection and goes one step further: **verified engineering discipline (spec-driven + test-first + autonomous loops + human acceptance), translated into plain language, packaged in one folder, with a perpetual improvement loop as the end state instead of a one-shot delivery.**

|  | Lovable / Bolt | spec-kit / BMAD | superpowers | **Loopwork** |
|---|---|---|---|---|
| Install | paid website | CLI toolchain (Python/Node) | `/plugin install` | **drag one folder** |
| Audience | beginners | engineers | engineers | **beginners** |
| End state | one-shot delivery | one-shot delivery | one-shot delivery | **perpetual loop** |
| Discipline | platform-managed | mostly text conventions | workflow-enforced | **hook-enforced (physical)** |

## 🇨🇳 中文快速上手（3 分钟）

**第 1 步 · 下载**：点本页绿色 **Code** 按钮 → **Download ZIP** → 解压。（会用 git 的话：`git clone https://github.com/EricEEEEEEE/loopwork-skill-claude-code.git`）

**第 2 步 · 安装**：把解压出来的 **`loopwork` 文件夹**（注意是里面那个 loopwork 文件夹，不是整个仓库）放进：

- macOS / Linux：`~/.claude/skills/loopwork`
- Windows：`%USERPROFILE%\.claude\skills\loopwork`

没有 `skills` 文件夹就自己新建一个。命令行党一步到位：

```bash
git clone https://github.com/EricEEEEEEE/loopwork-skill-claude-code.git /tmp/lw && mkdir -p ~/.claude/skills && cp -R /tmp/lw/loopwork ~/.claude/skills/
```

**第 3 步 · 开口**：打开 Claude Code（新会话），直接说你的想法：

> 我想做一个记账工具，但我不会编程

剩下的交给向导。你全程只做三件事：**回答问题、看结果、点批准**。中途随时可以关掉，回来说「继续」就能接上。

## What a session looks like（示例对话）

> **你**：我想做一个每天记录喝水杯数的小工具，但我完全不会编程
>
> **向导**：收到，我来当你的向导。接下来你全程只做三件事：回答我的问题、看我给你的结果、对重要的事点头。写代码、跑测试、存档这些脏活全部归我。先聊 10 分钟想法——
> 第一个问题：这个工具给谁用？
> ① 就我自己（推荐，最简单）　② 我和家人　③ 给很多人用　④ 其他
>
> **你**：1
>
> **向导**：明白，那就不需要注册登录——少一大块复杂度。主要在哪儿用它？
> ① 电脑浏览器（推荐）　② 手机　③ 都要　④ 不知道，你来定
>
> **你**：4
>
> **向导**：那我定：做成网页，电脑手机浏览器都能开，不用装任何东西。……（几问之后）……想法钉死了，项目简介 60 字如下……对吗？
>
> **你**：对
>
> **向导**：下一步我把它翻译成「做成什么样才算对」的验收清单——每一条都是你将来能亲手点一遍验收的句子。**你批准计划之前，我一行代码都不会写。**

…of course your session will differ — but the shape is always: interview → plain spec → your approval → autonomous loop → click-through acceptance → the perpetual improvement cycle.

Requires: Claude Code ≥ 2.1.196 recommended.

## How it works（两个半场）

```
上半场 · 首航（直线，走一次）
0 开场体检 → 1 想法访谈 → 2 白话规格+项目规矩 → 3 摊开计划(你批准)
→ 4 循环执行 ⟲ → 5 验收(照单点一遍) → 6 收尾 → 进环仪式

下半场 · 循环模式（圆环，转无限次）
点火(30秒) → AI 跑批(挂机) → 收货(3-10分钟) → 续单(5分钟) → 再点火…
```

You only ever do three things: **answer questions, look at results, approve.**
用户全程只做三件事：回答问题、看结果、点批准。

## What's inside

```
loopwork/
├── SKILL.md              # 向导本体：铁律 + 阶段路由（压缩存活区置顶）
├── references/           # 7 个阶段剧本 + 循环模式 + 快速通道 + 白话词典
├── scripts/              # 确定性机器
│   ├── init_project.sh   #   建家：git + 状态机 + 围栏接线
│   ├── verify.sh         #   验收裁判：exit code 说了算（fail closed）
│   ├── progress.py       #   状态机 + 进度卡（SessionStart 自动播报）
│   ├── guard_rules.py    #   围栏规则内核：纯函数、无 I/O（与 Codex 版字节相同）
│   ├── guard_edits.py    #   围栏：实现期锁死考题/规格/规矩
│   ├── guard_bash.py     #   围栏：拦 rm -rf / force push / shell 绕道改写 / 先绿后红的存档
│   ├── guard_ask.py      #   围栏：挂机批内拦弹窗提问（该写 BLOCKED.md 跳过）
│   ├── guard_log.py      #   拦截取证：blocks.jsonl（只增不减）
│   ├── audit_log.py      #   PostToolUse 全量审计日志
│   ├── stop_batch.py     #   检测门 + 挂机档：Stop 钩子轮末对账 + 自动续轮（外部计数器）
│   └── selftest.sh       #   装机自检：探明你这台机器的围栏能力面
└── agents/reviewer.md    # 只读判卷员（验收前预检，N 对 M 点名）
```

## Discipline is enforced, not suggested（纪律是硬的）

Industry lesson (68 documented failure cases): text rules get read, "understood", and ignored under pressure. So:

- Tests must **fail first** (red) before implementation; during implementation the test files are **physically locked** by a PreToolUse hook — including the known bypass via `sed`/`echo`/`tee` in Bash;
- Acceptance = `verify.sh` **exit code**, never the model's claim; unparseable = not passed (fail closed);
- Iteration caps are counted by **external scripts**, not by the model;
- Money / deletion / publishing / secrets: unconditional human gates, never mixed into "next step";
- Every task = one git commit ("存档点"), everything reversible.

## 诚实的能力边界（围栏拦不住什么）

围栏是**减少偶然违规**的工程装置，不是**对抗蓄意规避**的安全边界。一个想绕的模型（或一个想绕的你）总有路。把缝摊开说清楚，比假装没有更有用：

- **本版没有 OS 沙箱**。物理边界只有钩子覆盖面——这是与 [Codex 版](https://github.com/EricEEEEEEE/loopwork-skill-codex)（多一层 Seatbelt，`.git` 对模型都不可写）的实质差距，不遮掩。
- **命令行匹配面永远有缝**。`guard_bash.py` 读的是命令文本，所以解释器一行程序（`python3 -c "open('tests/a.py','w')…"`）、变量间接（`X=tests; sed -i "" … $X/a.py`）、以及各种拼接写法都可能不命中。**这正是第三层检测门存在的理由**：绕过实时围栏改了考题，轮末基线对账照样把它翻出来——两层的缝不重合，才是覆盖面。
- **`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP=0` 能把顶回整个关掉**，检测门随之失效。这是本版最危险的静默失效点：你以为轮末在对账，其实 Stop 钩子的话没人听。
- **用户自己终端里敲的命令不经过围栏**。这是特性不是缺陷：关批的开关只在你手上（`rm .loopwork/batch.flag`），模型删不掉。反过来说，你在自己终端里做的任何事，围栏一概不知情。
- **版本漂移**。平台的钩子字段形状、顶回上限、权限语义都可能变。[VERIFICATION.md](VERIFICATION.md) 里每条结论都带日期，**装机后请跑 `loopwork/scripts/selftest.sh` 以你自己的版本为准**——本仓库的实测是那一天的事实，不是永久承诺。

## 围栏管不到的地方：第三方 skill 是供应链（这一个也是）

围栏管的是**我**（模型）在这个项目里能干什么。它管不了**你装了什么**。

- **skill / MCP server / 钩子 = 每轮自动执行的代码，权限和 AI 一样大。** 装之前读一遍，尤其是 `scripts/` 里的东西。loopwork 自己也不例外：它的每个脚本都在这个仓库里摊开，`init_project.sh` 往你项目里写哪几个文件，上面 What's inside 一节列得清清楚楚。
- **别让 AI 替你挑安装来源。** 2026 年 7 月 Island 的实测（[CSA AI Safety Initiative 研究简报](https://labs.cloudsecurityalliance.org/research/csa-research-note-fakegit-agentbaiting-mcp-supply-chain-2026/)）：约 7,600 个伪装仓库、约 6,600 个假开发者账号，其中 800+ 直接伪装成 AI Skill / MCP server，在 LobeHub / Glama / MCP.so / MCP Market 等公开目录挂了 600+ 条，Release 附件累计下载 1,400 万+。这套打法（AgentBaiting）不骗人点链接，它骗 **AI 去发现仓库**、把攻击者写的 README 当成正经文档、再由 AI 把安装指引转达给你——你面对的问题从「要不要点这个陌生链接」变成「要不要照我的 AI 刚给的指引做」。载荷是 SmartLoader → StealC（浏览器凭据 / cookie / token / SSH 密钥 / 截图）。
- **「不再询问」是按动作类别记的，不是按这一次记的。** 学术侧在 Claude Code 上复现过：为一次正常操作点下的 "Yes, and don't ask again"，让之后一条恶意脚本无需再确认就跑了起来（[arXiv:2510.26328](https://arxiv.org/abs/2510.26328)）。凡是带「记住我的选择」的权限框都该按这个心态对待——这个勾只对你真的放心的类别点。

Stage 0 的体检会把这几条讲给用户，并报出「这个项目里除了 loopwork 还挂着谁」。

## Status

**v1.5; guard machinery fully regression-tested (167-case suite in [tests/](tests/), run `python3 tests/test_guards.py` in this repo); 存档闸 / 挂机批 / 顶回上限 / 停滞判定已在真项目上跑通一整轮（记录见 [VERIFICATION.md](VERIFICATION.md)）; real-beginner field test pending.** Release gates in [PROJECT.md](PROJECT.md) §9. Until a real beginner completes a voyage + one solo cycle, treat this as beta.

- Design doc: [PROJECT.md](PROJECT.md)（含完整用户旅程、五道锁、设计依据）
- Ecosystem research: [docs/research/](docs/research/)（官方规范 / spec-driven 框架 / 循环纪律 / 小白引导，4 份调研）

## Roadmap

- v1.x — real-beginner feedback, scheduled ignition (闹钟档), English-first pass
- v2 — Codex edition: **shipped** → [loopwork-skill-codex](https://github.com/EricEEEEEEE/loopwork-skill-codex)

## License

MIT — see [LICENSE](LICENSE).
