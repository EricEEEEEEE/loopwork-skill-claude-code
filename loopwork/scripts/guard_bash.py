#!/usr/bin/env python3
"""围栏 · Bash 守卫（PreToolUse: Bash）。

堵三个洞：
1. 小白安全净化：rm -rf（短/长旗标、sudo 前缀一视同仁）/ git push --force|-f|+refspec /
   git reset --hard / chmod 777 一律拦下（改为问用户）；
2. 绕道写文件：Edit 被拦后用 sed -i / tee / 重定向 / mv / cp 改保护文件——同样拦（头号绕过手法）；
3. 实现期 git 回滚考题：checkout/restore 指向保护路径、apply/revert 目标不可见——同样拦（二号绕过手法）。
非 loopwork 项目仅执行第 1 类净化；内部异常放行（fail-open）。
"""
import json, os, re, sys

DANGEROUS = [
    (r"\bgit\s+push\s+.*--force", "git push --force 被围栏拦下：会抹掉远端历史，必须用户亲自决定。"),
    (r"\bgit\s+push\s+(?:\S+\s+)*-[a-zA-Z]*f\b", "git push -f 被围栏拦下：等于 --force，会抹掉远端历史，必须用户亲自决定。"),
    (r"\bgit\s+push\s+[^;|&]*\s\+\S", "git push +refspec 被围栏拦下：加号写法等于强推，必须用户亲自决定。"),
    (r"\bgit\s+reset\s+.*--hard", "git reset --hard 被围栏拦下：会丢弃未存档的工作，必须先问用户（用户同意后可由用户亲手执行）。"),
    (r"\bchmod\s+777\b", "chmod 777 被围栏拦下：不做全开权限。"),
]

def dangerous_rm(cmd):
    """rm 同时带 r 和 f 旗标即危险：合写(-rf/-fr)、分写(-r -f)、长写(--recursive --force)一视同仁。"""
    for seg in re.split(r"[;|&]+", cmd):
        m = re.search(r"\brm\b(.*)", seg)
        if not m:
            continue
        args = m.group(1)
        flags = "".join(re.findall(r"(?:^|\s)-([a-zA-Z]+)", args)).lower()
        longs = set(re.findall(r"(?:^|\s)--([a-z-]+)", args.lower()))
        if ("r" in flags or "recursive" in longs) and ("f" in flags or "force" in longs):
            return True
    return False


def write_target_hit(cmd, targets):
    """只有当写动作『指向』保护路径才算命中——提到路径不算（跑考题 pytest tests/ 必须放行）。
    大小写不敏感比对（macOS 文件系统默认不区分）。返回命中的保护路径，未命中返回 None。"""
    # 1) 重定向落点：> 或 >> 后面的那个 token
    for m in re.finditer(r">>?\s*([^\s;|&<>]+)", cmd):
        tok = m.group(1).lower()
        for t in targets:
            if t in tok:
                return t
    # 2) 写型命令的参数区：按管道/分号切段，段内 sed -i / tee / mv / cp / truncate 之后的参数
    for seg in re.split(r"[;|&]+", cmd):
        m = re.search(r"\b(sed\s+-i\S*|tee(?:\s+-a)?|mv|cp|truncate)\b(.*)", seg)
        if m:
            args = m.group(2).lower()
            for t in targets:
                if t in args:
                    return t
    return None


def git_rewrite_hit(cmd, protected):
    """实现期二号绕道：用 git 改写考题内容而不经过编辑工具。
    checkout/restore 带保护路径 = 把考题回滚成旧版本；apply/revert 的落点从命令行根本看不见。
    命中返回 (子命令, 白话原因)；未命中返回 None。"""
    for seg in re.split(r"[;|&]+", cmd):
        m = re.search(r"\bgit\s+(checkout|restore)\b(.*)", seg)
        if m and any(t in m.group(2).lower() for t in protected):
            return (m.group(1), "指向考题/规格路径")
        m = re.search(r"\bgit\s+(apply|revert)\b", seg)
        if m:
            return (m.group(1), "补丁/回滚会改哪些文件，围栏从命令行看不见")
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
            g = git_rewrite_hit(cmd, protected_impl)
            if g:
                print(
                    f"[围栏] 拦截：实现期不许用 git {g[0]} 改写考题/历史（{g[1]}）。"
                    "红考题只能靠写实现变绿；确需回滚或打补丁，停下来向用户说明并征得同意。",
                    file=sys.stderr,
                )
                return 2
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
