#!/usr/bin/env bash
# Loopwork 建家脚本（幂等，重复跑安全）：
#   骨架 + git + 状态文件 + 围栏进驻 + 钩子接线 + .gitignore
# 用法: init_project.sh <项目目录> [项目名]
set -eu
PROJ="${1:?用法: init_project.sh <项目目录> [项目名]}"
NAME="${2:-$(basename "$PROJ")}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$PROJ/.loopwork/hooks" "$PROJ/.loopwork/logs" "$PROJ/tests"
cd "$PROJ"

# 1. git（存档系统）
if [ ! -d .git ]; then git init -q; echo "[init] git 存档系统已开启"; fi

# 2. 围栏与工具进驻（围栏脚本以标准库为准，覆盖更新）
for f in guard_edits.py guard_bash.py stop_batch.py progress.py verify.sh; do
  cp -f "$SKILL_DIR/scripts/$f" ".loopwork/hooks/$f"
done
chmod +x .loopwork/hooks/*.sh .loopwork/hooks/*.py 2>/dev/null || true

# 3. 状态文件（已存在则不动）
if [ ! -f .loopwork/state.json ]; then
  NODE_V="$(command -v node >/dev/null 2>&1 && node --version || echo none)"
  PY_V="$(command -v python3 >/dev/null 2>&1 && python3 --version 2>&1 | cut -d' ' -f2 || echo none)"
  cat > .loopwork/state.json <<EOF
{
  "schema": 1,
  "stage": "0",
  "phase": "test-writing",
  "cycle": 1,
  "project_name": "$NAME",
  "round_count": 0,
  "round_cap": 20,
  "batch_size": 5,
  "milestones": [],
  "env": {"node": "$NODE_V", "python3": "$PY_V"}
}
EOF
  echo "[init] 状态文件已创建"
fi
[ -f JOURNAL.md ] || printf '# 工作日志（每轮一行）\n\n' > JOURNAL.md
[ -f BLOCKED.md ] || printf '# 问题本（要用户拍板的事）\n\n' > BLOCKED.md

# 4. 钩子接线：合并进项目 .claude/settings.json（保留既有配置，幂等）
mkdir -p .claude
python3 - <<'PYEOF'
import json, os
p = ".claude/settings.json"
cfg = {}
if os.path.exists(p):
    with open(p, encoding="utf-8") as f:
        try: cfg = json.load(f)
        except Exception: cfg = {}
hooks = cfg.setdefault("hooks", {})
def cmd(c): return {"type": "command", "command": c}
WANT = {
    "PreToolUse": [
        {"matcher": "Edit|Write|MultiEdit", "hooks": [cmd('python3 "$CLAUDE_PROJECT_DIR/.loopwork/hooks/guard_edits.py"')]},
        {"matcher": "Bash", "hooks": [cmd('python3 "$CLAUDE_PROJECT_DIR/.loopwork/hooks/guard_bash.py"')]},
    ],
    "Stop": [{"hooks": [cmd('python3 "$CLAUDE_PROJECT_DIR/.loopwork/hooks/stop_batch.py"')]}],
    "SessionStart": [{"hooks": [cmd('python3 "$CLAUDE_PROJECT_DIR/.loopwork/hooks/progress.py" card')]}],
}
for event, entries in WANT.items():
    have = hooks.setdefault(event, [])
    for e in entries:
        sig = json.dumps(e, sort_keys=True, ensure_ascii=False)
        if not any(json.dumps(h, sort_keys=True, ensure_ascii=False) == sig for h in have):
            have.append(e)
with open(p, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print("[init] 围栏钩子已接线 (.claude/settings.json)")
PYEOF

# 5. .gitignore（追加缺失项）
touch .gitignore
for line in ".env" "*.local" ".loopwork/logs/" ".loopwork/batch.flag" "node_modules/" "__pycache__/"; do
  grep -qxF "$line" .gitignore || echo "$line" >> .gitignore
done

# 6. 首次存档
if ! git rev-parse HEAD >/dev/null 2>&1; then
  git add -A && git commit -qm "存档: Loopwork 项目初始化"
  echo "[init] 首次存档完成"
fi

echo "[init] ✅ 「$NAME」建家完成：git + 状态机 + 围栏 + 日志/问题本 + .gitignore"
