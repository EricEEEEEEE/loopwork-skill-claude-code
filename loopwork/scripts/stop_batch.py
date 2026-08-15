#!/usr/bin/env python3
"""围栏 · 挂机批模式（Stop 钩子）。外部计数器在这里，不靠模型自数。

批次语义（对齐 SKILL.md ④）：
- .loopwork/batch.flag 存 "起点轮数,上次顶回轮数,无进展次数,顶回总数"
  （兼容旧版纯数字 = 起点轮数；空 flag 首次遇到时自动写入）
- 本批做满 batch_size 条 → 摘 flag 并顶回一次：去验收（不许跳过检查点）
- 只剩受阻任务（〔卡·…〕）→ 摘 flag 并顶回一次：汇总 + 请用户清问题本
- 轮数达 round_cap → 摘 flag，安全停机汇总
- 连续 MAX_STALLS 次顶回轮数没涨 → 判定原地打转，摘 flag 并要求停批汇报
- 顶回总数达 MAX_BLOCKS → 摘 flag 优雅停批：平台对连续 Stop 顶回有硬上限
  （CLAUDE_CODE_STOP_HOOK_BLOCK_CAP，默认 8），第 8 次会被强制放行且 flag
  残留在盘上、批承诺无声作废——必须先于它自己收尾
- 还有可做任务且未满批 → 顶回继续
- 无 flag / 任务全清 → 放行
"""
import json, os, sys

MAX_BLOCKS = 7  # 平台连续顶回硬上限为 8，第 7 次转优雅停批，永不触顶
MAX_STALLS = 2  # 连续 N 次顶回轮数未涨 → 判定打转

def main():
    try:
        json.load(sys.stdin)  # 消费 payload（本钩子不需要内容）
    except Exception:
        pass
    try:
        root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        flag = os.path.join(root, ".loopwork", "batch.flag")
        if not os.path.exists(flag):
            return 0
        state_p = os.path.join(root, ".loopwork", "state.json")
        if not os.path.exists(state_p):
            return 0
        with open(state_p, encoding="utf-8") as f:
            st = json.load(f)
        cap = int(st.get("round_cap", 20))
        batch_size = int(st.get("batch_size", 5))
        rounds = int(st.get("round_count", 0))

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

        # flag 解析（旧版纯数字 = 只有起点）
        raw = ""
        try:
            raw = open(flag, encoding="utf-8").read().strip()
        except Exception:
            pass
        parts = raw.split(",") if raw else []

        def num(i, default=None):
            return int(parts[i]) if len(parts) > i and parts[i].lstrip("-").isdigit() else default

        start = num(0)
        last_nag = num(1)
        stalls = num(2, 0)
        blocks = num(3, 0)
        if start is None:
            start = rounds

        def finish(msg):
            try:
                os.remove(flag)
            except OSError:
                pass
            print(msg, file=sys.stderr)
            return 2

        if actionable <= 0 and blocked <= 0:
            try:
                os.remove(flag)
            except OSError:
                pass
            return 0  # 任务全清，正常收工
        if actionable <= 0:
            return finish(f"[挂机档] 只剩 {blocked} 条受阻任务，无活可干。请汇总本批结果，并把问题本（BLOCKED.md）提请用户拍板。")
        if rounds >= cap:
            return finish(f"[挂机档] 轮数达到上限 {cap}，安全停机。请汇总本批结果并请用户验收。")
        if rounds - start >= batch_size:
            return finish(f"[挂机档] 本批已做满 {batch_size} 条（外部计数）。按纪律进验收环节，不许跳过检查点。")
        if last_nag is not None and rounds == last_nag:
            stalls += 1
            if stalls >= MAX_STALLS:
                return finish(
                    f"[挂机档] 连续 {MAX_STALLS} 次顶回轮数都没涨（仍是第 {rounds} 轮），判定原地打转，自动停批。"
                    "请按停批汇报格式向用户汇总：完成了什么、卡在哪、问题本新增了什么。"
                )
        else:
            stalls = 0
        blocks += 1
        if blocks >= MAX_BLOCKS:
            return finish(
                f"[挂机档] 本批顶回已达安全上限（{MAX_BLOCKS} 次），先于平台硬上限优雅停批。"
                "请按停批汇报格式向用户汇总进度；要继续挂机请用户重新开批。"
            )
        with open(flag, "w", encoding="utf-8") as f:
            f.write(f"{start},{rounds},{stalls},{blocks}")
        if stalls > 0:
            print(
                f"[挂机档] 顶回后轮数没涨（仍是第 {rounds} 轮）——若卡在同一任务：按失败分级处理（3 次转诊断），"
                "或写 BLOCKED.md 跳过取下一条。再次无进展将自动停批。",
                file=sys.stderr,
            )
        else:
            print(
                f"[挂机档] 批模式进行中：本批 {rounds - start}/{batch_size} 条，剩余可做任务 {actionable} 条（总轮数 {rounds}/{cap}）。"
                "按内循环节奏继续取下一条任务。用户喊停 = 删除 .loopwork/batch.flag。",
                file=sys.stderr,
            )
        return 2
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
