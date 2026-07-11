#!/usr/bin/env python3
"""围栏 · Bash 守卫（PreToolUse: Bash）。

堵两个洞：
1. 小白安全净化：rm -rf / git push --force / git reset --hard / chmod 777 一律拦下（改为问用户）；
2. 绕道写文件：Edit 被拦后用 sed -i / tee / 重定向 / mv / cp 改保护文件——同样拦（已知的头号绕过手法）。
非 loopwork 项目仅执行第 1 类净化；内部异常放行（fail-open）。
"""
import json, os, re, sys

DANGEROUS = [
    (r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*[rR][a-zA-Z]*)\b",
     "rm -rf 类命令被围栏拦下：删除动作必须先问用户，并改用精确路径删除。"),
    (r"\bgit\s+push\s+.*--force", "git push --force 被围栏拦下：会抹掉远端历史，必须用户亲自决定。"),
    (r"\bgit\s+reset\s+.*--hard", "git reset --hard 被围栏拦下：会丢弃未存档的工作，必须先问用户。"),
    (r"\bchmod\s+777\b", "chmod 777 被围栏拦下：不做全开权限。"),
]
WRITE_HINTS = [r">\s*", r">>\s*", r"\bsed\s+-i\b", r"\btee\b", r"\bmv\b", r"\bcp\b", r"\btruncate\b"]

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        cmd = (payload.get("tool_input") or {}).get("command") or ""
        for pat, msg in DANGEROUS:
            if re.search(pat, cmd):
                print(f"[围栏] {msg}", file=sys.stderr)
                return 2
        root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        state_p = os.path.join(root, ".loopwork", "state.json")
        if not os.path.exists(state_p):
            return 0
        protected_always = [".loopwork/hooks", ".loopwork/state.json"]
        protected_impl = ["tests/", "spec.md", "rules.md"]
        with open(state_p, encoding="utf-8") as f:
            st = json.load(f)
        targets = list(protected_always)
        if str(st.get("phase", "")) == "implementing":
            targets += protected_impl
        has_write = any(re.search(w, cmd) for w in WRITE_HINTS)
        if has_write:
            for t in targets:
                if t in cmd:
                    print(
                        f"[围栏] 拦截：这条命令看起来在用 shell 改写保护文件（{t}）。"
                        "保护文件不许绕道修改——需要改就向用户说明并走正规流程。",
                        file=sys.stderr,
                    )
                    return 2
        return 0
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
