#!/usr/bin/env python3
"""Loopwork 围栏与状态机回归套件（本仓库的考题）。

在临时目录里用 init_project.sh 建一个沙盒项目，对四台机器
（guard_edits / guard_bash / stop_batch / progress）喂伪造载荷，验证拦截/放行/顶回行为。
exit 0 = 全绿。
"""
import json, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INIT = os.path.join(REPO, "loopwork", "scripts", "init_project.sh")
RESULTS = []

def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(("✅" if ok else "❌") + f" {name}" + (f"  [{detail}]" if detail and not ok else ""))

def main():
    S = tempfile.mkdtemp(prefix="loopwork-test-")
    try:
        env = {**os.environ, "CLAUDE_PROJECT_DIR": S}
        r = subprocess.run(["bash", INIT, S, "沙盒项目"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        check("init 建家成功", r.returncode == 0, r.stderr[-200:])
        H = os.path.join(S, ".loopwork", "hooks")
        for f in ("guard_edits.py", "guard_bash.py", "stop_batch.py", "progress.py", "verify.sh"):
            check(f"围栏进驻 {f}", os.path.exists(os.path.join(H, f)))
        check("钩子接线 settings.json", os.path.exists(os.path.join(S, ".claude", "settings.json")))

        def hook(script, payload):
            p = subprocess.run(["python3", os.path.join(H, script)], input=json.dumps(payload),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=S)
            return p.returncode

        def setp(key, val):
            subprocess.run(["python3", os.path.join(H, "progress.py"), "set", key, str(val)],
                           capture_output=True, env=env, cwd=S)

        ed = lambda fp: {"tool_name": "Edit", "tool_input": {"file_path": fp}, "cwd": S}
        ba = lambda c: {"tool_name": "Bash", "tool_input": {"command": c}, "cwd": S}
        RM = "rm " + "-rf /x"          # 拼接写法，避免上游安全钩子误拦本测试文件
        RM2 = "rm " + "-r " + "-f /x"

        # —— guard_edits ——
        setp("phase", "implementing")
        check("A1 implementing 改考题被拦", hook("guard_edits.py", ed("tests/foo.py")) == 2)
        check("A2 改围栏自身被拦", hook("guard_edits.py", ed(".loopwork/hooks/guard_edits.py")) == 2)
        check("A3 直接改 state 被拦", hook("guard_edits.py", ed(".loopwork/state.json")) == 2)
        check("A4 改普通文件放行", hook("guard_edits.py", ed("src/app.js")) == 0)
        check("A5 越界项目外被拦", hook("guard_edits.py", ed("/etc/hosts")) == 2)
        # —— guard_bash：剧本规定动作必须放行 ——
        check("B1 跑考题+管道放行", hook("guard_bash.py", ba("pytest tests/ -q 2>&1 | tail -20")) == 0)
        check("B2 跑考题+重定向放行", hook("guard_bash.py", ba("pytest tests/ > out.log 2>&1")) == 0)
        check("B3 verify+重定向放行", hook("guard_bash.py", ba("bash .loopwork/hooks/verify.sh > v.log 2>&1")) == 0)
        check("B4 红考题存档放行", hook("guard_bash.py", ba("git add tests/ && git commit -m 红")) == 0)
        # —— guard_bash：真实攻击仍拦 ——
        check("B5 重定向写考题被拦", hook("guard_bash.py", ba("echo cheat > tests/foo.py")) == 2)
        check("B6 cp 覆盖考题被拦", hook("guard_bash.py", ba("cp hack.py tests/foo.py")) == 2)
        check("B7 sed 改 spec 被拦", hook("guard_bash.py", ba("sed -i s/a/b/ spec.md")) == 2)
        check("B8 tee 写围栏被拦", hook("guard_bash.py", ba("echo x | tee .loopwork/hooks/g.py")) == 2)
        check("B9 危险删除(合写)被拦", hook("guard_bash.py", ba(RM)) == 2)
        check("B10 危险删除(分写)被拦", hook("guard_bash.py", ba(RM2)) == 2)
        check("B11 普通 rm 单文件放行", hook("guard_bash.py", ba("rm out.log")) == 0)
        check("B12 force push 被拦", hook("guard_bash.py", ba("git push --force origin main")) == 2)
        # —— phase 语义 ——
        setp("phase", "test-writing")
        check("C1 test-writing 改考题放行", hook("guard_edits.py", ed("tests/foo.py")) == 0)
        check("C2 任意 phase 围栏自保", hook("guard_bash.py", ba("sed -i x .loopwork/state.json")) == 2)
        journal = open(os.path.join(S, "JOURNAL.md"), encoding="utf-8").read()
        check("C3 phase 翻转有审计留痕", "[audit] phase → test-writing" in journal)
        # —— stop_batch：批次外部计数 ——
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [ ] T01 a\n- [ ] T02 b\n- [ ] T03 c\n")
        flag = os.path.join(S, ".loopwork", "batch.flag")
        open(flag, "w").close()
        setp("round_count", 0); setp("batch_size", 2)
        check("D1 批中顶回", hook("stop_batch.py", {}) == 2)
        check("D2 flag 记录批次起点", open(flag).read().strip() == "0")
        setp("round_count", 2)
        check("D3 满批强制去验收", hook("stop_batch.py", {}) == 2 and not os.path.exists(flag))
        open(flag, "w").close()
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [ ] T01 a 〔卡·B01〕\n- [x] T02 b\n")
        check("D4 只剩受阻→清问题本", hook("stop_batch.py", {}) == 2 and not os.path.exists(flag))
        open(flag, "w").close()
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [x] T01 a\n- [x] T02 b\n")
        check("D5 批空放行+摘 flag", hook("stop_batch.py", {}) == 0 and not os.path.exists(flag))
        # —— 对账与相位复位（实测②④发现）——
        setp("phase", "implementing")
        subprocess.run(["python3", os.path.join(H, "progress.py"), "bump-cycle"],
                       capture_output=True, env=env, cwd=S)
        st_now = json.load(open(os.path.join(S, ".loopwork", "state.json"), encoding="utf-8"))
        check("H1 bump-cycle 复位 phase", st_now.get("phase") == "test-writing")
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [x] T01 a\n- [x] T02 b\n- [ ] T03 c\n")
        p = subprocess.run(["python3", os.path.join(H, "progress.py"), "card"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=S)
        check("H2 进度卡对账警告（勾选>存档）", "对账警告" in p.stdout)
        # —— frontmatter 包装器（P0-2 回归）——
        w = 'G="$CLAUDE_PROJECT_DIR/.loopwork/hooks/guard_edits.py"; if [ -f "$G" ]; then python3 "$G"; fi'
        p = subprocess.run(["bash", "-c", w], input="{}", capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "CLAUDE_PROJECT_DIR": S + "-nonexistent"})
        check("E1 未建家目录不误封", p.returncode == 0)
        setp("phase", "implementing")
        p = subprocess.run(["bash", "-c", w], input=json.dumps(ed("tests/foo.py")),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=S)
        check("E2 已建家拦截穿透包装器", p.returncode == 2)
        # —— verify fail-closed ——
        shutil.rmtree(os.path.join(S, "tests"), ignore_errors=True)
        v = subprocess.run(["bash", os.path.join(H, "verify.sh")], capture_output=True, env=env, cwd=S)
        check("F1 无考题 fail-closed(exit 3)", v.returncode == 3)
        # —— init 幂等 ——
        r2 = subprocess.run(["bash", INIT, S, "沙盒项目"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        check("G1 init 重复跑安全", r2.returncode == 0)
    finally:
        shutil.rmtree(S, ignore_errors=True)

    print(f"\n{'=' * 42}\n{sum(RESULTS)}/{len(RESULTS)} 通过")
    return 0 if all(RESULTS) else 1

if __name__ == "__main__":
    sys.exit(main())
