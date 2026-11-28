"""JSON chat completion over subscription CLIs (claude, codex), rotating on failure.

chat_json(system, user) -> parsed JSON object. Default providers are the logged-in
`claude` and `codex` CLIs (no API keys: key env vars are stripped from the child env).
Order comes from LLM_PROVIDERS (default "claude,codex"); the starting provider alternates
per call. A provider that fails (non-zero exit, rate/usage limit, timeout, bad JSON) cools
down exponentially (60 s -> 15 min). When every provider is cooling we sleep until the
first recovers. The retry budget counts elapsed time, including CLI calls
(LLM_MAX_WAIT, default 3600 seconds).

Paid HTTP APIs (DeepSeek, GLM) are a last resort only: used when LLM_ALLOW_PAID=1 and
the key is set, and only after the CLI providers are exhausted. Keys are never logged.

Env: LLM_PROVIDERS, LLM_MAX_WAIT, LLM_ALLOW_PAID, LLM_CLAUDE_MODEL (haiku),
LLM_CODEX_MODEL (gpt-6-luna), LLM_CODEX_EFFORT (low), LLM_USAGE_LOG (JSONL path).
"""
import json, os, re, shutil, signal, subprocess, sys, tempfile, time, urllib.request, urllib.error

PAID_PROVIDERS = [
    ("deepseek", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat", {}),
    ("glm", "https://open.bigmodel.cn/api/paas/v4/chat/completions", "GLM_API_KEY", "glm-4.6", {"thinking": {"type": "disabled"}}),
]
PROVIDERS = PAID_PROVIDERS            # backwards-compatible name
CLI_PROVIDERS = ("claude", "codex")
STRIP_ENV = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "GLM_API_KEY",
             "ANTHROPIC_AUTH_TOKEN", "CODEX_API_KEY")
COOL_BASE, COOL_MAX = 60.0, 900.0
RATE_RE = re.compile(r"rate.?limit|usage.?limit|quota|too many requests|\b429\b|limit reached|"
                     r"hit your limit|overloaded|insufficient.?credit|try again (later|in)", re.I)

USED = set()
_cool = {}        # provider -> [until_monotonic, consecutive_failures]
_rr = [0]         # round-robin counter
_sleep, _now = time.sleep, time.monotonic   # patched in tests


class ProviderError(Exception):
    def __init__(self, provider, kind, msg=""):
        super().__init__(f"{provider} {kind}{': ' + msg if msg else ''}")
        self.provider, self.kind = provider, kind      # kind: rate | timeout | exit | json


def _log(provider, model, rec):
    path = os.environ.get("LLM_USAGE_LOG")
    if path:
        with open(path, "a") as f:
            f.write(json.dumps({"provider": provider, "model": model, **rec}, ensure_ascii=False) + "\n")


def _err(msg):
    print("llm", msg, file=sys.stderr, flush=True)


def extract_json(text):
    """Parse a JSON object from model text: strips ``` fences, else takes the outermost {...}."""
    s = (text or "").strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s.strip("`")
        s = s.rsplit("```", 1)[0].strip()
    try:
        out = json.loads(s)
    except ValueError:
        a, b = s.find("{"), s.rfind("}")
        if a < 0 or b <= a:
            raise ValueError("no JSON object in reply")
        out = json.loads(s[a:b + 1])
    if not isinstance(out, dict):
        raise ValueError("reply is not a JSON object")
    return out


def _child_env():
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env.pop("CLAUDECODE", None)       # allow `claude -p` when run under a Claude Code session
    return env


def _run(cmd, stdin_text, timeout, cwd):
    """Run cmd in its own process group and kill the group if communication fails."""
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         cwd=cwd, env=_child_env(), text=True, encoding="utf-8", errors="replace",
                         start_new_session=True)
    try:
        out, err = p.communicate(stdin_text, timeout=timeout)
    except BaseException:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        p.communicate()
        raise
    return p.returncode, out or "", err or ""


def _prompt(system, user):
    return (system.strip() + "\n\n" + user.strip() +
            "\n\nReply with ONLY one JSON object. No prose, no markdown fences.")


def _exec(name, cmd, prompt, timeout, cwd):
    try:
        rc, out, err = _run(cmd, prompt, timeout, cwd)
    except subprocess.TimeoutExpired:
        raise ProviderError(name, "timeout", f"> {timeout}s")
    except OSError as e:
        raise ProviderError(name, "exit", type(e).__name__)
    return rc, out, err


def _fail(name, rc, text):
    kind = "rate" if RATE_RE.search(text or "") else "exit"
    raise ProviderError(name, kind, f"rc={rc} {(text or '').strip()[-200:]}")


def call_claude(system, user, timeout):
    model = os.environ.get("LLM_CLAUDE_MODEL", "haiku")
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--tools", "",
           "--no-session-persistence"]
    rc, out, err = _exec("claude", cmd, _prompt(system, user), timeout, tempfile.gettempdir())
    try:
        env = json.loads(out)
    except ValueError:
        env = None
    if rc != 0 or not isinstance(env, dict) or env.get("is_error"):
        res = env.get("result") if isinstance(env, dict) else ""
        _fail("claude", rc, "\n".join([out, err, str(res or "")]))
    try:
        obj = extract_json(env.get("result") or "")
    except ValueError as e:
        raise ProviderError("claude", "json", str(e))
    u = env.get("usage") or {}
    _log("claude", model, {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
                           "cache_read": u.get("cache_read_input_tokens", 0),
                           "cache_write": u.get("cache_creation_input_tokens", 0),
                           "cost_usd_equiv": env.get("total_cost_usd"),
                           "models": sorted((env.get("modelUsage") or {}).keys())})
    return obj


def call_codex(system, user, timeout):
    model = os.environ.get("LLM_CODEX_MODEL", "gpt-6-luna")
    effort = os.environ.get("LLM_CODEX_EFFORT", "low")
    work = tempfile.mkdtemp(prefix="llm-codex-")
    try:
        last = os.path.join(work, "last.txt")
        cmd = ["codex", "exec", "-m", model, "-c", f"model_reasoning_effort={effort}", "-s", "read-only",
               "--skip-git-repo-check", "--ephemeral", "-o", last, "-"]     # prompt on stdin
        rc, out, err = _exec("codex", cmd, _prompt(system, user), timeout, work)
        if rc != 0:
            _fail("codex", rc, out + "\n" + err)
        try:
            with open(last, encoding="utf-8") as f:
                reply = f.read()
        except OSError:
            reply = ""
        try:
            obj = extract_json(reply)
        except ValueError as e:
            raise ProviderError("codex", "json", str(e))
        m = re.search(r"tokens used[:\s]*([\d,]+)", out + "\n" + err, re.I)
        _log("codex", model, {"tokens": int(m.group(1).replace(",", "")) if m else None})
        return obj
    finally:
        shutil.rmtree(work, ignore_errors=True)


CALLERS = {"claude": call_claude, "codex": call_codex}


def _providers():
    names = [p.strip() for p in os.environ.get("LLM_PROVIDERS", "claude,codex").split(",") if p.strip()]
    bad = [n for n in names if n not in CALLERS]
    if bad:
        raise ValueError(f"unknown LLM_PROVIDERS entries: {bad} (use {sorted(CALLERS)})")
    return names


def _cool_down(name):
    st = _cool.setdefault(name, [0.0, 0])
    st[1] += 1
    wait = min(COOL_MAX, COOL_BASE * 2 ** (st[1] - 1))
    st[0] = _now() + wait
    return wait


def _paid(system, user, temperature, retries, timeout):
    last = None
    for name, url, env, model, extra in PAID_PROVIDERS:
        if not os.environ.get(env):
            continue
        body = {"model": model, "temperature": temperature, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], **extra}
        for i in range(retries):
            try:
                req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
                    "Authorization": "Bearer " + os.environ[env], "Content-Type": "application/json",
                    "User-Agent": "tvshows-pipeline/0.3"})
                r = json.load(urllib.request.urlopen(req, timeout=timeout))
                u = r.get("usage") or {}
                _log(name, model, {"hit": u.get("prompt_cache_hit_tokens", 0),
                                   "miss": u.get("prompt_cache_miss_tokens", u.get("prompt_tokens", 0)),
                                   "out": u.get("completion_tokens", 0), "paid": True})
                out = extract_json(r["choices"][0]["message"]["content"])
                USED.add(name)
                return out
            except urllib.error.HTTPError as e:
                last = f"{name} HTTP {e.code}"
                _err(last)
                if e.code in (401, 402, 403):   # auth / balance: go to next provider now
                    break
                _sleep(4 * (i + 1))
            except Exception as e:
                last = f"{name} {type(e).__name__}"
                _err(last)
                _sleep(3 * (i + 1))
    return last


def chat_json(system, user, temperature=0.2, retries=3, timeout=240):
    """Return the parsed JSON object. `temperature` applies to paid APIs only (CLIs ignore it).
    `retries` caps non-rate-limit failures per CLI provider within this call, so one bad prompt
    cannot spin for LLM_MAX_WAIT; rate/usage limits only cool the provider and are waited out."""
    started = _now()
    names = _providers()
    max_wait = float(os.environ.get("LLM_MAX_WAIT", "3600"))
    start = _rr[0] % len(names) if names else 0
    _rr[0] += 1
    order = names[start:] + names[:start]
    hard = {n: 0 for n in order}
    last = None
    while True:
        live = [n for n in order if hard[n] < max(1, retries)]
        if not live:
            break
        ready = [n for n in live if _cool.get(n, [0.0, 0])[0] <= _now()]
        for name in ready:
            try:
                out = CALLERS[name](system, user, timeout)
            except ProviderError as e:
                last = str(e)
                if e.kind != "rate":
                    hard[name] += 1
                _err(f"{last} -> cooling {name} {_cool_down(name):.0f}s")
                continue
            _cool.pop(name, None)
            USED.add(name)
            return out
        live = [n for n in order if hard[n] < max(1, retries)]
        if not live:
            break
        now = _now()
        waited = now - started
        pause = max(0.0, min(_cool.get(n, [0.0, 0])[0] for n in live) - now)
        if waited >= max_wait or waited + pause > max_wait:
            break
        if pause <= 0:
            continue
        _err(f"all CLI providers cooling; sleeping {pause:.0f}s (waited {waited:.0f}/{max_wait:.0f}s)")
        _sleep(pause)
    if os.environ.get("LLM_ALLOW_PAID") == "1" and any(os.environ.get(p[2]) for p in PAID_PROVIDERS):
        _err("CLI providers exhausted; falling back to paid API (LLM_ALLOW_PAID=1)")
        got = _paid(system, user, temperature, retries, timeout)
        if isinstance(got, dict):
            return got
        last = got or last
    raise RuntimeError("all LLM providers failed: " + str(last))
