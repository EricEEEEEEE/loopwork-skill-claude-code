#!/usr/bin/env python3
"""围栏 · 文件编辑守卫（PreToolUse: Edit|Write|MultiEdit|NotebookEdit）。

规则：
- 任何时候：不许直接编辑 .loopwork/hooks/**、.loopwork/state.json（围栏保护自己；状态走 progress.py）
- phase == implementing（写实现期间）：锁死 tests/**、spec.md、rules.md（考题写好后不许改）
- 路径判定抗绕过：符号链接按 realpath 还原真身；大小写不敏感文件系统（macOS 默认）按 casefold 比对
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
        ti = payload.get("tool_input") or {}
        fp = ti.get("file_path") or ti.get("notebook_path") or ""  # NotebookEdit 传的是 notebook_path
        if not fp:
            return 0
        real_root = os.path.realpath(root)
        ap = os.path.realpath(fp if os.path.isabs(fp) else os.path.join(root, fp))
        rel = os.path.relpath(ap, real_root)
        if rel.startswith(".."):
            print("[围栏] 拦截：不许改项目文件夹之外的文件。需要的话请先问用户。", file=sys.stderr)
            return 2
        rel_cf = rel.casefold()
        # 永久保护：围栏与状态
        if rel_cf.startswith(os.path.join(".loopwork", "hooks").casefold()) or rel_cf == os.path.join(".loopwork", "state.json").casefold():
            print(f"[围栏] 拦截：{rel} 受保护。围栏脚本不许改；状态请用 progress.py 更新。", file=sys.stderr)
            return 2
        with open(state_p, encoding="utf-8") as f:
            st = json.load(f)
        if str(st.get("phase", "")) == "implementing":
            if rel_cf.startswith(("tests" + os.sep).casefold()) or rel_cf in ("spec.md", "rules.md"):
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
