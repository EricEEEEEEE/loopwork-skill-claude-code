#!/usr/bin/env python3
"""围栏 · Bash 守卫（PreToolUse: Bash）——薄适配层。

判定规则全部住在 guard_rules.py（两版逐字节相同的共享库）。这里只做四件事：
解析 Claude Code 的 payload → 找项目根 → 读当前相位 → 命中就 exit 2，把白话理由喂回模型。

它拦的五类（前四类的规则本体见 guard_rules.py）：
1. 小白安全净化：rm -rf / git push --force / chmod 777；
2. 改历史、销毁证据：amend / rebase / filter-branch / stash / clean / reset 搬指针……；
3. 绕道写文件：sed -i / tee / 重定向 / mv / cp / rm 指向保护文件（Edit 被拦后的头号绕过手法）；
4. 实现期用 git checkout/restore/apply/revert 回滚考题（二号绕过手法）；
5. 存档闸（先红后绿）：实现期的 git commit 要带实现物，就必须先有一张红票——
   见下面 red_ticket()。这一类要读 git，所以住在适配层，不进纯函数的 guard_rules.py。
非 loopwork 项目只执行第 1、2 类；内部异常放行（fail-open，围栏自身故障不砖会话）。
"""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import guard_rules
except Exception:  # 共享库不在（旧项目没重跑 init）——放行但吭一声，别默默变纸老虎
    guard_rules = None
try:
    import guard_log
except Exception:  # 取证账本是加分项，不在也照拦
    guard_log = None

# Claude Code 专属的接线文件：改它等于把钩子拆了。平台差异不进共享规则。
EXTRA_PROTECTED = [".claude/settings.json", ".claude/settings.local.json"]

TICKET_SCAN = 30   # 往回翻多少个存档找红票：一圈红绿只隔几档，翻 30 个绰绰有余


def sh(args, root):
    try:
        p = subprocess.run(args, cwd=root, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20)
        return p.returncode, p.stdout
    except Exception:
        return 1, ""


def will_stage(cmd):
    """命令行自己还会往暂存区里塞什么。返回 (整个脏工作区?, 点名的路径前缀)。
    PreToolUse 跑在 git add 之前——`git add -A && git commit` 这种连写，
    此刻看暂存区是空的，只能从命令行本身看出它待会儿要装什么。
    `git add tests/` 这类点名的写法只算那几个落点，不能一律当成「全都要」。"""
    wide, paths = False, []
    for sub, args in guard_rules.git_calls(cmd):
        if sub == "add":
            named = [a for a in args if not a.startswith("-")]
            if not named or any(p in (".", "./", "*", ":/") for p in named):
                wide = True
            else:
                paths += named
        elif sub == "commit":
            for a in args:
                if a == "--all" or re.fullmatch(r"-[a-zA-Z]*a[a-zA-Z]*", a):
                    wide = True
    return wide, paths


def dirty_files(root):
    """工作区里所有还没存档的路径（仓库根相对）。读不出来返回 []。
    -z：文件名里有空格/引号时 porcelain 的引号转义会把路径读歪。
    -uall：默认会把整个未跟踪目录折成一行 `src/`，里头的文件就看不见了。"""
    code, out = sh(["git", "status", "--porcelain", "-z", "-uall"], root)
    if code != 0:
        return []
    items, i, files = [x for x in out.split("\0") if x], 0, []
    while i < len(items):
        it = items[i]
        i += 1
        if len(it) < 4:
            continue
        files.append(it[3:])
        if it[0] in ("R", "C") and i < len(items):  # 改名/复制：原路径在下一段
            files.append(items[i])
            i += 1
    return files


def commit_payload(root, cmd):
    """这次 git commit 会带上哪些文件（仓库根相对）。读不出来返回 []（读不出就不判）。"""
    code, out = sh(["git", "diff", "--cached", "--name-only", "-z"], root)
    files = [x for x in out.split("\0") if x] if code == 0 else []
    wide, paths = will_stage(cmd)
    if wide or paths:
        dirty = dirty_files(root)
        files += dirty if wide else [
            f for f in dirty
            if any(f == p or f.startswith(p.rstrip("/") + "/") for p in paths)]
    return sorted(set(files))


def red_ticket(root):
    """手里有没有红票：从 HEAD 往回翻，在撞上「上一次带实现物的存档」之前，
    是否存在一档只有考题（+台账）的存档。有 = 这一轮先红过了，绿存档可以落。
    不存钩子里的开关，直接读历史：PreToolUse 看不见 commit 到底成没成，
    存出来的开关会被一次故意失败的 commit 白白骗走一张票；历史骗不了。"""
    code, out = sh(["git", "log", "-n", str(TICKET_SCAN), "--format=%x00", "--name-only"], root)
    if code != 0:
        return True          # 历史读不出来就不拦（fail-open，围栏故障不砖会话）
    for chunk in out.split("\0")[1:]:
        files = [ln for ln in chunk.splitlines() if ln.strip()]
        if not files:
            continue         # 空档/合并档：什么都不说明，继续往回翻
        if guard_rules.impl_files(files):
            return False     # 撞上上一次绿存档了，中间没红过
        if any(f.startswith("tests/") for f in files):
            return True      # 只有考题的一档 —— 红票在手
    return False


def archive_gate(root, cmd, phase):
    """存档闸：实现期落绿存档必须先有红票。命中返回 (rule, 白话理由)，干净返回 None。

    只管实现期。Stage 0–3 与循环模式的登记档都跑在 test-writing 相位上，
    那些档天生带规格/计划这类实现物，闸门在那里开着——先红后绿约束的是写代码的那一圈。"""
    if phase != "implementing":
        return None
    if not any(sub == "commit" for sub, _ in guard_rules.git_calls(cmd)):
        return None
    files = commit_payload(root, cmd)
    if not files or not guard_rules.impl_files(files):
        return None          # 空档 / 只有考题和台账：不是绿存档，不归这道闸管
    if red_ticket(root):
        return None
    return ("green-without-red",
            "拦截：这一档要带实现代码进去，但上一次绿存档之后没有过红存档。"
            "考题先红后绿——先写会失败的考题、亲眼跑红、单独存一档（那一档里只许有 "
            "tests/ 和 tasks.md / JOURNAL.md / 状态文件），再回来存这一档实现。"
            "确实是没有考题的活（纯文档/配置），把它写进 BLOCKED.md 交用户拍板，不要从这里绕。")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if guard_rules is None:
        print("[围栏] ⚠️ 判定核心 guard_rules.py 不在 .loopwork/hooks/，本次未做检查。"
              "请重跑 init_project.sh 补齐围栏。", file=sys.stderr)
        return 0
    try:
        cmd = (payload.get("tool_input") or {}).get("command") or ""
        root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        state_p = os.path.join(root, ".loopwork", "state.json")
        phase, in_project = "", os.path.exists(state_p)
        if in_project:
            with open(state_p, encoding="utf-8") as f:
                phase = str(json.load(f).get("phase", ""))
        verdict = guard_rules.check_bash(cmd, phase=phase, in_project=in_project,
                                         extra_protected=EXTRA_PROTECTED)
        if verdict is None and in_project:
            verdict = archive_gate(root, cmd, phase)
        if verdict:
            if guard_log is not None:
                guard_log.record(root, tool="Bash", target=cmd, rule=verdict[0], phase=phase)
            print(f"[围栏] {verdict[1]}", file=sys.stderr)
            return 2
        return 0
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
