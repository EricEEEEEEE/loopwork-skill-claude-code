#!/usr/bin/env python3
"""围栏 · 挂机批模式（Stop 钩子）。外部计数器在这里，不靠模型自数。

批次语义（对齐 SKILL.md ④）：
- .loopwork/batch.flag 存本批起点轮数（空 flag 首次遇到时自动写入当前轮数）
- 本批做满 batch_size 条 → 摘 flag 并顶回一次：去验收（不许跳过检查点）
- 只剩受阻任务（〔卡·…〕）→ 摘 flag 并顶回一次：汇总 + 请用户清问题本
- 轮数达 round_cap → 摘 flag，安全停机汇总
- 还有可做任务且未满批 → 顶回继续
- 无 flag / 任务全清 → 放行
"""
import json, os, sys

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

        # 批次起点：空 flag 首遇写入
        start = None
        try:
            raw = open(flag, encoding="utf-8").read().strip()
            start = int(raw) if raw else None
        except Exception:
            start = None
        if start is None:
            start = rounds
            with open(flag, "w", encoding="utf-8") as f:
                f.write(str(start))

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
