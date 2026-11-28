"""Tests for pipeline/llm.py CLI rotation (no network, no real CLI calls: llm._run is faked).
Run: python3 -B -m unittest tests/python/test_llm_cli.py"""
import json, os, subprocess, sys, unittest
from unittest import mock
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

import llm


def claude_ok(obj, cost=0.01):
    return 0, json.dumps({"type": "result", "is_error": False, "result": json.dumps(obj),
                          "usage": {"input_tokens": 10, "output_tokens": 5}, "total_cost_usd": cost,
                          "modelUsage": {"claude-haiku": {}}}), ""


class FakeRun:
    """Replaces llm._run. `script` maps provider -> list of results (tuple, Exception, or callable)."""
    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def __call__(self, cmd, stdin_text, timeout, cwd):
        name = cmd[0]
        self.calls.append((name, cmd, stdin_text, cwd))
        step = self.script[name].pop(0)
        if isinstance(step, BaseException):
            raise step
        if callable(step):
            return step(cmd)
        return step


def codex_reply(text, stdout="tokens used\n1,234\n"):
    def run(cmd):
        with open(cmd[cmd.index("-o") + 1], "w") as f:
            f.write(text)
        return 0, stdout, ""
    return run


class Base(unittest.TestCase):
    def setUp(self):
        llm._cool.clear(); llm.USED.clear(); llm._rr[0] = 0
        self.clock = [1000.0]
        self.slept = []
        def sleep(s):
            self.slept.append(s); self.clock[0] += s
        p = [mock.patch.object(llm, "_now", lambda: self.clock[0]),
             mock.patch.object(llm, "_sleep", sleep),
             mock.patch.dict(os.environ, {"LLM_PROVIDERS": "claude,codex"}, clear=False)]
        for x in p:
            x.start(); self.addCleanup(x.stop)
        for k in ("LLM_ALLOW_PAID", "LLM_MAX_WAIT", "LLM_USAGE_LOG", "DEEPSEEK_API_KEY", "GLM_API_KEY"):
            os.environ.pop(k, None)
        self.errs = mock.patch.object(llm, "_err", lambda m: None); self.errs.start(); self.addCleanup(self.errs.stop)

    def fake(self, script):
        f = FakeRun(script)
        p = mock.patch.object(llm, "_run", f); p.start(); self.addCleanup(p.stop)
        return f


class ExtractJson(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(llm.extract_json('{"a": 1}'), {"a": 1})

    def test_fenced(self):
        self.assertEqual(llm.extract_json('```json\n{"a": [1, 2]}\n```'), {"a": [1, 2]})

    def test_prose_around(self):
        self.assertEqual(llm.extract_json('Sure! {"t": {"x": "}"}} hope it helps'), {"t": {"x": "}"}})

    def test_invalid(self):
        for bad in ("", "no json here", "[1, 2]", "{broken"):
            with self.assertRaises(ValueError):
                llm.extract_json(bad)


class Commands(Base):
    def test_claude_command_prompt_and_log(self):
        f = self.fake({"claude": [claude_ok({"ok": 1}, cost=0.02)]})
        log = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"llm-test-{os.getpid()}.jsonl")
        self.addCleanup(lambda: os.path.exists(log) and os.remove(log))
        with mock.patch.dict(os.environ, {"LLM_USAGE_LOG": log}):
            self.assertEqual(llm.chat_json("SYS", "USER"), {"ok": 1})
        name, cmd, stdin, cwd = f.calls[0]
        self.assertEqual(cmd[:8], ["claude", "-p", "--model", "haiku", "--output-format", "json", "--tools", ""])
        self.assertLess(stdin.index("SYS"), stdin.index("USER"))
        self.assertIn("Reply with ONLY one JSON object", stdin)
        self.assertNotEqual(os.path.realpath(cwd), ROOT)
        with open(log) as fh:
            rec = json.loads(fh.read().strip())
        self.assertEqual((rec["provider"], rec["cost_usd_equiv"], rec["in"], rec["out"]), ("claude", 0.02, 10, 5))
        self.assertNotIn("cost_usd", rec)
        self.assertEqual(llm.USED, {"claude"})

    def test_codex_command_reads_output_file(self):
        os.environ["LLM_PROVIDERS"] = "codex"
        f = self.fake({"codex": [codex_reply('```json\n{"t": ["x"]}\n```')]})
        self.assertEqual(llm.chat_json("S", "U"), {"t": ["x"]})
        _, cmd, stdin, cwd = f.calls[0]
        for part in ("exec", "-m", "gpt-6-luna", "model_reasoning_effort=low", "read-only",
                     "--skip-git-repo-check", "--ephemeral", "-o"):
            self.assertIn(part, cmd)
        self.assertIn("U", stdin)
        self.assertFalse(os.path.exists(cwd))          # scratch dir cleaned up
        self.assertEqual(llm.USED, {"codex"})

    def test_child_env_strips_keys(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "x", "ANTHROPIC_API_KEY": "x",
                                          "DEEPSEEK_API_KEY": "x", "GLM_API_KEY": "x", "KEEP": "1"}):
            env = llm._child_env()
        for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "GLM_API_KEY"):
            self.assertNotIn(k, env)
        self.assertEqual(env["KEEP"], "1")

    def test_real_run_kills_on_timeout(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            llm._run([sys.executable, "-c", "import time; time.sleep(30)"], "", 0.5, "/tmp")


class Rotation(Base):
    def test_round_robin_start_alternates(self):
        f = self.fake({"claude": [claude_ok({"n": 1}), claude_ok({"n": 3})],
                       "codex": [codex_reply('{"n": 2}')]})
        self.assertEqual([llm.chat_json("s", "u")["n"] for _ in range(3)], [1, 2, 3])
        self.assertEqual([c[0] for c in f.calls], ["claude", "codex", "claude"])

    def test_rate_limit_rotates_and_cools(self):
        f = self.fake({"claude": [(1, "", "Error: You've hit your usage limit")],
                       "codex": [codex_reply('{"ok": true}'), codex_reply('{"ok": 2}')]})
        self.assertEqual(llm.chat_json("s", "u"), {"ok": True})
        self.assertGreater(llm._cool["claude"][0], self.clock[0])
        # next call would start at codex anyway; claude is cooling so it is skipped
        self.assertEqual(llm.chat_json("s", "u"), {"ok": 2})
        self.assertEqual([c[0] for c in f.calls], ["claude", "codex", "codex"])
        self.assertEqual(llm.USED, {"codex"})

    def test_timeout_and_invalid_json_rotate(self):
        self.fake({"claude": [subprocess.TimeoutExpired("claude", 1)],
                   "codex": [codex_reply("not json at all")]})
        with mock.patch.dict(os.environ, {"LLM_MAX_WAIT": "0"}):
            with self.assertRaises(RuntimeError):
                llm.chat_json("s", "u")
        self.assertIn("claude", llm._cool); self.assertIn("codex", llm._cool)

    def test_claude_is_error_envelope(self):
        bad = (0, json.dumps({"is_error": True, "result": "Claude AI usage limit reached"}), "")
        self.fake({"claude": [bad], "codex": [codex_reply('{"ok": 1}')]})
        self.assertEqual(llm.chat_json("s", "u"), {"ok": 1})

    def test_exponential_cooldown_capped(self):
        waits = [llm._cool_down("claude") for _ in range(8)]
        self.assertEqual(waits[:5], [60, 120, 240, 480, 900])
        self.assertEqual(max(waits), 900)

    def test_all_cooling_sleeps_then_succeeds(self):
        rl = (1, "", "429 Too Many Requests")
        self.fake({"claude": [rl, claude_ok({"ok": "late"})], "codex": [rl]})
        self.assertEqual(llm.chat_json("s", "u"), {"ok": "late"})
        self.assertEqual(len(self.slept), 1)
        self.assertAlmostEqual(self.slept[0], 60, delta=0.01)

    def test_all_cooling_raises_after_max_wait(self):
        rl = (1, "", "rate limit exceeded")
        self.fake({"claude": [rl] * 50, "codex": [rl] * 50})
        with mock.patch.dict(os.environ, {"LLM_MAX_WAIT": "500"}):
            with self.assertRaises(RuntimeError):
                llm.chat_json("s", "u")
        self.assertLessEqual(sum(self.slept), 500)
        self.assertGreater(len(self.slept), 0)

    def test_hard_failures_capped_by_retries(self):
        bad = (2, "", "some crash")
        f = self.fake({"claude": [bad] * 5, "codex": [bad] * 5})
        with self.assertRaises(RuntimeError):
            llm.chat_json("s", "u", retries=2)
        self.assertEqual(len(f.calls), 4)


class PaidFallback(Base):
    def setUp(self):
        super().setUp()
        self.rl = (1, "", "usage limit")
        os.environ["LLM_MAX_WAIT"] = "0"
        self.addCleanup(lambda: os.environ.pop("LLM_MAX_WAIT", None))

    def test_disabled_by_default_even_with_key(self):
        self.fake({"claude": [self.rl], "codex": [self.rl]})
        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}), \
             mock.patch.object(llm.urllib.request, "urlopen") as up:
            with self.assertRaises(RuntimeError):
                llm.chat_json("s", "u")
            up.assert_not_called()

    def test_flag_without_key_does_nothing(self):
        self.fake({"claude": [self.rl], "codex": [self.rl]})
        with mock.patch.dict(os.environ, {"LLM_ALLOW_PAID": "1"}), \
             mock.patch.object(llm.urllib.request, "urlopen") as up:
            with self.assertRaises(RuntimeError):
                llm.chat_json("s", "u")
            up.assert_not_called()

    def test_enabled_with_flag_and_key_after_cli_exhausted(self):
        f = self.fake({"claude": [self.rl], "codex": [self.rl]})
        import io
        resp = io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"paid": 1}'}}],
                                      "usage": {"prompt_tokens": 3}}).encode())
        with mock.patch.dict(os.environ, {"LLM_ALLOW_PAID": "1", "DEEPSEEK_API_KEY": "sk-test"}), \
             mock.patch.object(llm.urllib.request, "urlopen", return_value=resp) as up:
            self.assertEqual(llm.chat_json("s", "u"), {"paid": 1})
            up.assert_called_once()
        self.assertEqual(len(f.calls), 2)              # both CLIs tried first
        self.assertEqual(llm.USED, {"deepseek"})


if __name__ == "__main__":
    unittest.main()
