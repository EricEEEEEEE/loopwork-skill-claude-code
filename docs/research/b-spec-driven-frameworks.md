# 调研报告 B · Spec-Driven Development 框架

> 调研日期：2026-07-11 ｜ 调研范围：github/spec-kit、BMAD-METHOD、OpenSpec，及实测评价文章。补充两个高度相关的 Claude Code 原生框架（Superpowers、GSD）。

---

## a) 完整阶段流对照

### spec-kit（github/spec-kit）

CLI 工具生成 9 个命令/skill，顺序执行：

| 命令 | 产出文件 | 下一步 |
|---|---|---|
| `/speckit.constitution` | `.specify/memory/constitution.md` | specify |
| `/speckit.specify` | `specs/[feature]/spec.md` | clarify（推荐） |
| `/speckit.clarify` | spec.md 中 Clarifications 章节 | plan |
| `/speckit.plan` | `plan.md` + `data-model.md` + `contracts/` | tasks |
| `/speckit.tasks` | `tasks.md`（含 `[P]` 并行标记） | analyze（可选）→ implement |
| `/speckit.analyze` | 跨文件一致性校验报告 | implement |
| `/speckit.checklist` | 自定义质量清单 | 贯穿全程 |
| `/speckit.implement` | 生产代码，按 tasks.md 顺序、TDD 门禁 | converge |
| `/speckit.converge` | 对照代码库与 spec/plan/tasks 生成补齐任务 | 循环回 tasks |

### BMAD-METHOD（v6）

四阶段（Analysis → Planning → Solutioning → Implementation），27 个 agent、74+ workflow，v6 起核心已重写为官方 `SKILL.md` 格式。关键链：brainstorming → product-brief → PRD → UX/Architecture → epics & stories → dev-story → code-review → 下一 story。特殊件：`bmad-quick-dev`（小任务旁路完整流程）、`bmad-dev-auto`（无人值守循环）、`bmad-help`（状态检测 + 路由，随时告诉你现在该跑哪个 skill）。

### OpenSpec（Fission-AI/OpenSpec）

三阶段 delta-spec 模型，最短链：`/opsx:explore`（可选）→ `/opsx:propose`（proposal + delta specs + tasks）→ `/opsx:apply` → `/opsx:verify` → `/opsx:archive`（delta 合并回主 specs）。

### 相邻框架

- **obra/superpowers**：不产正式 spec 文档，对话中分块展示设计；brainstorming → writing-plans → subagent-driven-development → test-driven-development。
- **GSD (get-shit-done)**：防 context rot 为核心卖点，PLAN.md 即可执行指令，每个子任务派发到全新 200k 上下文 subagent（原仓库已归档迁移 open-gsd/gsd-core，细节未完整核实）。

## b) 处理「用户描述不清」的机制

- **spec-kit `/clarify`**：11 类分类法（数据模型、错误处理、边界条件、非功能需求等）逐类标记 Clear/Partial/Missing，优先审问最欠规格的领域。**一次只问一个问题**，等回答、写入 spec，再问下一个，**最多 5 个**。草稿阶段显式插入 `[NEEDS CLARIFICATION: ...]` 标记，质量清单强制「无残留标记才能进入下一阶段」。
- **BMAD `advanced-elicitation`**：内容精修机制——从方法库（苏格拉底诘问、Pre-mortem、红蓝对抗、第一性原理等）智能挑 5 个匹配当前上下文的方法供用户选。另有 Analyst 角色做前置结构化访谈。
- **OpenSpec**：容忍式——`explore` 可选闲聊澄清；真正机制是 delta spec（ADDED/MODIFIED/REMOVED），把「说不清」的代价从「重写整份规格」降到「补一个 delta」。

三者根本差异：spec-kit 审问式（interrogate）、BMAD 精修式（refine）、OpenSpec 容忍式（tolerate via delta）。

## c) 宪法/原则如何注入每一步

**spec-kit 是唯一有显式宪法机制的**：`/speckit.constitution` 生成 `.specify/memory/constitution.md`，八步执行流含**强制传播一致性**（显式检查 plan/spec/tasks 三个下游模板对齐）+ Sync Impact Report + 语义化版本。实际生效点是 plan 模板的 **"Phase -1 Gates"**——"Gates act as compile-time checks for architectural principles"，宪法条款变成进入技术方案前必须逐条勾选的门禁（历史版本 Article III "Test-First" 标注 **NON-NEGOTIABLE**）。

BMAD 无对等宪法概念（约束在角色人设+对抗性审查 skill）；OpenSpec 无元原则层。

**结论**：要做宪法注入，抄 spec-kit——重点不是「写一份原则文档」，而是「每个下游环节显式声明检查宪法哪一部分」。

## d) 任务清单格式与执行纪律

- **spec-kit tasks.md**：`[P]` 并行标记 + 文件创建顺序强约束（contracts → contract test → integration test → e2e → unit → 源文件）+「不允许投机性功能」清单。
- **BMAD story 文件（最值得借鉴）**：**分区写权限控制**——Dev agent 只被授权编辑 Tasks 复选框和 Dev Agent Record 区块；QA agent 只被授权编辑 QA Results 区块。轻量级并发控制 + 审计留痕：不同角色对同一文件有互斥写权限边界。
- **OpenSpec**：层级编号 + 复选框，设计哲学反对阶段门禁——"artifacts as a dependency graph, not gates"。

## e) 实测短板（5 篇评测汇总）

1. **Scott Logic**：spec-kit 实测比传统迭代提示慢约 4 倍（33.5 分钟 vs 8 分钟）；一个功能迭代产生 **2,577 行 markdown 只换来 689 行代码**；仍有明显 bug；"我不认为 SDD 在其纯粹形式下是可行流程"，怀疑其目标用户是"不写代码的人"但对此持怀疑态度。
2. **ranthebuilder 横评**：BMAD 从规范到 PR 耗时 6 天（12 agent 太复杂）；spec-kit「代码未准确映射规范意图」且**升级覆盖用户自定义文件**；评分 OpenSpec 4.00 > BMAD Quick 3.74 > BMAD Full 3.65 > spec-kit 2.77。新手友好度 spec-kit 最差——"工具不告诉你身在何处"。
3. **Martin Fowler 网站**：小 bug 生成"4 用户故事+16 验收标准"——"用大锤砸坚果"；"宁愿审代码也不想审这些 markdown"；类比 2000 年代 MDD，警告"可能同时继承 MDD 的不灵活 + LLM 的非确定性"。
4. **LPains**："规范非常详细，这增加审查负担，你可能需要 AI 协助来理解你自己的规范"；"编码复杂性不会消失——只是转移到规范阶段"。
5. **Marmelab**：文档过载、流程对多数场景过度复杂、审查时间翻倍、上下文盲目（漏掉需联动更新的既有函数）。（作者未亲测，说服力打折。）

**两条最重要的共性信号**：①「文档量与实际价值不成正比」且「看起来完整实则空洞」——小白没有能力判断 spec 写得好不好，验收必须是可执行检验而不是读 markdown；②「任务规模不适配流程重量」是高频抱怨——**必须有小任务旁路**。

## f) 形态与安装门槛

**第一类：CLI 工具 + 模板生成器（门槛高）**：spec-kit 要 Python 3.11+/uv；BMAD 要 Node v20+ 和 Python 3.10+ 双运行时；OpenSpec 要 npm 全局安装。三者最终都在 Claude Code 里变成 Skill 文件，但**都需要先在终端跑独立 CLI 生成**——对小白是第一道劝退墙。

**第二类：纯 Skill/插件（近零门槛）**：superpowers 一条 `/plugin install`；zip 解压进 `.claude/skills/` 的先例存在但未确认成熟度。

## ⚠️ 关于「单个 skill 引导全流程」的直接先例

**三个目标框架没有一个是单文件 SKILL.md 走完全流程的**——全部拆成「每阶段一个 skill/命令」家族。这不是偶然：

- spec-kit 源码（`src/specify_cli/integrations/claude/__init__.py`）记录了真实故障（issue #3185）：曾让部分命令在 fork 子上下文跑，但返回主对话的仍是 300-500 行报告，长会话里每次 fork 继承不断增长的上下文，**最终导致对话卡死**——最后 `FORK_CONTEXT_COMMANDS` 被显式清空。
- BMAD `bmad-help` 源码 Constraints 明确写 "**Recommend running each skill in a fresh context window**"——官方设计哲学刻意反对连续大上下文走全流程。

最接近的形态先例：⚠️ **superpowers**——物理上 ~13 个 skill 文件，但通过 SessionStart hook + 强制引导实现「用户体感单一入口、自动链式流转」，"mandatory workflows, not suggestions"。⚠️ **BMAD bmad-help 路由器**——「一个常驻 skill 负责告诉你下一步」，本身不执行内容生成。

**判断**：不存在「一个巨型 prompt 端到端管完」的成熟先例——三个严肃项目都在实践中主动放弃了这个形态（长上下文污染、可维护性、错误恢复困难）。正确做法：**对外表现为一次连续对话，对内实现为职责单一的分层内容 + 编排层。**

## 值得抄的

1. `[NEEDS CLARIFICATION]` 显式标记 + 清零门禁（spec-kit）
2. 一次只问一个问题、答案立刻写回文档（spec-kit /clarify）
3. 状态路由 skill：随时可问「我在哪、下一步干嘛」（BMAD bmad-help）
4. story 文件分区写权限（BMAD）——「自主循环能写什么」用文件区块级规则锁死
5. delta spec + 小任务快速通道（OpenSpec + BMAD quick-dev）

## 必须避开的

1. 文档量与代码量失衡（设硬性篇幅上限）
2. 一刀切流程不论任务大小（必须有前置规模判断 + 旁路）
3. 看起来完整实则空洞的生成物（验收必须可执行，不能让小白读 markdown 判断对不对）
4. 升级/重生成覆盖用户自定义内容
5. 「表面隔离实际污染主对话」的 subagent 用法（spec-kit issue #3185 工程级教训）

## 来源

spec-kit：README / spec-driven.md / issue #2181 / 源码 integrations/claude ｜ BMAD：GitHub + docs.bmad-method.org + 源码 core-skills ｜ OpenSpec：concepts.md / getting-started.md ｜ superpowers：github.com/obra/superpowers ｜ 评测：Scott Logic / ranthebuilder / martinfowler.com / LPains / Marmelab

**未完整核实项**：spec-kit constitution 模板当前路径（404，内容来自间接来源）；claudeskills.info 4-skill SDD 链背后仓库；GSD 完整安装步骤。
