# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""python3 -m anima.ui [--demo | --state DIR | --chain FILE --jobs DIR] [--port 8765]

Serves the SST screen on http://127.0.0.1:PORT/.  The other subcommands
(status, cmd, voice) also work here:  python3 -m anima.ui status --tree --demo
"""
import sys

from .cli import main

if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] not in ("status", "ui", "cmd", "voice", "-h", "--help"):
        argv = ["ui"] + argv
    sys.exit(main(argv))
