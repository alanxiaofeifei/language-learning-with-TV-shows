#!/usr/bin/env bash
# Fails if Git would publish private material: subtitle/audio files, anything under site/private/,
# or real email addresses. Checks tracked files plus files staged for commit.
# Allowlist: site/archive/5s-online/**.mp3 are our own Piper TTS clips (frozen archive), not show audio.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
fail=0
files=$( { git ls-files; git diff --cached --name-only --diff-filter=AM; } | sort -u)

bad_paths=$(printf '%s\n' "$files" | grep -E '^site/private/|\.(srt|mp3|m4a|webm|json3)$|\.(lines|phrases)\.json$' | grep -vE '^site/archive/5s-online/.*\.mp3$' || true)
if [ -n "$bad_paths" ]; then echo "private/media files tracked:"; echo "$bad_paths"; fail=1; fi

GM="@gmail"; GM="$GM.com"                                  # split so this script does not match itself
EMAIL='[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}'
# Scan both the working tree and the staged index (staged content can differ from the working tree).
hits=$( { git grep -nIF "$GM" -- . 2>/dev/null; git grep --cached -nIF "$GM" -- . 2>/dev/null | sed 's/^/(staged) /'; } || true)
emails=$( { git grep -noIE "$EMAIL" -- . ':!package-lock.json' 2>/dev/null; git grep --cached -noIE "$EMAIL" -- . ':!package-lock.json' 2>/dev/null | sed 's/^/(staged) /'; } | grep -viE '@example\.(test|com|org)$' || true)
if [ -n "$hits$emails" ]; then echo "email addresses in tracked files:"; printf '%s\n%s\n' "$hits" "$emails" | sed '/^$/d'; fail=1; fi

[ $fail -eq 0 ] && echo "check-no-private: ok ($(printf '%s\n' "$files" | wc -l) files)"
exit $fail
