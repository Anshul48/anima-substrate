#!/bin/sh
# ANIMA one-line installer.
#   curl -fsSL https://raw.githubusercontent.com/Anshul48/anima-substrate/main/install.sh | sh
#
# What it does (it prints this plan before it starts):
#   1. checks that git and python3 (3.11 or newer) exist
#   2. clones the repository into $ANIMA_HOME/repo (or fast-forwards an existing clone)
#   3. creates a Python venv at $ANIMA_HOME/venv (no packages are installed: ANIMA is standard library only)
#   4. writes a launcher at $ANIMA_HOME/bin/anima
#   5. runs `anima init`: looks for muse, claude and codex programs and writes $ANIMA_HOME/anima.yaml
#      (an existing anima.yaml is kept)
#   6. links `anima` into ~/.local/bin only if that folder already exists and is on your PATH
# It never uses sudo, never edits shell startup files, never reads or copies a login or key file,
# and never calls a model. Safe to run again.
#
# Settings (all optional):
#   ANIMA_HOME=~/.anima          where everything goes
#   ANIMA_REPO_URL=...           another remote (a file:// path works for testing)
#   ANIMA_BRANCH=main            branch to install
#   ANIMA_NO_LINK=1              skip step 6
set -eu

REPO_URL="${ANIMA_REPO_URL:-https://github.com/Anshul48/anima-substrate}"
BRANCH="${ANIMA_BRANCH:-main}"
ANIMA_HOME="${ANIMA_HOME:-$HOME/.anima}"
export ANIMA_HOME

say() { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
die() { printf 'anima install: %s\n' "$*" >&2; exit 1; }

say "ANIMA installer. Plan (nothing has been changed yet):"
say "  1. check git and python3 (3.11+)                         [read only]"
say "  2. clone $REPO_URL"
say "     (branch $BRANCH) into $ANIMA_HOME/repo, or fast-forward it if it is already there"
say "  3. create a venv at $ANIMA_HOME/venv                      [no packages installed]"
say "  4. write the launcher $ANIMA_HOME/bin/anima"
say "  5. run: anima init   (looks for muse / claude / codex on PATH, writes $ANIMA_HOME/anima.yaml, keeps it if it exists)"
say "  6. link anima into ~/.local/bin only if it already exists and is on PATH (skip with ANIMA_NO_LINK=1)"
say "  Will NOT: use sudo, edit your shell startup files, read or copy any login or key file, or call any model."

step "1/6 checking tools"
command -v git >/dev/null 2>&1 || die "git is not installed. Install git with your package manager, then run this again."
command -v python3 >/dev/null 2>&1 || die "python3 is not installed. Install Python 3.11 or newer, then run this again."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
  || die "python3 is older than 3.11 ($(python3 --version 2>&1)). Install Python 3.11 or newer."
say "git: $(command -v git)"
say "python3: $(command -v python3) ($(python3 --version 2>&1))"

step "2/6 getting the code"
mkdir -p "$ANIMA_HOME"
if [ -d "$ANIMA_HOME/repo/.git" ]; then
  say "already cloned: $ANIMA_HOME/repo"
  if [ -n "$(git -C "$ANIMA_HOME/repo" status --porcelain 2>/dev/null)" ]; then
    say "local changes found in $ANIMA_HOME/repo: leaving the code as it is (no update)"
  else
    git -C "$ANIMA_HOME/repo" fetch --quiet origin "$BRANCH" \
      && git -C "$ANIMA_HOME/repo" checkout --quiet "$BRANCH" 2>/dev/null \
      && git -C "$ANIMA_HOME/repo" merge --ff-only --quiet "origin/$BRANCH" \
      && say "up to date: $(git -C "$ANIMA_HOME/repo" log --oneline -1)" \
      || say "could not fast-forward (offline, or the branch moved); keeping the code as it is"
  fi
else
  git clone --quiet --branch "$BRANCH" "$REPO_URL" "$ANIMA_HOME/repo" || die "git clone failed for $REPO_URL (branch $BRANCH)"
  say "cloned: $(git -C "$ANIMA_HOME/repo" log --oneline -1)"
fi
[ -f "$ANIMA_HOME/repo/anima/harness/cli.py" ] || die "this checkout has no anima/harness (wrong branch? set ANIMA_BRANCH)"

step "3/6 python venv"
if [ -x "$ANIMA_HOME/venv/bin/python" ]; then
  say "venv already there: $ANIMA_HOME/venv"
elif python3 -m venv "$ANIMA_HOME/venv" >/dev/null 2>&1; then
  say "created: $ANIMA_HOME/venv"
else
  rm -rf "$ANIMA_HOME/venv"
  say "python3 -m venv is not available here (on Debian/Ubuntu it is the python3-venv package, which needs an admin)."
  say "continuing with the system python3: ANIMA has no dependencies, so nothing is lost."
fi

step "4/6 launcher"
mkdir -p "$ANIMA_HOME/bin"
cat > "$ANIMA_HOME/bin/anima.tmp" <<EOF
#!/bin/sh
# written by ANIMA install.sh
ANIMA_HOME="\${ANIMA_HOME:-$ANIMA_HOME}"
export ANIMA_HOME
exec "\$ANIMA_HOME/repo/bin/anima" "\$@"
EOF
chmod +x "$ANIMA_HOME/bin/anima.tmp"
mv "$ANIMA_HOME/bin/anima.tmp" "$ANIMA_HOME/bin/anima"
say "wrote $ANIMA_HOME/bin/anima"

step "5/6 anima init (what did you already have?)"
"$ANIMA_HOME/bin/anima" init

step "6/6 command on PATH"
LINK="$HOME/.local/bin/anima"
if [ "${ANIMA_NO_LINK:-0}" = "1" ]; then
  say "skipped (ANIMA_NO_LINK=1)"
elif [ -d "$HOME/.local/bin" ] && case ":$PATH:" in *":$HOME/.local/bin:"*) true ;; *) false ;; esac; then
  if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then
    say "$LINK exists and is not a link: left alone"
  else
    ln -sf "$ANIMA_HOME/bin/anima" "$LINK"
    say "linked $LINK -> $ANIMA_HOME/bin/anima"
  fi
else
  say "~/.local/bin is not on your PATH (or does not exist), so no link was made."
  say "use it with the full path:   $ANIMA_HOME/bin/anima doctor"
  say "or add this line to your shell startup file yourself:   export PATH=\"$ANIMA_HOME/bin:\$PATH\""
fi

printf '\nInstalled. Next:\n'
say "  $ANIMA_HOME/bin/anima doctor                      # checks each tool it found"
say "  $ANIMA_HOME/bin/anima harness test muse           # one tiny real call (uses your own login; swap in claude or codex)"
say "  $ANIMA_HOME/bin/anima run --harness muse --task tiny-bug"
