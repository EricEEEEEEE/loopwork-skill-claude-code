#!/usr/bin/env python3
"""围栏 · 挂机批提问守卫（PreToolUse: AskUserQuestion）。

挂机批模式（.loopwork/batch.flag 存在）意味着用户已离开现场：
此刻弹提问，整批会挂死在等待上——违背「问题本跳过不停机」纪律。
拦下并指路：写 BLOCKED.md、任务标〔卡〕、跳过取下一条。
非批模式 / 非 loopwork 项目 / 内部异常：放行（fail-open）。
"""
import json, os, sys

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        if not os.path.exists(os.path.join(root, ".loopwork", "state.json")):
            return 0
        if not os.path.exists(os.path.join(root, ".loopwork", "batch.flag")):
            return 0
        print(
            "[围栏] 挂机批进行中，用户不在场——提问会让整批挂死在等待上。"
            "要拍板的事写进 BLOCKED.md（问题/背景/建议+理由），任务标〔卡·B编号〕跳过取下一条，批末验收一把清算。"
            "真到了没人拍板就一步都动不了的地步：写进 BLOCKED.md 并在回复里如实说明，"
            "请用户在自己的终端删掉 .loopwork/batch.flag 停批——批次开关不在你手上（围栏拦模型删 flag）；"
            "你若原地打转，停滞检测会在 2 轮内自动停批。",
            file=sys.stderr,
        )
        return 2
    except Exception:
        return 0

if __name__ == "__main__":
    sys.exit(main())
