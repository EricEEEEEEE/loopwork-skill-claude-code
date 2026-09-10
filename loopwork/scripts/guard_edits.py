#!/usr/bin/env python3
"""围栏 · 文件编辑守卫（PreToolUse: Edit|Write|MultiEdit|NotebookEdit）——薄适配层。

判定规则住在 guard_rules.py（两版共用）。这里只负责平台那一半：
取出落点路径（NotebookEdit 传的是 notebook_path）→ 符号链接按 realpath 还原真身 →
算成项目内相对路径 → 交给 guard_rules.check_edit 判 → 命中 exit 2，stderr 喂回模型。

被锁的东西：任何时候的 .loopwork/hooks/**、.loopwork/state.json、批次 flag、钩子接线；
JOURNAL.md 只许追加；phase == implementing 时再锁上 tests/**、spec.md、rules.md。
非 loopwork 项目 / 内部异常：放行（fail-open，围栏自身故障不砖会话）。
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import guard_rules
except Exception:  # 共享库不在（旧项目没重跑 init）——放行但吭一声
    guard_rules = None
try:
    import guard_log
except Exception:  # 取证账本是加分项，不在也照拦
    guard_log = None

EXTRA_PROTECTED = [".claude/settings.json", ".claude/settings.local.json"]


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
        root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        state_p = os.path.join(root, ".loopwork", "state.json")
        if not os.path.exists(state_p):
            return 0  # 非 loopwork 项目
        ti = payload.get("tool_input") or {}
        fp = ti.get("file_path") or ti.get("notebook_path") or ""
        if not fp:
            return 0
        ap = os.path.realpath(fp if os.path.isabs(fp) else os.path.join(root, fp))
        rel = os.path.relpath(ap, os.path.realpath(root))
        with open(state_p, encoding="utf-8") as f:
            phase = str(json.load(f).get("phase", ""))
        verdict = guard_rules.check_edit(rel, phase=phase, extra_protected=EXTRA_PROTECTED)
        if verdict:
            if guard_log is not None:
                tool = str(payload.get("tool_name") or "Edit")
                guard_log.record(root, tool=tool, target=rel, rule=verdict[0], phase=phase)
            print(f"[围栏] {verdict[1]}", file=sys.stderr)
            return 2
        return 0
    except Exception:
        return 0  # 围栏自身故障不砖会话

if __name__ == "__main__":
    sys.exit(main())
