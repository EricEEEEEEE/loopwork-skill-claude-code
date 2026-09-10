#!/usr/bin/env python3
"""围栏 · 检测门 + 挂机批模式（Stop 钩子）。外部计数器在这里，不靠模型自数。

顺序：
1. 检测门（快检，永远执行，与批模式无关）：
   a. 基线锚定：state.last_round_commit 必须仍在 git 历史中可达（防 amend/rebase 假历史）；
   b. 相位纪律：phase==implementing 时，受保护文件（tests/ .loopwork/hooks/ spec.md rules.md）
      分两段核对——未存档改动（工作区/未跟踪）→ 顶回要求撤销；已存档改动（基线..HEAD）→
      多半是红考题存档后忘了推进基线（协议：存档即推进基线，见 SKILL.md 铁律 8），
      顶回教它补 progress.py set last_round_commit；
   c. JOURNAL.md 只增不减：删行 = 抹掉证据（编辑/shell 两条路已被 PreToolUse 拦住，
      这里堵的是 git checkout <旧版本> -- JOURNAL.md 这类绕道）；
   d. 审计账本 .loopwork/logs/audit.jsonl 只增不减：字节数变短且不是单代轮转 = 有人抹账。
      抹掉的账模型补不回来，所以只响一次（报完重置基准），不把会话钉死在死循环里。
2. 挂机批模式（.loopwork/batch.flag 存在时）：
   - .loopwork/batch.flag 存 "起点轮数,上次顶回轮数,无进展次数,顶回总数,进展指纹"
     （兼容旧版四段/纯数字 = 起点轮数；空 flag 首次遇到时自动写入）
   - 本批做满 batch_size 条 → 摘 flag 并顶回一次：去验收（不许跳过检查点）
   - 只剩受阻任务（〔卡·…〕）→ 摘 flag 并顶回一次：汇总 + 请用户清问题本
   - 轮数达 round_cap → 摘 flag，安全停机汇总
   - 连续 MAX_STALLS 次「一点进展都没有」→ 判定原地打转，摘 flag 并要求停批汇报。
     无进展 = 轮数没涨 ∧ HEAD 没动 ∧ tasks.md 没动 ∧ BLOCKED.md 没动（见 progress_sig）
   - 还有可做任务且未满批 → 顶回继续

顶回总数（MAX_BLOCKS）是检测门和批模式**共用**的一个计数：平台对连续 Stop 顶回有硬上限
（CLAUDE_CODE_STOP_HOOK_BLOCK_CAP，默认 8），触顶会被强制放行、flag 残留在盘上、批承诺
无声作废。所以两条路的顶回都记同一笔账，第 MAX_BLOCKS 次转优雅停机，并在 state 里留一个
「下一轮必须放行一次」的记号——把平台那串连续计数掐断，永不触顶。
批模式的账记在 flag 第 4 段，非批模式的记在 state.stop_blocks。

非 loopwork 项目 / git 异常 / 内部异常：放行（fail-open，不砖会话）。
输出协议：顶回 = exit 2 + stderr 理由；放行 = exit 0。
"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import guard_log    # 拦截取证账本（两版共享）
except Exception:
    guard_log = None
try:
    import guard_rules  # 停滞判定的证据面清单（两版共享）
except Exception:
    guard_rules = None

MAX_BLOCKS = 7  # 平台连续顶回硬上限为 8，第 7 次转优雅停机，永不触顶
MAX_STALLS = 2  # 连续 N 次顶回「一点进展都没有」→ 判定打转（定义见 progress_sig）

def sh(args, cwd):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20)
        return p.returncode, p.stdout.strip()
    except Exception:
        return 1, ""

def progress_sig(root):
    """本轮末的进展快照指纹：HEAD + guard_rules.PROGRESS_FILES 的内容。
    共享库不在就返回 ""——退回「只看轮数」的老判法，宁可少停批也不误停。"""
    if guard_rules is None:
        return ""
    _, head = sh(["git", "rev-parse", "HEAD"], root)
    blobs = []
    for name in guard_rules.PROGRESS_FILES:
        try:
            with open(os.path.join(root, name), "rb") as f:
                blobs.append(f.read())
        except OSError:
            blobs.append(None)
    return guard_rules.progress_sig(head, blobs)

def save_state(root, st):
    """写回 state.json（原子替换）。只有钩子走这条路——模型改状态一律用 progress.py。"""
    try:
        p = os.path.join(root, ".loopwork", "state.json")
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    except Exception:
        pass

def round_hits(root, st):
    """本轮被实时围栏拦了几次 = 取证账本新增行数，并把水位线推到当前值。

    每轮末调一次。账本轮转过（行数反而变小）就复位水位线——宁可少报，
    也不报出负数：一个说谎的计数比没有计数更糟。"""
    if guard_log is None:
        return 0
    total = guard_log.count(root)
    try:
        seen = int(st.get("blocks_seen", 0) or 0)
    except (TypeError, ValueError):
        seen = 0
    if total < seen:
        seen = 0
    if total != seen:
        st["blocks_seen"] = total
        save_state(root, st)
    return max(0, total - seen)

def hits_note(n):
    """挂在顶回理由末尾的一句取证。没拦过就什么都不说，别给噪音。"""
    if not n:
        return ""
    return (f"\n[取证] 本轮实时围栏拦下 {n} 次动作（明细 .loopwork/logs/blocks.jsonl）。"
            "同一面墙撞两次以上就别再找绕路了：改走合规路径，或写进 BLOCKED.md 交给用户拍板。")

def protected(lines):
    """受保护文件 = 考题/规格/规矩 + 围栏自己（改围栏脚本等于把围栏关掉，任何借口都不行）。"""
    return [l for l in lines
            if l.startswith("tests/") or l.startswith(".loopwork/hooks/")
            or l in ("spec.md", "rules.md")]

def journal_deleted(root, revs):
    """JOURNAL.md 在这段区间里被删掉多少行（numstat 第二列）。读不到就当 0（fail-open）。"""
    code, out = sh(["git", "diff", "--numstat"] + revs + ["--", "JOURNAL.md"], root)
    cols = out.split() if code == 0 else []
    return int(cols[1]) if len(cols) >= 2 and cols[1].isdigit() else 0

def gate_reason(root, st):
    """检测门：返回顶回理由，一切正常返回 None。
    只有审计账本那一条会写盘（重置基准），其余全是只读判定。"""
    stage = str(st.get("stage", ""))
    phase = str(st.get("phase", ""))
    baseline = str(st.get("last_round_commit", "") or "")
    if stage not in ("4", "loop", "quick") or not os.path.isdir(os.path.join(root, ".git")):
        return None
    if baseline:
        code, _ = sh(["git", "merge-base", "--is-ancestor", baseline, "HEAD"], root)
        if code != 0:
            return (
                "[检测门] 基线存档 " + baseline[:10] + " 在当前 git 历史中不可达——"
                "历史可能被改写（amend/rebase）。停止一切实现工作：先向用户如实报告，"
                "恢复历史或经用户同意后用 progress.py set last_round_commit 重设基线。"
            )
    if phase == "implementing":
        code, out = sh(["git", "diff", "--name-only", "HEAD"], root)
        code2, out2 = sh(["git", "ls-files", "--others", "--exclude-standard"], root)
        live = protected((out.splitlines() if code == 0 else []) +
                         (out2.splitlines() if code2 == 0 else []))
        if live:
            return (
                "[检测门] 实现期有未存档的受保护文件改动：" + ", ".join(live[:5]) +
                "。考题先红后绿，实现期间不许碰考题/规格/规矩；围栏脚本（.loopwork/hooks/）"
                "任何时候都不许改。立即：①撤销"
                "（已跟踪文件 git checkout -- <文件>；新建文件直接删除）"
                "②在 JOURNAL.md 记一行原因 ③向用户说明。"
            )
        if baseline:
            code3, out3 = sh(["git", "diff", "--name-only", baseline, "HEAD"], root)
            committed = protected(out3.splitlines() if code3 == 0 else [])
            if committed:
                return (
                    "[检测门] 基线之后有已存档的受保护文件改动：" + ", ".join(committed[:5]) +
                    "。若这是你刚存档的红考题——只是忘了推进基线，立即执行 "
                    "python3 .loopwork/hooks/progress.py set last_round_commit "
                    "$(git rev-parse HEAD)（存档即推进基线）；若是实现期偷改后存档的——"
                    "revert 该存档、JOURNAL.md 记一行原因并向用户坦白。"
                )
    # 只增不减：JOURNAL.md 是历史（无论哪个相位）。
    # 两段都要看：基线..HEAD 抓「改写后存了档」，HEAD..工作区 抓「还没存档的改写」。
    gone = journal_deleted(root, [baseline, "HEAD"]) if baseline else 0
    gone += journal_deleted(root, ["HEAD"])
    if gone > 0:
        return (
            f"[检测门] JOURNAL.md 少了 {gone} 行——日志只增不减，改写过的历史不是证据。"
            "立即 git checkout -- JOURNAL.md 还原（已存档的改写用 git revert 撤销），"
            '要记新内容用 python3 .loopwork/hooks/progress.py journal "…" 追加；'
            "若删除是用户要求的，停下来让用户自己动手。"
        )

    # 只增不减（二）：审计账本只能变长。
    # 变短 = 有人抹账。唯一合法的变短是单代轮转（老账本被顶成 .1）。
    # 抹账无法由模型补回，所以只响一次：报完把基准重置，避免死循环把会话钉死。
    audit = os.path.join(root, ".loopwork", "logs", "audit.jsonl")
    try:
        now_bytes = os.path.getsize(audit)
    except OSError:
        now_bytes = None
    if now_bytes is not None:
        mark = st.get("audit_bytes")
        mark = int(mark) if str(mark).isdigit() else None
        if mark is not None and now_bytes < mark:
            try:
                rotated = os.path.getsize(audit + ".1")
            except OSError:
                rotated = 0
            st["audit_bytes"] = now_bytes
            save_state(root, st)
            if rotated < mark:
                return (
                    f"[检测门] 审计账本 .loopwork/logs/audit.jsonl 从 {mark} 字节缩到 {now_bytes} 字节，"
                    "且不是轮转——有人抹了账。审计只增不减：立即向用户如实报告这件事"
                    "（谁、什么时候、少了多少），并在 JOURNAL.md 记一行。基准已重置，不再重复顶回。"
                )
        elif now_bytes != mark:
            st["audit_bytes"] = now_bytes
            save_state(root, st)
    return None

def main():
    try:
        json.load(sys.stdin)  # 消费 payload（本钩子不需要内容）
    except Exception:
        pass
    try:
        root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        state_p = os.path.join(root, ".loopwork", "state.json")
        if not os.path.exists(state_p):
            return 0
        with open(state_p, encoding="utf-8") as f:
            st = json.load(f)

        # 本轮取证：账本比上轮末多出几行，就是模型这一轮撞了几次墙。水位线在这里
        # 一次推进并落盘——不能让「记没记账」取决于后面走哪个分支。
        hits = round_hits(root, st)

        # 上一轮已优雅停机 → 本轮无条件放行一次，掐断平台的连续顶回计数
        try:
            carried = int(st.get("stop_blocks", 0) or 0)
        except (TypeError, ValueError):
            carried = 0
        if carried < 0:
            st["stop_blocks"] = 0
            save_state(root, st)
            return 0

        flag = os.path.join(root, ".loopwork", "batch.flag")
        has_flag = os.path.exists(flag)
        raw = ""
        if has_flag:
            try:
                raw = open(flag, encoding="utf-8").read().strip()
            except Exception:
                pass
        parts = raw.split(",") if raw else []

        def num(i, default=None):
            return int(parts[i]) if len(parts) > i and parts[i].lstrip("-").isdigit() else default

        cap = int(st.get("round_cap", 20))
        batch_size = int(st.get("batch_size", 5))
        rounds = int(st.get("round_count", 0))
        start = num(0)
        if start is None:
            start = rounds
        last_nag = num(1)
        stalls = num(2, 0)
        blocks = num(3, 0) if has_flag else carried
        last_sig = parts[4] if len(parts) > 4 else ""   # 上次挂机顶回时的进展指纹

        def drop_flag():
            try:
                os.remove(flag)
            except OSError:
                pass

        def write_blocks(n):
            """顶回记账：批模式记 flag 第 4 段，非批模式记 state.stop_blocks。
            第 2、5 段（上次顶回轮数、进展指纹）原样带过去——它俩是一对，
            都是「上一次挂机顶回时的样子」，检测门的顶回不该动它们。"""
            if has_flag:
                with open(flag, "w", encoding="utf-8") as f:
                    f.write(f"{start},{'' if last_nag is None else last_nag},"
                            f"{stalls},{n},{last_sig}")
            else:
                st["stop_blocks"] = n
                save_state(root, st)

        def emit(msg):
            """所有顶回的唯一出口：话尾挂上本轮取证——连撞同一面墙是「在找绕路」的信号，
            模型自己也该看见。与 Codex 版同结构，方便两版对照排障。"""
            print(msg + hits_note(hits), file=sys.stderr)
            return 2

        def graceful(msg):
            """优雅停机：摘 flag + 记「下轮放行」，本次仍顶回一次把话说完。"""
            drop_flag()
            st["stop_blocks"] = -1
            save_state(root, st)
            return emit(msg)

        # ---------- 1. 检测门（永远执行，与批模式无关）----------
        reason = gate_reason(root, st)
        if reason:
            blocks += 1
            if blocks >= MAX_BLOCKS:
                return graceful(
                    reason + f"\n[检测门] 同一违规已顶回 {MAX_BLOCKS} 次仍未消除，先于平台硬上限停机"
                    "（挂机批也一并停了）。不要再试第二遍：把这件事原样告诉用户，让他决定怎么办。"
                )
            write_blocks(blocks)
            return emit(reason)
        if not has_flag:
            if carried:  # 检测门通过 = 连续顶回的链断了，账清零
                st["stop_blocks"] = 0
                save_state(root, st)
            return 0

        # ---------- 2. 挂机批模式 ----------
        actionable = blocked = 0
        try:
            with open(os.path.join(root, "tasks.md"), encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s.startswith("- [ ]"):
                        if "〔卡" in s:
                            blocked += 1
                        else:
                            actionable += 1
        except FileNotFoundError:
            pass

        def finish(msg):
            drop_flag()
            return emit(msg)

        if actionable <= 0 and blocked <= 0:
            drop_flag()
            return 0  # 任务全清，正常收工
        if actionable <= 0:
            return finish(f"[挂机档] 只剩 {blocked} 条受阻任务，无活可干。请汇总本批结果，并把问题本（BLOCKED.md）提请用户拍板。")
        if rounds >= cap:
            return finish(f"[挂机档] 轮数达到上限 {cap}，安全停机。请汇总本批结果并请用户验收。")
        if rounds - start >= batch_size:
            return finish(f"[挂机档] 本批已做满 {batch_size} 条（外部计数）。按纪律进验收环节，不许跳过检查点。")
        # 无进展 = 轮数没涨 ∧ HEAD 没动 ∧ tasks.md 没动 ∧ BLOCKED.md 没动（见 progress_sig）。
        # 只看轮数会把「一条硬任务跨两次顶回」误判成打转——红考题存了档、任务标了〔卡〕、
        # 问题本添了一条，都是进展，不该因此停批。
        sig = progress_sig(root)
        if last_nag is not None and rounds == last_nag and sig == last_sig:
            stalls += 1
            if stalls >= MAX_STALLS:
                return finish(
                    f"[挂机档] 连续 {MAX_STALLS} 次顶回一点进展都没有（仍是第 {rounds} 轮，"
                    "HEAD、tasks.md、BLOCKED.md 都没动过），判定原地打转，自动停批。"
                    "请按停批汇报格式向用户汇总：完成了什么、卡在哪、问题本新增了什么。"
                )
        else:
            stalls = 0
        blocks += 1
        if blocks >= MAX_BLOCKS:
            return graceful(
                f"[挂机档] 本批顶回已达安全上限（{MAX_BLOCKS} 次），先于平台硬上限优雅停批。"
                "请按停批汇报格式向用户汇总进度；要继续挂机请用户重新开批。"
            )
        with open(flag, "w", encoding="utf-8") as f:
            f.write(f"{start},{rounds},{stalls},{blocks},{sig}")
        if stalls > 0:
            return emit(
                f"[挂机档] 顶回后轮数没涨（仍是第 {rounds} 轮），存档、tasks.md、BLOCKED.md 也都没动——"
                "若卡在同一任务：按失败分级处理（3 次转诊断），或写 BLOCKED.md 跳过取下一条。"
                "再次无进展将自动停批。"
            )
        return emit(
            f"[挂机档] 批模式进行中：本批 {rounds - start}/{batch_size} 条，剩余可做任务 {actionable} 条（总轮数 {rounds}/{cap}）。"
            "按内循环节奏继续取下一条任务。用户喊停 = 删除 .loopwork/batch.flag。"
        )
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
