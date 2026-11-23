#!/usr/bin/env python3
"""Restore Git-LFS asset binaries out of git history (sandbox workaround, no git-lfs).

    Tools/sandbox/restore_lfs_from_history.py [--dry-run]

Why this exists: on the locked-down sandbox `git-lfs` cannot be installed (release assets,
`github-cloud.githubusercontent.com` and `objects.githubusercontent.com` are all unreachable,
and there is no Go toolchain to build it). Every `Assets/**/*.glb` is therefore a 130-byte
pointer, and the whole gameplay/asset test suite has nothing to load.

The binaries are not lost: PR #14 committed them as **regular blobs**, and PR #15 replaced
them with LFS pointers afterwards. This script reads the `oid sha256:` of every pointer in the
working tree, walks the history of that exact path, and restores the first blob whose SHA-256
matches the pointer. A wrong or corrupt file can therefore never be restored.

Afterwards every pointer path is marked `--skip-worktree`, so the restored binaries can never
be committed back as plain blobs: `git status` stays clean and `git add -A` ignores them.
Undo a single file with

    git update-index --no-skip-worktree <path> && git checkout -- <path>

Exit codes: 0 all pointers resolved (or already real), 1 required files missing, 2 usage.
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

POINTER_MAGIC = b"version https://git-lfs.github.com/spec/v1"
OID_RE = re.compile(rb"oid sha256:([0-9a-f]{64})")
SIZE_RE = re.compile(rb"size (\d+)")


def git(*args, text=True):
    return subprocess.run(["git"] + list(args), capture_output=True, text=text)


def repo_root():
    r = git("rev-parse", "--show-toplevel")
    if r.returncode != 0:
        sys.exit("not inside a git repository")
    return r.stdout.strip()


def read_pointer(path):
    try:
        with open(path, "rb") as fh:
            head = fh.read(256)
    except OSError:
        return None
    if not head.startswith(POINTER_MAGIC):
        return None
    oid = OID_RE.search(head)
    size = SIZE_RE.search(head)
    if oid is None:
        return None
    return oid.group(1).decode(), int(size.group(1)) if size else -1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="report, change nothing")
    ap.add_argument("--no-fetch", action="store_true",
                    help="do not unshallow the clone before searching history")
    args = ap.parse_args()

    root = repo_root()
    os.chdir(root)

    # The arena checkout is shallow (1 commit); the blobs we want live further back.
    if git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        if args.no_fetch:
            sys.exit("shallow clone: run `git fetch --unshallow origin` first (or drop --no-fetch)")
        print("shallow clone -> git fetch --unshallow origin")
        r = git("fetch", "--unshallow", "origin")
        if r.returncode != 0:
            sys.exit("could not unshallow: %s" % (r.stderr.strip() or "unknown error"))

    files = [f for f in git("ls-files").stdout.split("\n") if f]
    pointers = {}
    for f in files:
        p = read_pointer(f)
        if p is not None:
            pointers[f] = p

    print("LFS pointer files in the working tree: %d" % len(pointers))
    if not pointers:
        print("nothing to restore")
        return 0

    restored, missing = 0, []
    for path, (oid, size) in sorted(pointers.items()):
        commits = git("log", "--all", "--format=%H", "--", path).stdout.split()
        hit = None
        for c in commits:
            rev = git("rev-parse", "%s:%s" % (c, path)).stdout.strip()
            if not rev:
                continue
            raw = subprocess.run(["git", "cat-file", "-p", rev], capture_output=True).stdout
            if raw.startswith(POINTER_MAGIC) or (size >= 0 and len(raw) != size):
                continue
            if hashlib.sha256(raw).hexdigest() == oid:
                hit = raw
                break
        if hit is None:
            missing.append(path)
            continue
        if not args.dry_run:
            with open(path, "wb") as fh:
                fh.write(hit)
        restored += 1
        print("  restored %-60s %8d B" % (path, len(hit)))

    if not args.dry_run:
        # All pointer paths, not only the restored ones: keeps the pointers that stay
        # unresolved from being committed as "deleted/modified" binaries either.
        git("update-index", "--skip-worktree", *sorted(pointers))

    print("\nrestored %d of %d" % (restored, len(pointers)))
    if missing:
        print("not recoverable from history (%d):" % len(missing))
        for f in missing:
            print("  ", f)
        print("These were never committed as plain blobs. They are only needed by the art/"
              "review tooling, not by Tests/run_all.sh.")
        if args.dry_run:
            return 0
        # Unrecoverable pointers stay pointers; that is not a failure for the test gate.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
