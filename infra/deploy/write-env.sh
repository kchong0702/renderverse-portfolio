#!/usr/bin/env bash
set -euo pipefail
umask 077

file=$1
shift
pattern="^($(IFS='|'; echo "$*"))"

jq --null-input --raw-output --arg pattern "$pattern" --arg quote "'" '
  [env.VARS, env.SECRETS | fromjson] | add | to_entries[]
  | select(.key | test($pattern))
  | if .value | test("[\($quote)\n]")
    then error("\(.key) contains a single quote or a newline")
    else "\(.key)=\($quote)\(.value)\($quote)"
    end
' > "$file"
