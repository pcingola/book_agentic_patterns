"""Compute MD5 and SHA-256 checksums for a given text."""

import hashlib
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python checksum.py '<text>'")
        sys.exit(1)
    text = " ".join(sys.argv[1:])
    data = text.encode("utf-8")
    print(f"MD5:    {hashlib.md5(data).hexdigest()}")
    print(f"SHA256: {hashlib.sha256(data).hexdigest()}")
