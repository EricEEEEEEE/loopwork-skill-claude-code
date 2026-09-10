#!/usr/bin/env python3
"""围栏 · Bash 守卫（PreToolUse: Bash）。

堵四个洞：
1. 小白安全净化：rm -rf（短/长旗标、sudo 前缀一视同仁）/ git push --force|-f|+refspec /
   chmod 777 一律拦下（改为问用户）；
2. 改历史 / 销毁证据：amend / rebase / filter-branch / update-ref / stash / clean /
   reflog expire / gc --prune / branch -f|-D / reset（搬指针形态）/ switch --discard-changes /
   push --delete 一律拦下——存档只增不减，改得动的历史不算证据；
3. 绕道写文件：Edit 被拦后用 sed -i / tee / 重定向 / mv / cp 改保护文件——同样拦（头号绕过手法）；
4. 实现期 git 回滚考题：checkout/restore 指向保护路径、apply/revert 目标不可见——同样拦（二号绕过手法）。
非 loopwork 项目仅执行第 1、2 类净化；内部异常放行（fail-open）。
"""
import json, os, re, shlex, sys

DANGEROUS = [
    (r"\bgit\s+push\s+.*--force", "git push --force 被围栏拦下：会抹掉远端历史，必须用户亲自决定。"),
    (r"\bgit\s+push\s+(?:\S+\s+)*-[a-zA-Z]*f\b", "git push -f 被围栏拦下：等于 --force，会抹掉远端历史，必须用户亲自决定。"),
    (r"\bgit\s+push\s+[^;|&]*\s\+\S", "git push +refspec 被围栏拦下：加号写法等于强推，必须用户亲自决定。"),
    (r"\bchmod\s+777\b", "chmod 777 被围栏拦下：不做全开权限。"),
]

# 分段：换行和 ; | & 一样是命令分隔符——多行脚本是最常见的绕道写法。
SEP = r"[;|&\n]+"

# git 自己的全局选项（在子命令之前），带值的要连值一起跳过。
GIT_OPT_VALUE = ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path")
RESET_MODES = ("--hard", "--soft", "--mixed", "--merge", "--keep")

# 只许追加的保护文件：>> 和 tee -a 放行，覆盖/改写/删除/搬走一律拦。
APPEND_ONLY = ["journal.md"]


def append_ok(target):
    return any(a in target for a in APPEND_ONLY)


def dangerous_rm(cmd):
    """rm 同时带 r 和 f 旗标即危险：合写(-rf/-fr)、分写(-r -f)、长写(--recursive --force)一视同仁。
    一段里可能有多个 rm（`rm a.txt` 后面跟真正危险的那条），逐个看，不能只看第一个。"""
    for seg in re.split(SEP, cmd):
        for m in re.finditer(r"\brm\b(.*)", seg):
            args = m.group(1)
            flags = "".join(re.findall(r"(?:^|\s)-([a-zA-Z]+)", args)).lower()
            longs = set(re.findall(r"(?:^|\s)--([a-z-]+)", args.lower()))
            if ("r" in flags or "recursive" in longs) and ("f" in flags or "force" in longs):
                return True
    return False


def git_calls(cmd):
    """把命令里每一处 git 调用拆成 (子命令, 参数列表)。
    只认「跳过 git 全局选项后的第一个词」这个位置当子命令——这样
    `git commit -m "clean up rebase"` 不会被提交信息里的词误伤。
    用 shlex 分词，引号里的内容整体成一个 token，旗标比对走精确相等。"""
    out = []
    for seg in re.split(SEP, cmd):
        try:
            toks = shlex.split(seg)
        except ValueError:  # 引号不成对，退回粗分词，宁可多看几个词
            toks = seg.split()
        for i, t in enumerate(toks):
            if t != "git" and not t.endswith("/git"):
                continue
            j = i + 1
            while j < len(toks):
                if toks[j] in GIT_OPT_VALUE:
                    j += 2
                elif toks[j].startswith("-"):
                    j += 1
                else:
                    break
            if j < len(toks):
                out.append((toks[j].lower(), toks[j + 1:]))
            break  # 一段里只认第一处 git 调用（后面的词是它的参数）
    return out


def reset_moves_pointer(args):
    """git reset 只放行「取消暂存」形态：git reset [HEAD] [--] <路径>。
    带模式旗标、或第一个位置参数不是 HEAD（是某个版本号/分支）→ 就是在搬分支指针。"""
    for a in args:
        if a in RESET_MODES:
            return f"{a} 会搬动分支指针并丢弃工作"
    head = args[: args.index("--")] if "--" in args else args
    pos = [a for a in head if not a.startswith("-")]
    if pos and pos[0] != "HEAD":
        return f"把分支指针搬到 {pos[0]}，中间的存档等于被抹掉"
    return None


def git_rewrite_ban(cmd):
    """改历史 / 销毁证据类 git 动作。命中返回 (动作名, 白话原因)，否则 None。
    Loopwork 的流程从不需要改历史：存档只增不减，改得动的历史不算证据。
    （用户自己在终端做这些事不经过围栏，这里只管住模型。）"""
    for sub, args in git_calls(cmd):
        flags = [a for a in args if a.startswith("-")]
        if sub == "commit" and "--amend" in flags:
            return ("git commit --amend", "改写已有存档 = 抹掉证据。要修正就再存一档，旧的留着")
        if sub in ("rebase", "filter-branch", "filter-repo", "update-ref"):
            return (f"git {sub}", "会重排或伪造 git 历史——基线存档一旦凭空消失，检测门会判定假历史并停机")
        if sub == "stash":
            return ("git stash", "把改动藏进一个不在存档里的暗格；存档才是证据，藏起来的不算")
        if sub == "clean":
            return ("git clean", "批量删除未跟踪文件，删掉的东西 git 里也找不回来——要删就点名删单个文件")
        if sub == "reflog" and any(a in ("expire", "delete") for a in args):
            return ("git reflog expire/delete", "销毁最后一层找回历史的后路")
        if sub == "gc" and any(a.startswith("--prune") for a in flags):
            return ("git gc --prune", "立刻回收悬空对象——误删的存档就真的没了")
        if sub == "branch" and ("--force" in flags or
                                any(re.fullmatch(r"-[a-zA-Z]*[fD][a-zA-Z]*", a) for a in flags)):
            return ("git branch -f/-D", "强制搬动或删除分支指针")
        if sub == "switch" and "--discard-changes" in flags:
            return ("git switch --discard-changes", "丢弃未存档的工作")
        if sub == "push" and ("--delete" in flags or "-d" in flags):
            return ("git push --delete", "删除远端分支——远端是别人也在看的东西")
        if sub == "reset":
            why = reset_moves_pointer(args)
            if why:
                return ("git reset", why)
    return None


def write_target_hit(cmd, targets):
    """只有当写动作『指向』保护路径才算命中——提到路径不算（跑考题 pytest tests/ 必须放行）。
    大小写不敏感比对（macOS 文件系统默认不区分）。返回命中的保护路径，未命中返回 None。"""
    # 1) 重定向落点：> 或 >> 后面的那个 token（只许追加的文件放行 >>，拦 >）
    for m in re.finditer(r"(>>?)\s*([^\s;|&<>]+)", cmd):
        op, tok = m.group(1), m.group(2).lower()
        for t in targets:
            if t in tok:
                if op == ">>" and append_ok(t):
                    continue
                return t
    # 2) 写型命令的参数区：按管道/分号/换行切段，每段里每个匹配都要看（不能只看第一个）。
    #    sed -i/tee/truncate 对每个文件参数都是写；mv 也算——把考题搬走等于删掉源文件。
    for seg in re.split(SEP, cmd):
        for m in re.finditer(r"\b(sed\s+-i\S*|tee(?:\s+-a\b)?|mv|truncate)\b(.*)", seg):
            verb, args = m.group(1).lower(), m.group(2).lower()
            appending = verb.startswith("tee") and "-a" in verb
            for t in targets:
                if t in args:
                    if appending and append_ok(t):
                        continue
                    return t
        # cp 只有目的地算写：从考题目录拷出去是读，必须放行。
        # 目的地通常是最后一个参数，但 -t <目录> / --target-directory=<目录> 会把它挪到前面。
        for m in re.finditer(r"\bcp\b(.*)", seg):
            raw = m.group(1).lower().split()
            dest = None
            for i, x in enumerate(raw):
                if x == "-t" and i + 1 < len(raw):
                    dest = raw[i + 1]
                elif x.startswith("--target-directory="):
                    dest = x.split("=", 1)[1]
            if dest is None:
                toks = [x for x in raw if not x.startswith("-")]
                dest = toks[-1] if toks else None
            if dest:
                for t in targets:
                    if t in dest:
                        return t
        # 3) 删也是写的一种：删掉围栏脚本/接线/批次 flag 等于把围栏关掉。
        #    普通文件的 rm 不受影响（只看参数是否落在保护清单上）。
        for m in re.finditer(r"\brm\b(.*)", seg):
            for tok in m.group(1).lower().split():
                if tok.startswith("-"):
                    continue
                for t in targets:
                    if t in tok:
                        return t
    return None


def git_rewrite_hit(cmd, protected):
    """实现期二号绕道：用 git 改写考题内容而不经过编辑工具。
    checkout/restore 带保护路径 = 把考题回滚成旧版本；apply/revert 的落点从命令行根本看不见。
    命中返回 (子命令, 白话原因)；未命中返回 None。"""
    for seg in re.split(SEP, cmd):
        for m in re.finditer(r"\bgit\s+(checkout|restore)\b(.*)", seg):
            if any(t in m.group(2).lower() for t in protected):
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
        ban = git_rewrite_ban(cmd)
        if ban:
            print(
                f"[围栏] {ban[0]} 被围栏拦下：{ban[1]}。"
                "存档只增不减——要改就往前再存一档；确实非做不可，停下来向用户说明，由他自己在终端执行。",
                file=sys.stderr,
            )
            return 2
        root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        state_p = os.path.join(root, ".loopwork", "state.json")
        if not os.path.exists(state_p):
            return 0
        # 永久保护：围栏脚本 / 状态 / 钩子接线 / 批次 flag。
        # touch 不在写型命令清单里——开批是模型的合法动作；关批只归用户和 Stop 钩子。
        protected_always = [
            ".loopwork/hooks",
            ".loopwork/state.json",
            ".loopwork/batch.flag",
            ".claude/settings.json",
            ".claude/settings.local.json",
            "journal.md",  # 只许追加：>> / tee -a 放行，覆盖改写删除全拦
        ]
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
            tail = (
                '只许追加：记一笔用 `python3 .loopwork/hooks/progress.py journal "…"`，或 `>>` / `tee -a`。'
                if append_ok(hit)
                else "保护文件不许绕道修改——需要改就向用户说明并走正规流程。"
            )
            print(f"[围栏] 拦截：这条命令在用 shell 改写或删除保护文件（{hit}）。{tail}", file=sys.stderr)
            return 2
        return 0
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
