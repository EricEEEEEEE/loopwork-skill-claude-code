#!/usr/bin/env python3
"""围栏 · 文件编辑守卫（PreToolUse: Edit|Write|MultiEdit）。

规则：
- 任何时候：不许直接编辑 .loopwork/hooks/**、.loopwork/state.json（围栏保护自己；状态走 progress.py）
- phase == implementing（写实现期间）：锁死 tests/**、spec.md、rules.md（考题写好后不许改）
- 非 loopwork 项目 / 内部异常：放行（fail-open，避免砖死会话）
被拦时 exit 2，stderr 消息会喂回给 Claude。
"""
import json, os, sys

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        state_p = os.path.join(root, ".loopwork", "state.json")
        if not os.path.exists(state_p):
            return 0  # 非 loopwork 项目
        fp = (payload.get("tool_input") or {}).get("file_path") or ""
        if not fp:
            return 0
        ap = os.path.abspath(fp if os.path.isabs(fp) else os.path.join(root, fp))
        rel = os.path.relpath(ap, root)
        if rel.startswith(".."):
            print("[围栏] 拦截：不许改项目文件夹之外的文件。需要的话请先问用户。", file=sys.stderr)
            return 2
        # 永久保护：围栏与状态
        if rel.startswith(os.path.join(".loopwork", "hooks")) or rel == os.path.join(".loopwork", "state.json"):
            print(f"[围栏] 拦截：{rel} 受保护。围栏脚本不许改；状态请用 progress.py 更新。", file=sys.stderr)
            return 2
        with open(state_p, encoding="utf-8") as f:
            st = json.load(f)
        if str(st.get("phase", "")) == "implementing":
            protected = ("tests" + os.sep, "spec.md", "rules.md")
            if rel.startswith(protected[0]) or rel in protected[1:]:
                print(
                    f"[围栏] 拦截：现在是实现阶段，{rel} 已锁定（考题先红后绿，写实现期间不许改考题/规格/规矩）。"
                    "确需修改：停下来，向用户说明理由并征得明确同意。",
                    file=sys.stderr,
                )
                return 2
        return 0
    except Exception:
        return 0  # 围栏自身故障不砖会话

if __name__ == "__main__":
    sys.exit(main())
