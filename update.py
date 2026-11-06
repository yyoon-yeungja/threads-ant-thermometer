#!/usr/bin/env python3
"""Refresh the public dashboard from the private page.

usage: python3 update.py <private_page.html> [--weekly] [--raw raw/YYYY-MM.json ...]

Copies only anonymous aggregates into index.html:
  daily : DAILY, MKT, and KW (per-keyword L/S/other counts, last 7 DAILY days)
          when --raw files are given
  weekly: also HISTORY
Never copies PRED, DATA.posts, DATA.fol or any account name, text or link.
"""
import json, re, sys, subprocess, datetime

args = sys.argv[1:]
src = open(args[0], encoding="utf-8").read()
weekly = "--weekly" in args
raws = args[args.index("--raw") + 1:] if "--raw" in args else []
raws = [r for r in raws if not r.startswith("--")]
pub = open("index.html", encoding="utf-8").read()

def block(text, name):
    m = re.search(r"/\*%s_START\*/(.*?)/\*%s_END\*/" % (name, name), text, re.S)
    if not m:
        sys.exit("missing block " + name)
    return m.group(1)

def put(name, value):
    global pub
    pub = re.sub(r"/\*%s_START\*/.*?/\*%s_END\*/" % (name, name),
                 lambda _: "/*%s_START*/%s/*%s_END*/" % (name, value, name), pub, count=1, flags=re.S)

ANON = {"DAILY": ["d", "n", "L", "S", "N", "P", "I", "lkL", "lkS", "src", "sampled"],
        "HISTORY": ["week", "start", "end", "n", "L", "S", "N", "P", "I", "long", "wlong", "runs"]}

def anon(name):
    rows = json.loads(block(src, name))
    return json.dumps([{k: r[k] for k in ANON[name] if k in r} for r in rows], ensure_ascii=False)

put("DAILY", anon("DAILY"))
mkt = json.loads(block(src, "MKT"))
put("MKT", json.dumps(mkt, ensure_ascii=False))

if weekly:
    put("HISTORY", anon("HISTORY"))

CORE = ["코스피", "삼성전자", "국장", "나스닥", "미국주식", "비트코인"]
if raws:
    daily = json.loads(block(src, "DAILY"))
    days = [d["d"] for d in daily if d.get("kw") == 6][-7:]
    if days:
        cnt = {k: {"k": k, "L": 0, "S": 0, "N": 0, "P": 0, "I": 0} for k in CORE}
        seen = set()
        for r in raws:
            for p in json.load(open(r, encoding="utf-8")).get("posts", {}).values():
                if p["id"] in seen or not p.get("win") or p.get("dir") not in ("L", "S", "N", "P", "I"):
                    continue
                dt = datetime.datetime.fromisoformat(p["dt"].replace("Z", "+00:00")) + datetime.timedelta(hours=9)
                if dt.date().isoformat() not in days:
                    continue
                seen.add(p["id"])
                for q in set(p.get("q") or []):
                    if q in cnt:
                        cnt[q][p["dir"]] += 1
        rows = [dict(c, n=c["L"] + c["S"] + c["N"] + c["P"] + c["I"]) for c in cnt.values()]
        rows = [r for r in rows if r["n"]]
        rows.sort(key=lambda r: -r["n"])
        put("KW", json.dumps({"from": days[0], "to": days[-1], "rows": rows}, ensure_ascii=False))

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
put("UPDATED", json.dumps(now.strftime("%Y-%m-%d %H:%M KST")))

# privacy guard: no account handles, post links or post text may reach the public page
for bad in ["threads.com/@", "threads.net/@", '"u":', '"id":', '"x":', '"s":', "PRED", "fol"]:
    if bad in pub:
        sys.exit("privacy check failed: " + bad)
open("index.html", "w", encoding="utf-8").write(pub)
js = pub.split("<script>")[1].split("</script>")[0]
open("/tmp/_pub_check.js", "w").write(js)
subprocess.run(["node", "--check", "/tmp/_pub_check.js"], check=True)
print("ok", "weekly" if weekly else "daily")
