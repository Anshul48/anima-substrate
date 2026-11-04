# Copyright 2026 Anshul48
# SPDX-License-Identifier: Apache-2.0
"""ANIMA memory: the agent's finished jobs become TRACE passages; the next job starts from similar past fixes.

Command line:  python3 -m anima.memory {setup,status,ingest,record,recall,prompt,verify} ...
Library hook:  anima.memory.hook.augment_prompt(prompt, task_text, store_dir)
See docs/MEMORY.md.
"""
