# Security

ANIMA is a research prototype. There is no hosted service, no account system and no stored user data; the project site is static pages.

## Report a problem privately

Please do not open a public issue for a security problem. Use GitHub's private report form:
<https://github.com/Anshul48/anima-substrate/security/advisories/new>

Say what you found, how to reproduce it and what you expected. We aim to reply within a week. This is a small project, so that is a goal, not a promise.

## What is in scope

- The tools in this repository: `tools/site.py`, `docs/evidence/flagship-run3/check_chain.py`, the in-browser record check under `docs/demo/`, and the package under `src/`.
- Anything that makes a page run code you did not expect, or makes the record check say a changed file is fine.

## What is not

- The TRACE repository ([Anshul48/trace](https://github.com/Anshul48/trace)) has its own policy.
- Coding tools such as Muse Code, Claude Code and Codex: report those to their makers.
- What the record check cannot do by design: it shows that a log was not edited afterwards. It does not show that the run itself was honest.

## Secrets

Never put keys, tokens or passwords in an issue, pull request or commit. If you find one in this repository, report it privately using the link above. ANIMA's planned rule pack blocks reading and copying key files; that part is not built yet (see the [status table](README.md)).
