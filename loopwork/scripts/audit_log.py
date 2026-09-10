#!/usr/bin/env python3
"""围栏 · 审计账本（PostToolUse：只记录，不拦截——拦截是 PreToolUse 和 Stop 钩子的事）。
每次工具调用追加一行 JSONL 到 .loopwork/logs/audit.jsonl：谁、什么时候、动了什么。
出事之后要能倒查「这一步到底是怎么发生的」，靠的就是这本账。fail-open：本身出错绝不挡路。"""
import datetime, json, os, sys

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        if not os.path.isdir(os.path.join(root, ".loopwork")):
            return 0
        logdir = os.path.join(root, ".loopwork", "logs")
        os.makedirs(logdir, exist_ok=True)
        ti = payload.get("tool_input") or {}
        # CC 各工具的落点字段名不同：Bash 是 command，编辑类是 file_path，
        # NotebookEdit 是 notebook_path，检索类是 pattern——挨个兜住。
        summary = (ti.get("command") or ti.get("file_path") or ti.get("notebook_path")
                   or ti.get("path") or ti.get("pattern") or "")
        rec = {
            "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "tool": payload.get("tool_name", "?"),
            "summary": str(summary)[:200],
        }
        path = os.path.join(logdir, "audit.jsonl")
        # 单代轮转：超 5MB 把老账本顶成 .1（审计要能追溯，但不能无限吃盘）
        try:
            if os.path.getsize(path) > 5 * 1024 * 1024:
                os.replace(path, path + ".1")
        except OSError:
            pass
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return 0
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
