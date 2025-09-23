---
name: Bug report
about: Report an issue (include seed + profile)
labels: bug
---

**What happened**
A clear description.

**Repro steps**
- Profile: ross | wife | son | family_mix
- Seed: 777 (or value)
- Intent (if any):
- Endpoint: `/recommendations?...`

**Expected vs actual**
What you expected; what you saw.

**Artifacts**
Attach JSON from:
```
curl -s "http://localhost:8000/recommendations?for=ross&seed=777" -o ross_777.json
```

