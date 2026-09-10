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
        for f in ("guard_rules.py", "guard_edits.py", "guard_bash.py", "guard_ask.py", "stop_batch.py",
                  "audit_log.py", "progress.py", "verify.sh"):
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
        check("A9 改钩子接线 settings.json 被拦", hook("guard_edits.py", ed(".claude/settings.json")) == 2)
        check("A10 改 settings.local.json 被拦", hook("guard_edits.py", ed(".claude/settings.local.json")) == 2)
        check("A11 改批次 flag 被拦", hook("guard_edits.py", ed(".loopwork/batch.flag")) == 2)
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
        # —— guard_bash：多行脚本 / 一段多个写命令（换行不是分隔符 + 只看第一个匹配 = 两个洞）——
        check("B24 换行后的危险删除被拦", hook("guard_bash.py", ba("rm out.log\n" + RM)) == 2)
        check("B25 换行后 sed 改 spec 被拦",
              hook("guard_bash.py", ba("sed -i s/x/y/ notes.txt\nsed -i s/a/b/ spec.md")) == 2)
        check("B26 换行后 mv 搬考题被拦", hook("guard_bash.py", ba("mv a.txt b.txt\nmv tests/exam.py /tmp/")) == 2)
        check("B27 换行后 cp 覆盖考题被拦", hook("guard_bash.py", ba("cp a.txt b.txt\ncp hack.py tests/foo.py")) == 2)
        check("B28 换行后 checkout 回滚考题被拦",
              hook("guard_bash.py", ba("git checkout -b feature\ngit checkout HEAD~1 -- tests/exam.py")) == 2)
        check("B29 换行后 restore 回滚考题被拦",
              hook("guard_bash.py", ba("git restore --staged notes.txt\ngit restore --source=HEAD~1 tests/")) == 2)
        check("B30 换行后 truncate 清空 state 被拦",
              hook("guard_bash.py", ba("truncate -s 0 out.log\ntruncate -s 0 .loopwork/state.json")) == 2)
        check("B31 一段内第二个 tee 写围栏被拦",
              hook("guard_bash.py", ba("tee out.log < a.txt\ntee .loopwork/hooks/g.py < hack.py")) == 2)
        check("B32 多行脚本里的 heredoc 覆盖考题被拦",
              hook("guard_bash.py", ba("echo start\ncat <<'EOF' > tests/foo.py\ncheat\nEOF")) == 2)
        check("B33 多行正当命令放行", hook("guard_bash.py", ba("pytest tests/ -q\ngit status\ngit add tests/")) == 0)
        # —— guard_bash：关围栏的三个文件（钩子接线 / 批次 flag）——
        check("B34 重定向覆盖钩子接线被拦",
              hook("guard_bash.py", ba("echo '{}' > .claude/settings.json")) == 2)
        check("B35 sed 改 settings.local.json 被拦",
              hook("guard_bash.py", ba("sed -i s/hooks/x/ .claude/settings.local.json")) == 2)
        RMF = "rm " + ".loopwork/batch.flag"
        check("B36 删批次 flag 被拦（停批归用户和 Stop 钩子）", hook("guard_bash.py", ba(RMF)) == 2)
        RMG = "rm " + ".loopwork/hooks/guard_bash.py"
        check("B37 删围栏脚本被拦", hook("guard_bash.py", ba(RMG)) == 2)
        check("B38 touch 开批放行", hook("guard_bash.py", ba("touch .loopwork/batch.flag")) == 0)
        check("B39 删普通文件放行", hook("guard_bash.py", ba("rm out.log")) == 0)
        # —— guard_bash：改历史 / 销毁证据（存档只增不减，改得动的历史不算证据）——
        def hban(name, cmd, want):
            check(name, hook("guard_bash.py", ba(cmd)) == want, cmd)
        hban("R1 commit --amend 被拦", "git commit --amend -m 改一下", 2)
        hban("R2 rebase 被拦", "git rebase -i HEAD~3", 2)
        hban("R3 reset --hard 被拦", "git reset --hard HEAD~1", 2)
        hban("R4 reset 搬指针（无模式旗标）被拦", "git reset abc1234", 2)
        hban("R5 filter-branch 被拦", "git filter-branch --tree-filter true HEAD", 2)
        hban("R6 filter-repo 被拦", "git filter-repo --path tests/", 2)
        hban("R7 update-ref 被拦", "git update-ref refs/heads/main abc1234", 2)
        hban("R8 branch -D 被拦", "git branch -D feature", 2)
        hban("R9 stash 被拦（整条）", "git stash push -m wip", 2)
        hban("R10 reflog expire 被拦", "git reflog expire --expire=now --all", 2)
        hban("R11 gc --prune 被拦", "git gc --prune=now", 2)
        hban("R12 clean 被拦", "git clean -fd", 2)
        hban("R13 switch --discard-changes 被拦", "git switch --discard-changes main", 2)
        hban("R14 push --delete 被拦", "git push --delete origin feature", 2)
        hban("R15 sudo 前缀照样拦", "sudo git reset --hard HEAD~1", 2)
        hban("R16 换行后的改写也拦", "git status\ngit rebase main", 2)
        hban("R17 git -C 别处改写也拦", "git -C /tmp/x rebase main", 2)
        # 必须放行的日常动作（误伤这些等于把工作流砸了）
        hban("R18 add 放行", "git add -A", 0)
        hban("R19 commit 放行", "git commit -m 存档: T01 记一笔", 0)
        hban("R20 提交信息里出现禁词不误伤", 'git commit -m "clean up rebase and stash"', 0)
        hban("R21 log 放行", "git log --oneline -5", 0)
        hban("R22 diff 放行", "git diff --numstat HEAD", 0)
        hban("R23 status 放行", "git status --short", 0)
        hban("R24 checkout -b 放行", "git checkout -b feature", 0)
        hban("R25 switch -c 放行", "git switch -c feature", 0)
        hban("R26 tag 放行", "git tag v1.0", 0)
        hban("R27 reset -- 路径（取消暂存）放行", "git reset -- notes.txt", 0)
        hban("R28 reset HEAD -- 路径 放行", "git reset HEAD -- notes.txt", 0)
        hban("R29 branch -a 放行（-a 不是 -f/-D）", "git branch -a", 0)
        hban("R30 gc 不带 --prune 放行", "git gc", 0)
        hban("R31 reflog 只读放行", "git reflog -n 5", 0)
        # —— JOURNAL.md 只许追加（日志是历史，只增不减）——
        check("J1 Edit 改 JOURNAL 被拦", hook("guard_edits.py", ed("JOURNAL.md")) == 2)
        check("J2 单尖括号覆盖 JOURNAL 被拦", hook("guard_bash.py", ba("echo x > JOURNAL.md")) == 2)
        check("J3 双尖括号追加 JOURNAL 放行", hook("guard_bash.py", ba("echo x >> JOURNAL.md")) == 0)
        check("J4 sed -i 改写 JOURNAL 被拦",
              hook("guard_bash.py", ba("sed -i /T01/d JOURNAL.md")) == 2)
        RMJ = "rm " + "JOURNAL.md"
        check("J5 删 JOURNAL 被拦", hook("guard_bash.py", ba(RMJ)) == 2)
        check("J6 tee -a 追加 JOURNAL 放行", hook("guard_bash.py", ba("tee -a JOURNAL.md < note.txt")) == 0)
        check("J7 tee 覆盖 JOURNAL 被拦", hook("guard_bash.py", ba("tee JOURNAL.md < note.txt")) == 2)
        check("J8 mv 搬走 JOURNAL 被拦", hook("guard_bash.py", ba("mv JOURNAL.md /tmp/")) == 2)
        jp = os.path.join(S, "JOURNAL.md")
        before = open(jp, encoding="utf-8").read()
        rj = subprocess.run(["python3", os.path.join(H, "progress.py"), "journal", "T99 ✅ 手工一行"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=S)
        after = open(jp, encoding="utf-8").read()
        check("J9 progress.py journal 追加一行", rj.returncode == 0 and after.startswith(before)
              and after.rstrip().endswith("T99 ✅ 手工一行"), rj.stderr[-160:])
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
        fp = lambda: open(flag).read().strip().split(",")
        check("D2 flag 记起点+顶回计数+进展指纹", fp()[:4] == ["0", "0", "0", "1"] and len(fp()[4]) == 12)
        rc, err = hook2("stop_batch.py", {})
        check("D2b 无进展第 1 次仅警告", rc == 2 and "没涨" in err and fp()[:4] == ["0", "0", "1", "2"])
        rc, err = hook2("stop_batch.py", {})
        check("D2c 连续 2 次无进展自动停批", rc == 2 and "打转" in err and not os.path.exists(flag))
        # 无进展 = 轮数没涨 ∧ HEAD 没动 ∧ tasks.md 没动 ∧ BLOCKED.md 没动。
        # 只看轮数会把「一条硬任务跨两次顶回」误判成打转——两版量同一把尺（guard_rules.PROGRESS_FILES）。
        gitD = lambda *a: subprocess.run(["git"] + list(a), capture_output=True, text=True,
                                         encoding="utf-8", errors="replace", env=env, cwd=S)
        open(flag, "w").close()
        hook("stop_batch.py", {})                       # 第 1 次：记下起点与指纹
        with open(os.path.join(S, "BLOCKED.md"), "a", encoding="utf-8") as f:
            f.write("## B01 · 图表库选择\n")             # 轮数仍没涨，但问题本新增了一条
        rc, err = hook2("stop_batch.py", {})
        check("D2d 轮数没涨但问题本新增 → 算进展，不计打转",
              rc == 2 and "没涨" not in err and fp()[2] == "0", err[-160:])
        with open(os.path.join(S, "tasks.md"), "a", encoding="utf-8") as f:
            f.write("- [ ] T04 d\n")                    # 轮数仍没涨，但 tasks.md 动了
        rc, err = hook2("stop_batch.py", {})
        check("D2e 轮数没涨但 tasks.md 动了 → 算进展，不计打转",
              rc == 2 and "没涨" not in err and fp()[2] == "0", err[-160:])
        gitD("commit", "-qm", "存档: 进展指纹用例", "--allow-empty")
        rc, err = hook2("stop_batch.py", {})
        check("D2f 轮数没涨但落了新存档 → 算进展，不计打转",
              rc == 2 and "没涨" not in err and fp()[2] == "0", err[-160:])
        rc, err = hook2("stop_batch.py", {})
        check("D2g 三样全没动才计无进展", rc == 2 and "没涨" in err and fp()[2] == "1", err[-160:])
        os.remove(flag)
        os.remove(os.path.join(S, "BLOCKED.md"))
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [ ] T01 a\n- [ ] T02 b\n- [ ] T03 c\n")
        open(flag, "w").close()
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
        # —— 检测门：基线锚定 + 相位纪律（与批模式共用同一笔顶回账）——
        state_p = os.path.join(S, ".loopwork", "state.json")
        def stbl():
            return json.load(open(state_p, encoding="utf-8")).get("stop_blocks", 0)
        def git(*a):
            return subprocess.run(["git"] + list(a), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", env=env, cwd=S)
        setp("stop_blocks", 0); setp("stage", "4")
        check("K1 进循环阶段但无违规放行", hook("stop_batch.py", {}) == 0)
        setp("last_round_commit", "deadbeef" * 5)
        rc, err = hook2("stop_batch.py", {})
        check("K2 基线在 git 历史中不可达被顶回", rc == 2 and "不可达" in err, err[-160:])
        check("K3 非批模式顶回记在 state.stop_blocks", stbl() == 1)
        head1 = git("rev-parse", "HEAD").stdout.strip()
        setp("last_round_commit", head1)
        check("K4 基线恢复后放行且顶回计数清零", hook("stop_batch.py", {}) == 0 and stbl() == 0)
        os.makedirs(os.path.join(S, "tests"), exist_ok=True)
        with open(os.path.join(S, "tests", "exam.py"), "w", encoding="utf-8") as f:
            f.write("def test_x():\n    assert 1\n")
        setp("phase", "implementing")
        rc, err = hook2("stop_batch.py", {})
        check("K5 实现期未存档的考题改动被顶回", rc == 2 and "未存档" in err and "tests/exam.py" in err, err[-160:])
        git("add", "tests/exam.py"); git("commit", "-qm", "存档: 红考题")
        rc, err = hook2("stop_batch.py", {})
        check("K6 红考题存了档但忘推基线被顶回", rc == 2 and "存档即推进基线" in err, err[-160:])
        setp("last_round_commit", git("rev-parse", "HEAD").stdout.strip())
        check("K7 推进基线后放行（存档即推进基线）", hook("stop_batch.py", {}) == 0)
        with open(os.path.join(S, "tests", "exam2.py"), "w", encoding="utf-8") as f:
            f.write("def test_y():\n    assert 1\n")
        open(flag, "w").close()
        setp("round_count", 0)
        rc, err = hook2("stop_batch.py", {})
        check("K8 批模式下检测门先于批逻辑，顶回记进 flag 第 4 段",
              rc == 2 and "检测门" in err and fp()[3] == "1", err[-120:])
        with open(flag, "w", encoding="utf-8") as f:
            f.write("0,,0,6")  # 已顶回 6 次
        rc, err = hook2("stop_batch.py", {})
        check("K9 检测门顶回达上限优雅停机+摘 flag", rc == 2 and "停机" in err and not os.path.exists(flag))
        check("K10 停机后下一轮强制放行一次（掐断平台连续顶回计数）", hook("stop_batch.py", {}) == 0)
        os.remove(os.path.join(S, "tests", "exam2.py"))
        setp("phase", "test-writing"); setp("last_round_commit", "")
        # —— 审计账本只增不减（与 Codex 版同一把锁，两版不许一版有一版没有）——
        audit_p = os.path.join(S, ".loopwork", "logs", "audit.jsonl")
        os.makedirs(os.path.dirname(audit_p), exist_ok=True)
        aline = '{"ts":"x","tool":"Bash","summary":"a"}\n'
        def wr_audit(n):
            with open(audit_p, "w", encoding="utf-8") as f:
                f.write(aline * n)
        wr_audit(20); hook("stop_batch.py", {})  # 先记下基准
        wr_audit(1)
        rc, err = hook2("stop_batch.py", {})
        check("K11 审计账本被抹短被顶回", rc == 2 and "审计" in err, err[-160:])
        check("K12 抹账只报一次（基准已重置，不把会话钉死）", hook("stop_batch.py", {}) == 0)
        wr_audit(20); hook("stop_batch.py", {})
        os.replace(audit_p, audit_p + ".1")
        wr_audit(1)
        check("K13 轮转后账本变短不误报", hook("stop_batch.py", {}) == 0)
        os.remove(audit_p); os.remove(audit_p + ".1")
        setp("audit_bytes", 0)
        setp("stage", "0")
        # —— guard_ask：挂机批禁提问 ——
        ask = {"tool_name": "AskUserQuestion", "tool_input": {}, "cwd": S}
        open(flag, "w").close()
        rc, err = hook2("guard_ask.py", ask)
        check("I1 挂机批弹提问被拦+指路", rc == 2 and "BLOCKED" in err)
        os.remove(flag)
        check("I2 非批模式提问放行", hook("guard_ask.py", ask) == 0)
        # —— audit_log：只记账不拦人 ——
        audit = os.path.join(S, ".loopwork", "logs", "audit.jsonl")
        rc_a = hook("audit_log.py", {"tool_name": "Bash", "tool_input": {"command": "pytest tests/ -q"}, "cwd": S})
        rc_b = hook("audit_log.py", {"tool_name": "Edit", "tool_input": {"file_path": "src/app.py"}, "cwd": S})
        lines = [json.loads(x) for x in open(audit, encoding="utf-8").read().splitlines() if x.strip()]
        check("A1 审计账本追加两行且从不拦人（rc=0）",
              rc_a == 0 and rc_b == 0 and len(lines) == 2)
        check("A2 账本记下工具名+落点+时间戳",
              lines[0]["tool"] == "Bash" and lines[0]["summary"].startswith("pytest")
              and lines[1]["tool"] == "Edit" and lines[1]["summary"] == "src/app.py"
              and len(lines[0]["ts"]) >= 19, str(lines)[:160])
        check("A3 PostToolUse 已接线", '"PostToolUse"' in
              open(os.path.join(S, ".claude", "settings.json"), encoding="utf-8").read())
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
        # —— T 系列：判卷预警 tripwire（绿灯不等于没作弊；只出声，不改判决） ——
        def vrun():
            return subprocess.run(["bash", os.path.join(H, "verify.sh")], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", env=env, cwd=S)

        def gitS(*a):
            return subprocess.run(["git", *a], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", env=env, cwd=S)
        os.makedirs(os.path.join(S, "src"), exist_ok=True)
        with open(os.path.join(S, "tests", "exam_t.py"), "w", encoding="utf-8") as f:
            f.write("def test_a():\n    assert 1 == 1\n\ndef test_b():\n    assert 2 == 2\n")
        with open(os.path.join(S, "src", "t.py"), "w", encoding="utf-8") as f:
            f.write("def f():\n    return g()\n")
        gitS("add", "-A"); gitS("commit", "-qm", "tripwire 起点")
        setp("phase", "implementing")
        v = vrun()
        check("T1 干净轮一声不吭（预警不制造噪音）",
              v.returncode == 0 and "判卷预警" not in v.stdout, v.stdout[-200:])
        with open(os.path.join(S, "tests", "exam_t.py"), "w", encoding="utf-8") as f:
            f.write("import pytest\n\n@pytest.mark.skip\ndef test_a():\n    pass\n\ndef test_b():\n    pass\n")
        with open(os.path.join(S, "src", "t.py"), "w", encoding="utf-8") as f:
            f.write("# type: ignore\ndef f():\n    try:\n        return g()\n    except Exception:\n        pass\n")
        v = vrun()
        check("T2 四种作弊痕迹被逐条点名，且判决不变（还是 exit 0）",
              v.returncode == 0 and v.stdout.count("⚠️ 判卷预警：") == 4
              and all(k in v.stdout for k in ("抑制标记", "跳过考题", "吞异常", "删掉了")),
              v.stdout[-400:])
        gitS("checkout", "--", "tests/exam_t.py", "src/t.py")
        os.remove(os.path.join(S, "tests", "exam_t.py")); os.remove(os.path.join(S, "src", "t.py"))
        gitS("add", "-A"); gitS("commit", "-qm", "tripwire 收尾")
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
        # —— selftest：装机自检（全绿 exit 0；接线被改坏 exit 1）——
        S3 = tempfile.mkdtemp(prefix="loopwork-self-")
        try:
            subprocess.run(["bash", INIT, S3, "自检沙盒"], capture_output=True, env=env)
            SELF = os.path.join(os.path.dirname(INIT), "selftest.sh")
            t = subprocess.run(["bash", SELF, S3], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env={**os.environ}, cwd=S3)
            check("S1 自检全绿 exit 0", t.returncode == 0 and "0 失败" in t.stdout,
                  t.stdout[-300:] + t.stderr[-160:])
            sp3 = os.path.join(S3, ".claude", "settings.json")
            c3 = json.load(open(sp3, encoding="utf-8"))
            c3["hooks"].pop("Stop", None)
            with open(sp3, "w", encoding="utf-8") as f:
                json.dump(c3, f, ensure_ascii=False, indent=2)
            t2 = subprocess.run(["bash", SELF, S3], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env={**os.environ}, cwd=S3)
            check("S2 接线被摘掉时自检报 ❌ 并 exit 1",
                  t2.returncode == 1 and "Stop/stop_batch.py" in t2.stdout, t2.stdout[-200:])
        finally:
            shutil.rmtree(S3, ignore_errors=True)

        # ---- L 系列：取证账本 blocks.jsonl（拦了什么要留痕，顶回时要说出来） ----
        LOG = os.path.join(S, ".loopwork", "logs", "blocks.jsonl")
        nline = lambda p: sum(1 for _ in open(p, encoding="utf-8")) if os.path.exists(p) else 0
        setp("stage", "1"); setp("phase", "implementing")   # 出循环阶段：检测门不插话，只看取证
        hook("stop_batch.py", {})                           # 先推平水位线，从干净起点数
        base = nline(LOG)
        hook("guard_edits.py", ed("tests/ledger.py"))
        hook("guard_bash.py", ba("sed -i s/a/b/ spec.md"))
        rows = [json.loads(l) for l in open(LOG, encoding="utf-8")][base:] if os.path.exists(LOG) else []
        check("L1 两次拦截留下两行取证，字段齐、相位对",
              len(rows) == 2 and all({"ts", "tool", "target", "rule", "phase"} <= set(r) for r in rows)
              and [r["phase"] for r in rows] == ["implementing"] * 2, str(rows)[:200])
        with open(os.path.join(S, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [ ] T01 a\n- [ ] T02 b\n- [ ] T03 c\n")
        open(flag, "w").close()
        setp("round_count", 0); setp("batch_size", 2)
        rc, err = hook2("stop_batch.py", {})
        check("L2 顶回理由带上本轮拦截数", rc == 2 and "拦下 2 次" in err, err[-200:])
        setp("round_count", 1)
        rc, err = hook2("stop_batch.py", {})
        check("L3 水位线已推进：同一批拦截不重复计入下一轮",
              rc == 2 and "[取证]" not in err, err[-200:])

        # ---- V 系列：判卷员定义不许悄悄消失或缩水（两版同一份职责，锁住） ----
        SKILL = os.path.join(REPO, "loopwork")
        rv_p = os.path.join(SKILL, "agents", "reviewer.md")
        check("V1 判卷员定义在", os.path.exists(rv_p))
        rv = open(rv_p, encoding="utf-8").read() if os.path.exists(rv_p) else ""
        check("V2 判卷员四段齐全（合规/质量/作弊清单/考题盲区 + 固定输出格式）",
              all(k in rv for k in ("第一段 · 合规", "第二段 · 质量", "第三段 · 作弊清单",
                                    "第四段 · 考题盲区", "判卷结论：", "N 对 M", "verify.sh")))
        check("V5 作弊清单八条齐全，且如实交代自动探测只查得动前五条",
              all(k in rv for k in ("空转修复", "断言放水", "断言消失", "吞异常",
                                    "抑制检查", "假重构", "查表蒙混", "功能孤岛"))
              and "0/27" in rv and "只查得动 1–5" in rv)
        check("V3 判卷员如实交代「只读」靠什么兜着（CC 没有系统级只读沙箱）",
              "没有系统级只读沙箱" in rv and "guard_edits.py" in rv)
        s5 = open(os.path.join(SKILL, "references", "stage-5-accept.md"), encoding="utf-8").read()
        check("V4 stage-5 指向判卷员且不吹成物理隔离",
              "agents/reviewer.md" in s5 and "不是系统沙箱" in s5)
        s0 = open(os.path.join(SKILL, "references", "stage-0-setup.md"), encoding="utf-8").read()
        check("V6 stage-0 交代围栏管不到供应链：清点别人的钩子 + 搜来的安装指引只转述不执行",
              all(k in s0 for k in (".claude/settings.json", "AgentBaiting", "只转述",
                                    "装什么由用户指定", "不再询问")))

        # ---- W 系列：存档闸（先红后绿）。CC 版模型自己 git commit，闸就设在 commit 那一刻。
        # 红票从 git 历史里读、不从状态开关里读：PreToolUse 看不见 commit 到底成没成，
        # 存出来的开关会被一次故意失败的 commit 白白骗走一张票，历史骗不了。
        os.makedirs(os.path.join(S, "src"), exist_ok=True)
        with open(os.path.join(S, "src", "w.py"), "w", encoding="utf-8") as f:
            f.write("def w():\n    return 1\n")
        git("add", "-A"); git("commit", "-qm", "存档: 闸门起点（带实现物）")
        GC = "git add -A && git commit -m 存档"
        appw = lambda s: open(os.path.join(S, "src", "w.py"), "a", encoding="utf-8").write(s)
        setp("phase", "implementing")
        appw("def w2():\n    return 2\n")
        check("W1 实现期落绿存档但手里没红票被拦", hook("guard_bash.py", ba(GC)) == 2)
        with open(os.path.join(S, "tests", "exam_w.py"), "w", encoding="utf-8") as f:
            f.write("def test_w():\n    assert False\n")
        git("add", "tests/exam_w.py"); git("commit", "-qm", "存档: W 红考题")
        check("W2 红存档落进历史后，同一条绿存档命令就放行了", hook("guard_bash.py", ba(GC)) == 0)
        git("add", "-A"); git("commit", "-qm", "存档: W 绿实现")
        appw("def w3():\n    return 3\n")
        check("W3 一张红票只管一轮：绿存档之后再落实现又被拦", hook("guard_bash.py", ba(GC)) == 2)
        git("checkout", "--", "src/w.py")
        with open(os.path.join(S, "JOURNAL.md"), "a", encoding="utf-8") as f:
            f.write("- [存档] 记事一行\n")
        check("W4 只动台账的记事档不归这道闸管（它不是绿存档）", hook("guard_bash.py", ba(GC)) == 0)
        setp("phase", "test-writing")
        appw("def w4():\n    return 4\n")
        check("W5 非实现期闸门是开的：Stage 0–3 的规格/计划档照样存得下",
              hook("guard_bash.py", ba(GC)) == 0)
        check("W6 点名 add 只算点名的落点：git add tests/ 不会被当成整个工作区",
              hook("guard_bash.py", ba("git add tests/ && git commit -m 红")) == 0)
    finally:
        shutil.rmtree(S, ignore_errors=True)

    print(f"\n{'=' * 42}\n{sum(RESULTS)}/{len(RESULTS)} 通过")
    return 0 if all(RESULTS) else 1

if __name__ == "__main__":
    sys.exit(main())
