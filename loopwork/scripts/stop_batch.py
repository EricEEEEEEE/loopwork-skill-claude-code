#!/usr/bin/env python3
"""围栏 · 挂机批模式（Stop 钩子）。

.loopwork/batch.flag 存在 且 本批还有未完成任务 且 轮数未达上限
→ exit 2 把 Claude 顶回去继续干（stderr 作为继续指令）。
批空 / 达上限 / 无 flag → 放行；批空时顺手摘掉 flag。
外部计数器在这里，不靠模型自数。
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
        rounds = int(st.get("round_count", 0))
        remaining = 0
        try:
            with open(os.path.join(root, "tasks.md"), encoding="utf-8") as f:
                remaining = sum(1 for line in f if line.strip().startswith("- [ ]"))
        except FileNotFoundError:
            pass
        if remaining <= 0:
            os.remove(flag)
            return 0  # 批空，恢复正常
        if rounds >= cap:
            os.remove(flag)
            print(f"[挂机档] 轮数达到上限 {cap}，安全停机。请汇总本批结果并请用户验收。", file=sys.stderr)
            return 2
        print(
            f"[挂机档] 批模式进行中：还有 {remaining} 条任务未完成（第 {rounds}/{cap} 轮）。"
            "按内循环节奏继续取下一条任务。用户喊停 = 删除 .loopwork/batch.flag。",
            file=sys.stderr,
        )
        return 2
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
