---
name: checksum
description: Compute checksums (MD5, SHA-256) for text or files.
---

# Checksum

## When to use this skill

Use this skill when asked to compute a hash or checksum of any text or file content.

## How to use

Run the bundled script:

```
python scripts/checksum.py '<text>'
```

The script outputs MD5 and SHA-256 checksums for the given input.

## Verification

Always verify computed checksums against known test vectors when available. Read the `test_vectors.md` reference to compare results.
