#!/usr/bin/env python3
"""围栏 · Bash 守卫（PreToolUse: Bash）。

堵两个洞：
1. 小白安全净化：rm -rf / git push --force / git reset --hard / chmod 777 一律拦下（改为问用户）；
2. 绕道写文件：Edit 被拦后用 sed -i / tee / 重定向 / mv / cp 改保护文件——同样拦（已知的头号绕过手法）。
非 loopwork 项目仅执行第 1 类净化；内部异常放行（fail-open）。
"""
import json, os, re, sys

DANGEROUS = [
    (r"\bgit\s+push\s+.*--force", "git push --force 被围栏拦下：会抹掉远端历史，必须用户亲自决定。"),
    (r"\bgit\s+reset\s+.*--hard", "git reset --hard 被围栏拦下：会丢弃未存档的工作，必须先问用户（用户同意后可由用户亲手执行）。"),
    (r"\bchmod\s+777\b", "chmod 777 被围栏拦下：不做全开权限。"),
]

def dangerous_rm(cmd):
    """rm 同时带 r 和 f 旗标即危险，无论旗标合写(-rf/-fr)还是分写(-r -f)。"""
    for seg in re.split(r"[;|&]+", cmd):
        m = re.search(r"\brm\b(.*)", seg)
        if not m:
            continue
        flags = "".join(re.findall(r"(?:^|\s)-([a-zA-Z]+)", m.group(1))).lower()
        if "r" in flags and "f" in flags:
            return True
    return False


def write_target_hit(cmd, targets):
    """只有当写动作『指向』保护路径才算命中——提到路径不算（跑考题 pytest tests/ 必须放行）。
    返回命中的保护路径，未命中返回 None。"""
    # 1) 重定向落点：> 或 >> 后面的那个 token
    for m in re.finditer(r">>?\s*([^\s;|&<>]+)", cmd):
        tok = m.group(1)
        for t in targets:
            if t in tok:
                return t
    # 2) 写型命令的参数区：按管道/分号切段，段内 sed -i / tee / mv / cp / truncate 之后的参数
    for seg in re.split(r"[;|&]+", cmd):
        m = re.search(r"\b(sed\s+-i\S*|tee(?:\s+-a)?|mv|cp|truncate)\b(.*)", seg)
        if m:
            args = m.group(2)
            for t in targets:
                if t in args:
                    return t
    return None

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        cmd = (payload.get("tool_input") or {}).get("command") or ""
        if dangerous_rm(cmd):
            print("[围栏] rm -rf 类命令被围栏拦下：删除动作必须先问用户，并改用精确路径删除。", file=sys.stderr)
            return 2
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
        hit = write_target_hit(cmd, targets)
        if hit:
            print(
                f"[围栏] 拦截：这条命令在用 shell 改写保护文件（{hit}）。"
                "保护文件不许绕道修改——需要改就向用户说明并走正规流程。",
                file=sys.stderr,
            )
            return 2
        return 0
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
