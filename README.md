# Loopwork Skill

**A drop-in Claude Code skill that turns a complete beginner's idea into working, continuously-evolving software — through a guided loop workflow.**

一个拖进 Claude Code 就能用的引导型 skill：不会编程的人说出一个想法，它以向导身份带他走完「访谈 → 白话规格 → 批准计划 → 自主循环开发 → 亲手验收」的全过程，然后把项目装进永续循环——**你出方向，AI 跑圈，项目不是做完的，是转起来的。**

## Why

"Beginner-friendly AI builders" (Lovable / Bolt / Replit) and "engineering-grade Claude Code workflows" (superpowers / spec-kit / BMAD) are two lines that never crossed — the former are closed paid products, the latter assume you are an engineer, and both stop at *delivery*. Loopwork sits at the intersection and goes one step further: **verified engineering discipline (spec-driven + test-first + autonomous loops + human acceptance), translated into plain language, packaged in one folder, with a perpetual improvement loop as the end state instead of a one-shot delivery.**

## Install（安装，只有一步）

Download this repo, put the **`loopwork/` folder** into:

```
~/.claude/skills/loopwork
```

Done. Open Claude Code and say（打开 Claude Code，直接说）：

> 我想做一个记账工具，但我不会编程

or explicitly: `/loopwork 我的想法`

Recommended: Claude Code ≥ 2.1.196.

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

**v1 built, live-testing in progress.** Release gates (see [PROJECT.md](PROJECT.md) §9): four cold-start scenarios, red-team test against the guards, doc-volume discipline, and one real beginner completing a voyage + one solo loop cycle. Until those pass, treat this as beta.

- Design doc: [PROJECT.md](PROJECT.md)（含完整用户旅程、五道锁、设计依据）
- Ecosystem research: [docs/research/](docs/research/)（官方规范 / spec-driven 框架 / 循环纪律 / 小白引导，4 份调研）

## Roadmap

- v1.x — real-beginner feedback, scheduled ignition (闹钟档), English-first pass
- v2 — Codex edition (different hook & instruction system, separate build)

## License

TBD (all rights reserved until decided).
