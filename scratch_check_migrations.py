import re
import glob

revs = {}
for f in glob.glob("migrations/versions/*.py"):
    content = open(f, encoding="utf-8").read()
    m = re.search(r'^revision\s*:.*=\s*"([^"]+)"', content, re.M)
    d = re.search(r'^down_revision\s*:.*=\s*"([^"]+)"', content, re.M)
    if m:
        revs[m.group(1)] = (d.group(1) if d else None, f)

missing = set()
for rev, (down, f) in revs.items():
    if down and down not in revs:
        missing.add(down)
        print(f"BROKEN: {f} -> down_revision '{down}' NOT FOUND")

print("total migration files:", len(revs))
print("missing revisions referenced:", missing)

# find heads (revisions nobody points down to)
down_set = {d for d, _ in revs.values() if d}
heads = [r for r in revs if r not in down_set]
print("heads:", heads)
