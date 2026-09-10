#!/usr/bin/env bash
# Loopwork CC 版 · 装机自检（零模型调用，约 5 秒）
# 回答一个问题：这个项目的围栏，现在真的在岗吗？
# 用法: selftest.sh [项目目录]        全 ✅ → exit 0；有 ❌ → exit 1
set -u
: "${LANG:=en_US.UTF-8}"; export LANG
PROJ="$(cd "${1:-$PWD}" && pwd)"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS="$PROJ/.loopwork/hooks"
PASS=0; FAIL=0; WARN=0

say()  { printf '%s\n' "$*"; }
ok()   { say "  ✅ $*"; PASS=$((PASS+1)); }
bad()  { say "  ❌ $*"; FAIL=$((FAIL+1)); }
warn() { say "  ⚠️  $*"; WARN=$((WARN+1)); }

say "== Loopwork 装机自检 · $PROJ =="

if [ ! -d "$PROJ/.loopwork" ]; then
  bad "这里没有 .loopwork/——不是 loopwork 项目，或还没建家（先跑 init_project.sh）"
  say ""; say "== 自检结果：0 通过，1 失败 =="; exit 1
fi

say "[1] 底座"
if command -v python3 >/dev/null 2>&1; then ok "python3 $(python3 --version 2>&1 | cut -d' ' -f2)"
else bad "找不到 python3——所有围栏都是 python 脚本，装上它围栏才会动"; fi
if command -v git >/dev/null 2>&1; then ok "git $(git --version | cut -d' ' -f3)"
else bad "找不到 git——存档系统不可用，等于没有证据链"; fi
if [ -d "$PROJ/.git" ]; then ok "存档系统已开启（.git 在）"
else bad "项目没有 .git——检测门无法对账基线，存档纪律全废"; fi

say "[2] 围栏进驻 + 与技能库一致性"
for f in guard_edits.py guard_bash.py guard_ask.py stop_batch.py audit_log.py progress.py verify.sh; do
  if [ ! -f "$HOOKS/$f" ]; then
    bad "$f 没进驻（重跑 init_project.sh 补齐）"
  elif [ -f "$SKILL_DIR/scripts/$f" ] && ! cmp -s "$SKILL_DIR/scripts/$f" "$HOOKS/$f"; then
    warn "$f 与技能库版本不一致（技能升级过但项目没同步：重跑 init_project.sh）"
  else
    ok "$f"
  fi
done

say "[3] 钩子接线（双写：技能 frontmatter 兜底 + 项目 settings.json 主线）"
SET="$PROJ/.claude/settings.json"
if [ ! -f "$SET" ]; then
  bad "缺 .claude/settings.json——围栏一条都不会被触发（重跑 init_project.sh）"
else
  python3 - "$SET" <<'PYEOF'
import json, sys
want = {
    "PreToolUse": ["guard_edits.py", "guard_bash.py", "guard_ask.py"],
    "PostToolUse": ["audit_log.py"],
    "Stop": ["stop_batch.py"],
    "SessionStart": ["progress.py"],
}
try:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    print(f"  ❌ settings.json 解析失败（{e}）——CC 会整份忽略它，围栏全线失联")
    sys.exit(9)
hooks = cfg.get("hooks") or {}
missing = []
for event, scripts in want.items():
    blob = json.dumps(hooks.get(event) or [], ensure_ascii=False)
    for s in scripts:
        if s not in blob:
            missing.append(f"{event}/{s}")
if missing:
    print("  ❌ settings.json 少了接线：" + ", ".join(missing))
    sys.exit(9)
print("  ✅ settings.json 六处接线齐全（Pre×3 / Post / Stop / SessionStart）")
PYEOF
  if [ $? -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
fi
SK="$SKILL_DIR/SKILL.md"
if [ -f "$SK" ] && grep -q "guard_bash.py" "$SK" && grep -q "audit_log.py" "$SK"; then
  ok "技能 frontmatter 兜底接线在（settings.json 丢了也还有一层）"
else
  warn "技能 frontmatter 里没找到围栏接线——只剩 settings.json 单点，别丢它"
fi

say "[4] 顶回上限（平台硬上限 vs 围栏自停线）"
CAP="${CLAUDE_CODE_STOP_HOOK_BLOCK_CAP:-8}"
# 先砍掉行尾注释再取数字——注释里也有「8」「7」，不砍会读成 787
MAXB="$(grep -m1 '^MAX_BLOCKS' "$HOOKS/stop_batch.py" 2>/dev/null | sed 's/#.*//' | tr -dc '0-9')"
MAXB="${MAXB:-0}"
if [ "$MAXB" -eq 0 ]; then
  bad "读不到 stop_batch.py 的 MAX_BLOCKS——顶回上限失控"
elif [ "$MAXB" -lt "$CAP" ]; then
  ok "MAX_BLOCKS=$MAXB < 平台上限 ${CAP}：围栏会先于平台优雅停机，flag 不会残留"
else
  bad "MAX_BLOCKS=$MAXB ≥ 平台上限 ${CAP}：平台会先强制放行且 batch.flag 残留——把 CLAUDE_CODE_STOP_HOOK_BLOCK_CAP 调大，或把 MAX_BLOCKS 调小"
fi

say "[5] 状态机"
python3 - "$PROJ/.loopwork/state.json" <<'PYEOF'
import json, sys
try:
    st = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    print(f"  ❌ state.json 读不了（{e}）——文件即记忆，这份文件坏了等于失忆")
    sys.exit(9)
need = ["stage", "phase", "round_count", "round_cap", "batch_size", "last_round_commit"]
miss = [k for k in need if k not in st]
if miss:
    print("  ❌ state.json 缺字段：" + ", ".join(miss) + "（旧版状态文件，补上默认值即可）")
    sys.exit(9)
print(f"  ✅ state.json 完整：stage={st['stage']} phase={st['phase']} 轮次={st['round_count']}/{st['round_cap']}")
PYEOF
if [ $? -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

say "[6] 活体探针（接线在 ≠ 拦得住）"
RMP="rm -""rf /nonexistent-loopwork-selftest"
PROBE="$(printf '{"tool_name":"Bash","tool_input":{"command":"%s"},"cwd":"%s"}' "$RMP" "$PROJ")"
if [ -f "$HOOKS/guard_bash.py" ]; then
  printf '%s' "$PROBE" | CLAUDE_PROJECT_DIR="$PROJ" python3 "$HOOKS/guard_bash.py" >/dev/null 2>&1
  RC=$?
  if [ "$RC" -eq 2 ]; then ok "危险删除探针被 guard_bash 当场拦下"
  else bad "危险删除探针没被拦（exit=${RC}）——围栏在岗但不咬人，立刻停用挂机批"; fi
fi
if [ -f "$HOOKS/stop_batch.py" ]; then
  printf '{}' | CLAUDE_PROJECT_DIR="$PROJ" python3 "$HOOKS/stop_batch.py" >/dev/null 2>&1
  RC=$?
  if [ "$RC" -eq 0 ] || [ "$RC" -eq 2 ]; then ok "stop_batch 可执行（本轮判定 exit=${RC}）"
  else bad "stop_batch 执行异常（exit=${RC}）"; fi
fi

say ""
say "== 自检结果：$PASS 通过，$FAIL 失败，$WARN 警告 =="
if [ "$FAIL" -gt 0 ]; then
  say "有 ❌ 就别开挂机批——围栏没在岗的时候挂机，等于无人看守的施工现场。"
  exit 1
fi
say "围栏在岗。警告项不阻断使用，但建议顺手清掉。"
exit 0
