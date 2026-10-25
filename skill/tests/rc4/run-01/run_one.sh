#!/bin/bash
# usage: run_one.sh <ID> <rep>   (reads prompt from prompts.tsv fixed copy)
set -u
S=<scratch>
OUT=$S/results4; ID=$1; R=$2; RID=${ID}_r${R}
PROMPT=$(awk -F'\t' -v id="$ID" '$1==id{print $2}' /home/user/NRMO/skill/tests/rc4/prompts.tsv)
mkdir -p $OUT/raw $OUT/meta $OUT/input
WD=$S/work4/$RID; rm -rf $WD; mkdir -p $WD
printf '%s' "$PROMPT" > $OUT/input/$RID.txt
START=$(date -Iseconds)
cd $WD
timeout 1200 env -u CLAUDE_ADDITIONAL_DIRECTORIES -u CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD \
  CLAUDE_CONFIG_DIR=$S/cfg4 CLAUDE_CODE_SYNC_SKILLS=0 CLAUDE_CODE_SYNC_PLUGINS=0 \
  claude -p "$PROMPT" --model claude-opus-5-5 --tools "Skill,Read,Glob,Grep" \
  --add-dir $S/cfg4/skills/nrmo --strict-mcp-config --no-session-persistence \
  --output-format stream-json --verbose < /dev/null > $OUT/raw/$RID.jsonl 2> $OUT/raw/$RID.stderr.txt
EC=$?
END=$(date -Iseconds)
printf '{"run":"%s","start":"%s","end":"%s","exit_code":%d,"prompt_sha256":"%s"}\n' "$RID" "$START" "$END" "$EC" "$(sha256sum $OUT/input/$RID.txt|cut -d' ' -f1)" > $OUT/meta/$RID.json
echo "$RID exit=$EC"
