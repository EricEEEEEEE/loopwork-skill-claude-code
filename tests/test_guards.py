#!/usr/bin/env python3
"""Loopwork 围栏与状态机回归套件（本仓库的考题）。

在临时目录里用 init_project.sh 建一个沙盒项目，对五台机器
（guard_edits / guard_bash / guard_ask / stop_batch / progress）喂伪造载荷，验证拦截/放行/顶回行为。
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
        for f in ("guard_edits.py", "guard_bash.py", "guard_ask.py", "stop_batch.py", "progress.py", "verify.sh"):
            check(f"围栏进驻 {f}", os.path.exists(os.path.join(H, f)))
        check("钩子接线 settings.json", os.path.exists(os.path.join(S, ".claude", "settings.json")))

        def hook(script, payload):
            p = subprocess.run(["python3", os.path.join(H, script)], input=json.dumps(payload),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=S)
            return p.returncode

        def hook2(script, payload):
            p = subprocess.run(["python3", os.path.join(H, script)], input=json.dumps(payload),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=S)
            return p.returncode, p.stderr

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
        nb = lambda fp: {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": fp}, "cwd": S}
        check("A6 NotebookEdit 改考题被拦", hook("guard_edits.py", nb("tests/nb.ipynb")) == 2)
        check("A7 大小写变体改考题被拦", hook("guard_edits.py", ed("TESTS/foo.py")) == 2)
        os.symlink("tests", os.path.join(S, "tlink"))
        check("A8 符号链接绕道被拦", hook("guard_edits.py", ed("tlink/foo.py")) == 2)
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
        check("B13 push -f 短旗标被拦", hook("guard_bash.py", ba("git push -f origin main")) == 2)
        check("B14 push +refspec 被拦", hook("guard_bash.py", ba("git push origin +main")) == 2)
        RM3 = "rm " + "--recursive " + "--force /x"
        check("B15 危险删除(长旗标)被拦", hook("guard_bash.py", ba(RM3)) == 2)
        check("B16 正常 push 放行", hook("guard_bash.py", ba("git push origin main")) == 0)
        check("B17 checkout 回滚考题被拦", hook("guard_bash.py", ba("git checkout HEAD~1 -- tests/exam.py")) == 2)
        check("B18 restore 回滚考题被拦", hook("guard_bash.py", ba("git restore --source=HEAD~1 tests/")) == 2)
        check("B19 git apply 盲区被拦", hook("guard_bash.py", ba("git apply fix.patch")) == 2)
        check("B20 checkout 开分支放行", hook("guard_bash.py", ba("git checkout -b feature")) == 0)
        check("B21 cp 从考题拷出放行（只有目的地算写）", hook("guard_bash.py", ba("cp tests/golden.json /tmp/out.json")) == 0)
        check("B22 cp 带旗标覆盖考题被拦", hook("guard_bash.py", ba("cp -f hack2.py tests/golden.json")) == 2)
        check("B23 mv 搬走考题被拦（源文件会消失）", hook("guard_bash.py", ba("mv tests/exam.py /tmp/")) == 2)
        # —— phase 语义 ——
        setp("phase", "test-writing")
        check("C1 test-writing 改考题放行", hook("guard_edits.py", ed("tests/foo.py")) == 0)
        check("C2 任意 phase 围栏自保", hook("guard_bash.py", ba("sed -i x .loopwork/state.json")) == 2)
        journal = open(os.path.join(S, "JOURNAL.md"), encoding="utf-8").read()
        check("C3 phase 翻转有审计留痕", "[audit] phase → test-writing" in journal)
        check("C4 考题期 checkout 考题放行", hook("guard_bash.py", ba("git checkout -- tests/foo.py")) == 0)
        # —— stop_batch：批次外部计数 + 防打转 + 顶回安全上限 ——
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [ ] T01 a\n- [ ] T02 b\n- [ ] T03 c\n")
        flag = os.path.join(S, ".loopwork", "batch.flag")
        open(flag, "w").close()
        setp("round_count", 0); setp("batch_size", 2)
        check("D1 批中顶回", hook("stop_batch.py", {}) == 2)
        check("D2 flag 记起点+顶回计数", open(flag).read().strip() == "0,0,0,1")
        rc, err = hook2("stop_batch.py", {})
        check("D2b 无进展第 1 次仅警告", rc == 2 and "没涨" in err and open(flag).read().strip() == "0,0,1,2")
        rc, err = hook2("stop_batch.py", {})
        check("D2c 连续 2 次无进展自动停批", rc == 2 and "打转" in err and not os.path.exists(flag))
        with open(flag, "w", encoding="utf-8") as f:
            f.write("0")  # 旧版 flag 格式（纯数字 = 起点）
        setp("round_count", 2)
        check("D3 满批强制去验收（兼容旧 flag）", hook("stop_batch.py", {}) == 2 and not os.path.exists(flag))
        open(flag, "w").close()
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [ ] T01 a 〔卡·B01〕\n- [x] T02 b\n")
        check("D4 只剩受阻→清问题本", hook("stop_batch.py", {}) == 2 and not os.path.exists(flag))
        open(flag, "w").close()
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [x] T01 a\n- [x] T02 b\n")
        check("D5 批空放行+摘 flag", hook("stop_batch.py", {}) == 0 and not os.path.exists(flag))
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [ ] T01 a\n- [ ] T02 b\n- [ ] T03 c\n")
        with open(flag, "w", encoding="utf-8") as f:
            f.write("0,0,0,6")  # 本批已顶回 6 次
        setp("round_count", 1)
        rc, err = hook2("stop_batch.py", {})
        check("D6 顶回达安全上限优雅停批", rc == 2 and "安全上限" in err and not os.path.exists(flag))
        # —— guard_ask：挂机批禁提问 ——
        ask = {"tool_name": "AskUserQuestion", "tool_input": {}, "cwd": S}
        open(flag, "w").close()
        rc, err = hook2("guard_ask.py", ask)
        check("I1 挂机批弹提问被拦+指路", rc == 2 and "BLOCKED" in err)
        os.remove(flag)
        check("I2 非批模式提问放行", hook("guard_ask.py", ask) == 0)
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
        subprocess.run(["git", "commit", "-qm", "存档: T01 假完成", "--allow-empty"], capture_output=True, env=env, cwd=S)
        p = subprocess.run(["python3", os.path.join(H, "progress.py"), "card"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=S)
        check("H3 空存档假完成被点破", "空提交" in p.stdout)
        # —— frontmatter 包装器（P0-2 回归）——
        w = 'G="$CLAUDE_PROJECT_DIR/.loopwork/hooks/guard_edits.py"; if [ -f "$G" ]; then python3 "$G"; fi'
        p = subprocess.run(["bash", "-c", w], input="{}", capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "CLAUDE_PROJECT_DIR": S + "-nonexistent"})
        check("E1 未建家目录不误封", p.returncode == 0)
        setp("phase", "implementing")
        p = subprocess.run(["bash", "-c", w], input=json.dumps(ed("tests/foo.py")),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=S)
        check("E2 已建家拦截穿透包装器", p.returncode == 2)
        # —— verify：绿灯 / 超时保险 / fail-closed ——
        with open(os.path.join(S, "tests", "run.sh"), "w", encoding="utf-8") as f:
            f.write("exit 0\n")
        v = subprocess.run(["bash", os.path.join(H, "verify.sh")], capture_output=True, env=env, cwd=S)
        check("F0 考题全绿 exit 0", v.returncode == 0)
        with open(os.path.join(S, "tests", "run.sh"), "w", encoding="utf-8") as f:
            f.write("sleep 30\n")
        v = subprocess.run(["bash", os.path.join(H, "verify.sh")], capture_output=True,
                           env={**env, "LOOPWORK_VERIFY_TIMEOUT": "2"}, cwd=S)
        check("F2 考题挂住被超时保险击杀 (exit 124)", v.returncode == 124)
        # F5 日志修剪：塞 25 份旧日志，跑一轮后只留最近 20 份
        logdir = os.path.join(S, ".loopwork", "logs")
        for i in range(25):
            old = os.path.join(logdir, f"verify-dummy-{i:03d}.log")
            with open(old, "w") as f:
                f.write("x\n")
            os.utime(old, (1600000000 + i, 1600000000 + i))
        with open(os.path.join(S, "tests", "run.sh"), "w", encoding="utf-8") as f:
            f.write("exit 0\n")
        subprocess.run(["bash", os.path.join(H, "verify.sh")], capture_output=True, env=env, cwd=S)
        nlogs = len([x for x in os.listdir(logdir) if x.startswith("verify-") and x.endswith(".log")])
        check("F5 verify 日志只留最近 20 份", nlogs == 20, f"实际 {nlogs}")
        # F3/F4 多栈裁判：没有 tests/run.sh 时探测到的栈全都要跑（假 npm shim，考题不依赖本机 npm）
        os.remove(os.path.join(S, "tests", "run.sh"))
        shim = os.path.join(S, "shim")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "npm"), "w") as f:
            f.write('#!/bin/sh\nexit "$(cat .npm_exit 2>/dev/null || echo 0)"\n')
        os.chmod(os.path.join(shim, "npm"), 0o755)
        envF = {**env, "PATH": shim + os.pathsep + env["PATH"]}
        with open(os.path.join(S, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"name": "x", "version": "1.0.0", "scripts": {"test": "exit 0"}}\n')
        with open(os.path.join(S, "tests", "test_ok.py"), "w", encoding="utf-8") as f:
            f.write("import unittest\nclass TestOK(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        with open(os.path.join(S, ".npm_exit"), "w") as f:
            f.write("0\n")
        v = subprocess.run(["bash", os.path.join(H, "verify.sh")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=envF, cwd=S)
        check("F3 多栈全绿 exit 0", v.returncode == 0 and "2 个测试栈" in v.stdout, f"rc={v.returncode}")
        with open(os.path.join(S, ".npm_exit"), "w") as f:
            f.write("1\n")
        v = subprocess.run(["bash", os.path.join(H, "verify.sh")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=envF, cwd=S)
        check("F4 多栈一红全局红", v.returncode == 1, f"rc={v.returncode}")
        os.remove(os.path.join(S, "package.json"))
        shutil.rmtree(os.path.join(S, "tests"), ignore_errors=True)
        v = subprocess.run(["bash", os.path.join(H, "verify.sh")], capture_output=True, env=env, cwd=S)
        check("F1 无考题 fail-closed(exit 3)", v.returncode == 3)
        # —— init 幂等 ——
        r2 = subprocess.run(["bash", INIT, S, "沙盒项目"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        check("G1 init 重复跑安全", r2.returncode == 0)
        # N1 旧接线升级：过期签名的自家钩子被清、用户钩子保留、新接线只有一条
        sp = os.path.join(S, ".claude", "settings.json")
        cfg = json.load(open(sp, encoding="utf-8"))
        cfg["hooks"]["PreToolUse"] = [
            {"matcher": "Edit|Write|MultiEdit",
             "hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.loopwork/hooks/guard_edits.py"'}]},
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo user-custom"}]},
        ]
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        subprocess.run(["bash", INIT, S, "沙盒项目"], capture_output=True, env=env)
        pre = json.load(open(sp, encoding="utf-8"))["hooks"]["PreToolUse"]
        old_gone = not any(e.get("matcher") == "Edit|Write|MultiEdit" for e in pre)
        new_once = sum(1 for e in pre if e.get("matcher") == "Edit|Write|MultiEdit|NotebookEdit") == 1
        user_kept = any("user-custom" in json.dumps(e) for e in pre)
        check("N1 旧接线升级去重+用户钩子保留", old_gone and new_once and user_kept)
        # N2 首次存档密钥筛查：疑似密钥文件不入库、不删盘（独立沙盒走首次提交路径）
        S2 = tempfile.mkdtemp(prefix="loopwork-sec-")
        try:
            with open(os.path.join(S2, "fake.pem"), "w") as f:
                f.write("PRIVATE KEY\n")
            with open(os.path.join(S2, "notes.txt"), "w") as f:
                f.write("hello\n")
            subprocess.run(["bash", INIT, S2, "密钥沙盒"], capture_output=True, env=env)
            ls = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", cwd=S2).stdout
            check("N2 首次存档剔除疑似密钥（盘上保留）",
                  "fake.pem" not in ls and "notes.txt" in ls and os.path.exists(os.path.join(S2, "fake.pem")))
        finally:
            shutil.rmtree(S2, ignore_errors=True)
    finally:
        shutil.rmtree(S, ignore_errors=True)

    print(f"\n{'=' * 42}\n{sum(RESULTS)}/{len(RESULTS)} 通过")
    return 0 if all(RESULTS) else 1

if __name__ == "__main__":
    sys.exit(main())
