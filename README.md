# Loopwork Skill

![status](https://img.shields.io/badge/status-beta-orange) ![license](https://img.shields.io/badge/license-MIT-blue) ![claude-code](https://img.shields.io/badge/Claude_Code-%E2%89%A5_2.1.196-8A2BE2) ![lang](https://img.shields.io/badge/%E4%B8%AD%E6%96%87-first-red)

**A drop-in Claude Code skill that turns a complete beginner's idea into working, continuously-evolving software — through a guided loop workflow.**

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

**第 1 步 · 下载**：点本页绿色 **Code** 按钮 → **Download ZIP** → 解压。（会用 git 的话：`git clone https://github.com/EricEEEEEEE/loopwork-skill.git`）

**第 2 步 · 安装**：把解压出来的 **`loopwork` 文件夹**（注意是里面那个 loopwork 文件夹，不是整个仓库）放进：

- macOS / Linux：`~/.claude/skills/loopwork`
- Windows：`%USERPROFILE%\.claude\skills\loopwork`

没有 `skills` 文件夹就自己新建一个。命令行党一步到位：

```bash
git clone https://github.com/EricEEEEEEE/loopwork-skill.git /tmp/lw && mkdir -p ~/.claude/skills && cp -R /tmp/lw/loopwork ~/.claude/skills/
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
│   ├── guard_edits.py    #   围栏：实现期锁死考题/规格/规矩
│   ├── guard_bash.py     #   围栏：拦 rm -rf / force push / shell 绕道改写
│   └── stop_batch.py     #   挂机档：Stop 钩子自动续轮（外部计数器）
└── agents/reviewer.md    # 只读判卷员（验收前预检，N 对 M 点名）
```

## Discipline is enforced, not suggested（纪律是硬的）

Industry lesson (68 documented failure cases): text rules get read, "understood", and ignored under pressure. So:

- Tests must **fail first** (red) before implementation; during implementation the test files are **physically locked** by a PreToolUse hook — including the known bypass via `sed`/`echo`/`tee` in Bash;
- Acceptance = `verify.sh` **exit code**, never the model's claim; unparseable = not passed (fail closed);
- Iteration caps are counted by **external scripts**, not by the model;
- Money / deletion / publishing / secrets: unconditional human gates, never mixed into "next step";
- Every task = one git commit ("存档点"), everything reversible.

## Status

**v1 built; guard machinery fully regression-tested (36-case suite in [tests/](tests/), run `bash loopwork/scripts/verify.sh` in this repo); live cold-start scenarios simulated, real-beginner field test pending.** Release gates in [PROJECT.md](PROJECT.md) §9. Until a real beginner completes a voyage + one solo cycle, treat this as beta.

- Design doc: [PROJECT.md](PROJECT.md)（含完整用户旅程、五道锁、设计依据）
- Ecosystem research: [docs/research/](docs/research/)（官方规范 / spec-driven 框架 / 循环纪律 / 小白引导，4 份调研）

## Roadmap

- v1.x — real-beginner feedback, scheduled ignition (闹钟档), English-first pass
- v2 — Codex edition (different hook & instruction system, separate build)

## License

MIT — see [LICENSE](LICENSE).
