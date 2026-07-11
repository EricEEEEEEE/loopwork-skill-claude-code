#!/usr/bin/env bash
# 本仓库的考题入口（loopwork/scripts/verify.sh 会自动发现并执行它）
set -eu
cd "$(dirname "$0")/.."
python3 tests/test_guards.py
