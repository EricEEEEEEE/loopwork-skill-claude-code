# 调研报告 A · Anthropic 官方 Agent Skills 规范

> 调研日期：2026-07-11 ｜ 调研范围：Claude Code 官方文档、Agent Skills 开放标准（agentskills.io）、GitHub anthropics/skills 仓库、Anthropic 工程博客，外加实地验证本机已安装的 `skill-creator`（485 行）与 `doc-coauthoring`（376 行）两个官方生产级 skill 源码。

---

## a) SKILL.md 确切格式

**必需字段**（两个信息源略有差异，取更严格者为准）：

Agent Skills 开放标准（agentskills.io/specification）：
> `name` — Required. "Max 64 characters. Lowercase letters, numbers, and hyphens only. Must not start or end with a hyphen." "Must match the parent directory name."
> `description` — Required. "Max 1024 characters. Non-empty. Describes what the skill does and when to use it."

Claude 官方 best-practices（platform.claude.com）额外约束（更严）：
> `name`: "Cannot contain XML tags" / "Cannot contain reserved words: 'anthropic', 'claude'"
> `description`: "Cannot contain XML tags"

**Claude Code 的实现有一处重要放宽**：`name` 在 Claude Code 里其实是可选的（"All fields are optional. Only `description` is recommended"），且不强制等于目录名——命令名来自目录名，`name` 只是列表里的 display label。但因为要做成跨工具可移植的开放标准 skill，**建议仍按开放标准的严格版写**：小写字母+数字+连字符、不以连字符开头/结尾、无连续连字符、等于目录名。

**可选字段**（Claude Code 独有，开放标准里没有）：`when_to_use`、`argument-hint`、`arguments`、`disable-model-invocation`、`user-invocable`、`allowed-tools`、`disallowed-tools`、`model`、`effort`、`context`、`agent`、`hooks`、`paths`、`shell`。开放标准里还有 `license`、`compatibility`（≤500 字符）、`metadata`（任意 key-value）。

**description 怎么写才能被正确触发**（多个来源一致强调）：
- 必须 "third person"："**Good:** 'Processes Excel files and generates reports' / **Avoid:** 'I can help you...'"
- 必须同时说明 what + when："Should describe both what the skill does and when to use it" "Should include specific keywords that help agents identify relevant tasks"
- Claude Code 截断陷阱：`description` + `when_to_use` 在技能列表里合并后按 **1,536 字符**截断（不是 spec 规定的 1024），且 "Put the key use case first"——超长部分会被砍掉，最重要的触发场景必须写在最前面。
- 命名推荐用动名词形式（gerund）："`processing-pdfs`, `analyzing-spreadsheets`" 优于笼统词如 "helper/utils/tools"。

来源：https://agentskills.io/specification ｜ https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices ｜ https://code.claude.com/docs/en/skills

## b) 渐进披露机制——对「一个 skill 引导多阶段长流程」的关键含义

三层加载模型（agentskills.io 原文）：
> "1. **Discovery**: At startup, agents load only the name and description... 2. **Activation**: When a task matches a skill's description, the agent reads the full `SKILL.md` instructions into context. 3. **Execution**: The agent follows the instructions, optionally executing bundled code or loading referenced files as needed."

Token 预算官方量化建议：
> "1. **Metadata** (~100 tokens)... 2. **Instructions** (< 5000 tokens recommended)... 3. **Resources** (as needed)"
> "Keep your main `SKILL.md` under 500 lines."
> "Keep file references one level deep from `SKILL.md`. Avoid deeply nested reference chains."

**对长流程设计决定性的机制**——skill 内容一旦被加载，只在首次注入时进入上下文，之后不会重新读取：
> "When you or Claude invoke a skill, the rendered `SKILL.md` content enters the conversation as a single message and stays there for the rest of the session. Claude Code does not re-read the skill file on later turns, so write guidance that should apply throughout a task as standing instructions rather than one-time steps."

**自动压缩（auto-compaction）行为**——直接决定长自主循环里 skill 指令会不会「失忆」：
> "When the conversation is summarized to free context, Claude Code re-attaches the most recent invocation of each skill after the summary, **keeping the first 5,000 tokens of each**. Re-attached skills share a combined budget of 25,000 tokens."
> "If a skill seems to stop influencing behavior after the first response... re-invoke it after compaction to restore the full content."

**实际含义**：如果 skill 要支撑可能跑几小时/跨多次 compaction 的自主循环，SKILL.md **只有前 ~5000 token 能在压缩后存活**。必须把「核心循环铁律」放在文件最前面，把每个阶段的详细操作步骤拆到 `references/*.md`，靠 Claude 按需重新 Read（这些文件不受 5000-token 上限约束，可随时重读）。

来源：https://agentskills.io ｜ https://code.claude.com/docs/en/skills（"Skill content lifecycle" 一节）

## c) 官方对 skill 大小/结构的建议

三个信息源数字完全一致，可视为硬性共识：

| 来源 | 原文 |
|---|---|
| agentskills.io/specification | "Keep your main `SKILL.md` under 500 lines. Move detailed reference material to separate files." |
| code.claude.com/docs/en/skills | "Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files." |
| platform.claude.com best-practices | "Keep SKILL.md body under 500 lines for optimal performance. If your content exceeds this, split it into separate files" |

拆分触发条件：`references/` 文件超过 100 行必须加目录；互斥场景应拆到不同文件（"If certain contexts are mutually exclusive or rarely used together, keeping the paths separate will reduce the token usage"）。

实地参照：`skill-creator` 485 行、`doc-coauthoring` 376 行——都卡在 500 行红线以内。

## d) 脚本执行 / 多轮交互 / 官方向导型先例

**脚本**：官方明确支持且鼓励，`scripts/` 里的代码是 "executed, not loaded"——不占上下文，只有输出占 token。判断标准："Prefer scripts for deterministic operations: Write `validate_form.py` rather than asking Claude to generate validation code"。脚本要 "Solve, don't punt"——显式处理错误，避免 "voodoo constants"。

**多轮交互**：官方支持，没有特殊 API——机制就是普通对话轮换。skill 内容加载后作为一条消息常驻上下文一整个 session，Claude 在第 20 轮对话时依然记得「我们在 Stage 2」。

**⚠️ 直接先例（两个官方生产 skill）**：

1. **`skill-creator`**——向导流程：Capture Intent（访谈用户）→ Interview and Research → Write SKILL.md → 生成测试用例并给用户确认 → spawn 子 agent 跑测试（with-skill vs baseline 对照）→ HTML viewer 让用户逐条反馈 → 迭代 → 打包交付。用 `agents/grader.md` 等三个 subagent 定义文件做客观评分，用 `evals/evals.json`、`benchmark.json`、`feedback.json` 做跨轮次的**外部状态持久化**。
2. **`doc-coauthoring`**——结构上最贴近目标：单文件 376 行，三阶段（Context Gathering → Refinement & Structure → Reader Testing），每阶段有明确 Exit condition、Transition 提示、"if user declines this workflow, work freeform" 降级路径。细节：
   - "**Exit condition:** Sufficient context has been gathered when questions show understanding..."
   - 用子 agent 做「读者视角」验收；
   - 人工验收权责："Recommend they do a final read-through themselves - **they own this document and are responsible for its quality**."
   - 防无效打磨："After 3 consecutive iterations with no substantial changes, ask if anything can be removed"。

**没有找到任何官方 skill 是专门做「引导编程小白从想法到完整软件项目」的**——需要自己拼装。

**额外发现**：Anthropic 工程博客 *Effective harnesses for long-running agents*（https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents）：
> "an initializer agent that sets up the environment on the first run, and a coding agent that is tasked with making incremental progress in every session"
> "claude-progress.txt file that keeps a log of what agents have done"，配合 git commit 记录进度
> "Set up a structured JSON file with a list of end-to-end feature descriptions"，初始状态标记为 failing，防止 agent 过早宣称完成
> "The next iteration of the coding agent was then asked to work on only one feature at a time. This incremental approach turned out to be critical"

来源：https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md ｜ https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md ｜ https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

## e) skill 与 slash command / CLAUDE.md / subagent / hook 的分工

**vs Slash Command**：已合并，command 是 skill 的功能子集。"**Custom commands have been merged into skills.**" 新建优先用 skill。

**vs CLAUDE.md**："Create a skill when you keep pasting the same instructions, checklist, or multi-step procedure into chat, **or when a section of CLAUDE.md has grown into a procedure rather than a fact**." 一句话：CLAUDE.md 是常驻的「事实/偏好」，skill 是按需加载的「流程」。

**vs Subagent**：双向支持——`context: fork` 让 skill 正文变成 subagent 任务 prompt（警告：只适合有明确任务指令的 skill）；自定义 subagent 可在定义里声明 `skills` 字段预加载。

**vs Hook**：「概率性指令 vs 确定性强制」的分工。"use hooks to enforce behavior deterministically"。Skill 有 `hooks` frontmatter 字段，可把 hook 限定在该 skill 生命周期内。**启示**：自主循环里「绝对不能跳过」的硬约束用 hook，光靠 SKILL.md 文字是概率性的。

## f) 分发方式

**「拖一个文件夹进 `~/.claude/skills/` 或 `.claude/skills/`」就是官方标准安装方式**。四级作用域优先级：enterprise > personal > project > plugin。

**Plugin 与裸 skill 的差别**：plugin 是更重的分发单元（可打包 agents/hooks/MCP servers，带命名空间）。混合形态：给普通 skill 文件夹加 `.claude-plugin/plugin.json` 即变成可安装 plugin。**对小白场景：裸 skill 文件夹 + 拖入法是最低摩擦的分发形式。**

## 对设计的直接启示

1. **单文件 + 分阶段路由是官方验证过的形状**——照抄 doc-coauthoring 骨架（Stage 划分 + Exit condition + Transition + 降级路径 + "Always give user agency to adjust the process"）。
2. **5000-token compaction 存活线决定内容分层，不是可选项。**
3. **自主循环阶段用 `disallowed-tools` 硬隔离「人工确认」动作**（官方场景原文："such as `AskUserQuestion` for a background loop"），红线用 hook 兜底。
4. **借 skill-creator 的「外部状态文件 + 子 agent 验证 + 人只看结果给反馈」模式做验收。**
5. **description 为长流程写触发词、场景堆最前**；`disable-model-invocation` 用于有副作用的显式启动流程时再考虑。
