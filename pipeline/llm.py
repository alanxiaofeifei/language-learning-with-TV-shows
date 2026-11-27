"""JSON chat completion: DeepSeek primary, GLM (glm-4.6) fallback. Keys from env, never logged."""
import json, os, sys, time, urllib.request, urllib.error

PROVIDERS = [
    ("deepseek", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat", {}),
    ("glm", "https://open.bigmodel.cn/api/paas/v4/chat/completions", "GLM_API_KEY", "glm-4.6", {"thinking": {"type": "disabled"}}),
]
USED = set()

def _log(provider, model, u):
    path = os.environ.get("LLM_USAGE_LOG")
    if path:
        with open(path, "a") as f:
            f.write(json.dumps({"provider": provider, "model": model, "hit": u.get("prompt_cache_hit_tokens", 0),
                                "miss": u.get("prompt_cache_miss_tokens", u.get("prompt_tokens", 0)),
                                "out": u.get("completion_tokens", 0)}) + "\n")

def chat_json(system, user, temperature=0.2, retries=3, timeout=240):
    last = None
    for name, url, env, model, extra in PROVIDERS:
        if not os.environ.get(env):
            continue
        body = {"model": model, "temperature": temperature, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], **extra}
        for i in range(retries):
            try:
                req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
                    "Authorization": "Bearer " + os.environ[env], "Content-Type": "application/json", "User-Agent": "tvshows-pipeline/0.2"})
                r = json.load(urllib.request.urlopen(req, timeout=timeout))
                _log(name, model, r.get("usage") or {})
                content = r["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
                out = json.loads(content)
                USED.add(name)
                return out
            except urllib.error.HTTPError as e:
                last = f"{name} HTTP {e.code}"
                print("llm", last, file=sys.stderr)
                if e.code in (401, 402, 403):   # auth / balance: go to next provider now
                    break
                time.sleep(4 * (i + 1))
            except Exception as e:
                last = f"{name} {type(e).__name__}"
                print("llm", last, file=sys.stderr)
                time.sleep(3 * (i + 1))
    raise RuntimeError("all LLM providers failed: " + str(last))
