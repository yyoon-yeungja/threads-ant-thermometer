#!/usr/bin/env python3
"""Refresh the public dashboard from the private page.

usage: python3 update.py <private_page.html> [--weekly]

Copies only anonymous aggregates into index.html:
  daily : DAILY, MKT
  weekly: also HISTORY and ASSETS (mention counts per asset, no account data)
Never copies PRED, DATA.posts, DATA.fol or any account name, text or link.
"""
import json, re, sys, subprocess, datetime

src = open(sys.argv[1], encoding="utf-8").read()
weekly = "--weekly" in sys.argv
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
        "HISTORY": ["week", "start", "end", "n", "L", "S", "N", "P", "I", "long", "wlong", "del", "delL", "delS", "checked", "runs"]}

def anon(name):
    rows = json.loads(block(src, name))
    return json.dumps([{k: r[k] for k in ANON[name] if k in r} for r in rows], ensure_ascii=False)

put("DAILY", anon("DAILY"))
mkt = json.loads(block(src, "MKT"))
put("MKT", json.dumps(mkt, ensure_ascii=False))

if weekly:
    put("HISTORY", anon("HISTORY"))
    m = re.search(r"const DATA=(\{.*?\});\n", src, re.S)
    posts = json.loads(m.group(1))["posts"]
    grp = json.loads(re.search(r"const GRP=(\{.*?\});", src).group(1))
    agg = {}
    for p in posts:
        for a in {grp.get(a, a) for a in p.get("assets") or []}:
            x = agg.setdefault(a, {"k": a, "n": 0, "L": 0, "S": 0})
            x["n"] += 1
            if p.get("dir") in ("L", "S"):
                x[p["dir"]] += 1
    top = sorted(agg.values(), key=lambda x: -x["n"])[:13]
    put("ASSETS", json.dumps(top, ensure_ascii=False))

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
