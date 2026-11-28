"""Fill missing translations in gen/<CODE>.lines.json with the LLM (DeepSeek primary, GLM fallback).

Usage: python pipeline/multi/translate_lines.py SHOW_ID WORKDIR [--only S01E01] [--langs zh,vi] [--batch 80]
Only lines missing a target field are sent; the file is saved after every batch, so re-runs resume
(idempotent per episode). Usage is appended to $LLM_USAGE_LOG if set. Keys come from env only.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, episodes, select, gen_dir, save, load, clean
from llm import chat_json, USED

NAMES = {"zh": "简体中文（自然口语，像国内字幕组，不要翻译腔）", "vi": "越南语（北越河内自然口语，称呼按人物关系用 anh/chị/em/mình/cậu/tớ 等）",
         "en": "English (natural spoken)"}

SOURCE_NAMES = {"ja": "日语", "fr": "法国法语"}

def system(c, langs):
    want = "；".join(f"{k} = {NAMES[k]}" for k in langs)
    source = c["target"]
    title = c["title"].get(source) if source in SOURCE_NAMES else c["title"]["en"]
    label = SOURCE_NAMES.get(source, "")
    names = "原名" if label else "英文原名"
    return (f"你是影视字幕译者。剧集：{title}（{c['title']['zh']}）。把每行{label}字幕译成：{want}。"
            f"要求：逐行对应、不合并不拆分；保留语气和笑点，俚语按意思译；人名保留{names}；[声音描述] 也简短翻译并保留方括号。"
            f"只输出 JSON：{{\"t\":[[行号, {', '.join(json.dumps(k) for k in langs)}], ...]}}，每个输入行一项。")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("show"); ap.add_argument("work")
    ap.add_argument("--only"); ap.add_argument("--langs"); ap.add_argument("--batch", type=int, default=80); a = ap.parse_args()
    c = cfg(a.show)
    langs = [x for x in (a.langs.split(",") if a.langs else c["translate"]) if x]
    if c["target"] in SOURCE_NAMES and any(k not in c["translate"] for k in langs):
        ap.error("Japanese and French shows support only zh and vi translations")
    if not langs: print(json.dumps({"note": "nothing to translate for " + a.show})); return
    src = c["target"]; gen = gen_dir(a.work); total = 0; run_used = set()
    for ep in select(episodes(a.show, a.work), a.only):
        path = os.path.join(gen, ep["code"] + ".lines.json")
        lines = load(path)
        if not lines: continue
        todo = [L for L in lines if L.get(src) and any(not L.get(k) for k in langs)]
        if not todo: continue
        by_i = {L["i"]: L for L in lines}
        USED.clear()                      # meta records only this episode's providers
        for b in range(0, len(todo), a.batch):
            chunk = todo[b:b + a.batch]
            first = chunk[0]["i"]
            ctx = [by_i[j][src] for j in range(max(0, first - 4), first) if j in by_i]
            user = (("上文（仅供理解，不要输出）：\n" + "\n".join(ctx) + "\n\n") if ctx else "") + \
                   "字幕：\n" + "\n".join(f"{L['i']}: {L[src]}" for L in chunk)
            got = chat_json(system(c, langs), user, temperature=0.3).get("t", []); run_used |= USED
            n = 0
            for row in got:
                if not isinstance(row, list) or len(row) < 1 + len(langs): continue
                try: i = int(row[0])
                except (TypeError, ValueError): continue
                if i not in by_i: continue
                for k, v in zip(langs, row[1:]):
                    if isinstance(v, str) and v.strip() and not by_i[i].get(k): by_i[i][k] = clean(v) or v.strip(); n += 1
            save(path, lines); total += n
            print(f"{ep['code']} batch {b // a.batch + 1}/{(len(todo) + a.batch - 1) // a.batch}: {n} fields", file=sys.stderr)
        meta_p = os.path.join(gen, ep["code"] + ".meta.json"); meta = load(meta_p, {}) or {}
        meta["translate"] = sorted(set(meta.get("translate", [])) | USED); save(meta_p, meta)
    print(json.dumps({"filled": total, "providers": sorted(run_used)}))

if __name__ == "__main__": main()
