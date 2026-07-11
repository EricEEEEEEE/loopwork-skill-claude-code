# 调研报告 D · 小白引导型产品与 Skill UX 先例

> 调研日期：2026-07-11 ｜ 调研范围：GitHub awesome 清单×4、anthropics/skills 官方仓库、obra/superpowers、BMAD-METHOD、davila7/claude-code-templates、多篇小白向教程、Lovable/Bolt/Replit 拆解。

---

## 总结论

**没有找到「小白拖入即用、从头到尾引导完成整个项目」的 Claude Code skill 直接先例。** 「小白友好的引导式产品」（Lovable 系）和「Claude Code 里的多阶段引导 skill」（doc-coauthoring/brainstorming/BMAD）是两条没有交汇过的线。要做的东西卡在交汇点上，是空位，不是抄改。

## a) 引导式 skill 的组织模式

- **doc-coauthoring**（官方）：三阶段硬编码于 SKILL.md（Context Gathering → Refinement & Structure → Reader Testing），每阶段有 "Trigger conditions" 和 "Instructions to user"。每 section 走五步子循环：提 5-10 个编号问题 → brainstorm 选项 → 用户 keep/remove/combine → gap check → 起草迭代，「连续 3 轮无实质改动」触发收敛。**无独立状态文件**——正在写的文档本身就是状态。收尾用**无上下文的全新子实例**当「读者」验证（可复用的质检模式）。
- **brainstorming**（obra/superpowers-skills）："Ask ONE question at a time"、"prefer multiple-choice formats"；方案分节展示（每节 200-300 字）+ 节后 "Does this look right so far?" 验证闸门；**任何肯定性回应即可推进**；允许非线性回退（"Don't force forward linearly"）；每次切阶段显式广播「我正在用 XX skill 的第 X 步」。
- **BMAD**：入口 `bmad-help` 自动检查项目处于哪个阶段，**主动**给「接下来该做什么」；`sprint-status.yaml` 持久状态文件跨 session 记录（最接近「进度条落地文件」的先例）；每个 workflow 结束自动再跑一次 bmad-help，形成「完成一步→自动被告知下一步」闭环。
- **Claude Code onboarding 流程（社区拆解）**：AskUserQuestion 四阶段——强制三问（逐个问）→ 条件性追问 → 查预置索引表生成个性化路线 → 「深入/下一个/跳过/重来」节奏控制。
- **反面参照**：claude-code-templates 是「组件选择器+一键安装」的装配式向导，假设用户懂 npm/CLI。**装配式向导 vs 对话式引导是两种范式**，小白产品是后者。
- **Lovable Plan Mode**：写代码前把完整计划（schema、组件、认证、部署）摊开，用户批准才开始生成。

## b) 小白最常卡住的环节清单

- **终端恐惧**——「黑窗口」是头号劝退原因；Windows 再加一层 WSL 摩擦；
- **黑话墙**——"agentic"、"subagent" 第一眼劝退；
- **权限弹窗看不懂在批准什么**——本能不安，习惯去 Google 确认「这不会搞坏什么」；
- **模糊指令才是真瓶颈，不是语法**——"Your bottleneck will never be syntax; it will be vague verbs"（真实事故：一句 "clean up" 误删 11GB）；
- **不知道对话有上下文上限**——一个 session 塞多个不相关任务，质量越来越差，不知道何时开新对话；
- **部署断层**——「代码写完」到「有个能给别人看的网址」之间：开什么账号、跑什么命令、URL 在哪；
- **反馈太模糊**——说 "It's bad" 而不是「按钮在手机上太小」，修复陷入无效循环；
- **API key 泄露的隐形渠道**——粘进 prompt、被读的 .env、verbose 日志、自动备份；
- **花钱失控**——一次 timeout 的 naive retry 90 秒打出 340 个请求；无上限 session 一夜烧光额度；
- **「什么时候该找专业的人」门槛焦虑**；
- **没有能力判断代码对不对**——只能靠「点一遍看能不能用」的功能性测试。

## c) 好的提问设计

- **平台硬约束（AskUserQuestion）**：每次最多 4 问、每问 2-4 选项、自动带 "Other" 兜底、推荐项放第一并标注 "(Recommended)"、header ≤12 字符——顺着这个格式设计，不自己发明问答 UI。
- **一次几个**：不确定答案时一次一个（brainstorming）；收集已知信息时可批量编号提问并允许简写批量作答（doc-coauthoring："1: yes, 2: see #channel..."）。
- **选择 vs 开放**：选的时候用选择题，说理由用开放题，分工而非二选一。
- **必须给「不确定」出口**："Always give Claude a place to put its uncertainty. Without one, it guesses"——反过来对用户同理：选项要留「不知道/你决定」。

## d) 「下一步是什么」的呈现

- 编号 checkpoint + 每步时间预估 + **把部署成功设计成庆祝时刻**（"🎉 你造出了第一个 app"）——心理里程碑代替无感长任务；
- 完成一步**自动**推下一步（BMAD bmad-help 闭环），不依赖用户主动问；
- 持久状态文件当进度条（sprint-status.yaml）；
- 产物链接即状态（doc-coauthoring 每次编辑甩 artifact 链接）；
- 先摊开完整计划再动手（Lovable Plan Mode）；
- 系统状态透明化（statusline）缓解黑箱恐惧。

## e) 安全兜底

- 权限分级、渐进式放权（默认每次改动批准，建立信任后升级）；
- 强制沙箱：只从目标文件夹启动，不从 home 启动；
- 备份/版本控制先行："Keep backups of anything you would cry about"；
- 「不要删除」写成配置层硬规则，不靠每次提醒；
- **高风险操作平台自动管理、对用户隐藏**（Base44：认证/后端/数据权限/密钥全自动，用户看不到也就配不错）；
- 花钱系统级硬上限（circuit breaker 监控消耗速率超阈值自动暂停；预算硬开关）；
- 上线前人工把关硬边界：真实用户上线前 code review + 部署审计；支付/个人数据/医疗信息必须专业实现；
- 多文件改动前先要 plan（"Show me the plan before changing more than one file"）。

## f) 哪些事被证明不该让小白自己做

- 认证系统、后端基础设施、密钥管理（平台自动化并从 UI 隐藏）；
- 生产部署的最终安全判断（要专业角色把关）；
- 花费控制（系统硬限额，不靠用户盯用量表）；
- 一次性精确描述整个系统（工具应主动拆小，不纵容大而全 prompt）；
- 读代码判断对错（用可视化/功能性验证代替 diff 审查）。

## 直接先例排查（为何无 ⚠️）

| 候选 | 为什么不算 |
|---|---|
| doc-coauthoring（官方） | 引导对象是文档不是软件项目，机制可借鉴、领域不对口 |
| brainstorming（superpowers） | 只到设计定稿，整体面向工程师（"engineering-grade development"） |
| vlad-ko/claude-wizard | 明确面向资深工程师/架构师，与小白引导反方向 |
| BMAD-METHOD | 多 agent 框架非单 skill；用户实测反馈「仍需基本技术概念，不懂代码很难用好」 |
| Lovable / Bolt / Replit Agent | 定位准确但是独立付费 Web 产品，不是 Claude Code 载体，只能借鉴 UX |

## 值得抄的

1. AskUserQuestion 的「选择题优先 + Other 兜底 + 推荐项排第一」
2. brainstorming 的「一次一问 + 200-300 字小节 + 节后确认」验证闸门
3. BMAD 的「每阶段结束自动给下一步 + 持久状态文件」
4. 「编号 checkpoint + 时间预估 + 部署庆祝时刻」
5. Lovable Plan Mode 的「先出计划、批准了再动手」

## 必须避开的

1. 黑话不解释（首现必带白话注解，能不提就不提）
2. 假设小白会自己管理会话/上下文（skill 要主动提示或处理）
3. 把密钥/部署/认证混在普通流程里（要么自动化隐藏，要么单独标风险逐项确认）
4. 无上限自动化不可逆/花钱动作（「帮小白省心」≠「替小白拍板」）
5. 纯开放式问答（选择题为主 + 自由文本兜底）

## 关键来源

anthropics/skills（18 个官方 skill 均无小白向全流程引导）｜ doc-coauthoring / brainstorming SKILL.md ｜ BMAD docs ｜ vlad-ko/claude-wizard ｜ davila7/claude-code-templates ｜ lovable.dev/guides ｜ michaelcrist.substack.com ｜ ccforeveryone.com ｜ claude-world.com first-app-tutorial ｜ lowcode.agency ｜ base44.com/blog/common-vibe-coding-mistakes ｜ platform.claude.com AskUserQuestion 规格 ｜ 四个 awesome 清单（karanb192 / travisvn / ComposioHQ / hesreallyhim）
