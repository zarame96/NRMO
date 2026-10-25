#!/bin/bash
# Two lanes, each sequential. A lane stops the whole batch after 2 consecutive failures.
S=/tmp/claude-0/-home-user-NRMO/52d78ce8-8508-56ed-aaab-63247e7801b2/scratchpad
ST=$S/results12/guarded_status.txt
LOCK=$S/results12/ABORT.lock
rm -f "$LOCK"
lane() {
  local fails=0
  while read -r id r; do
    [ -z "$id" ] && continue
    [ -f "$LOCK" ] && break
    $S/bin/run_one12.sh "$id" "$r" >> $S/results12/guarded.log 2>&1
    ec=$(python3 -c "import json;print(json.load(open('$S/results12/meta/${id}_r${r}.json'))['exit_code'])" 2>/dev/null || echo 99)
    echo "${id}_r${r} exit=$ec $(date -Iseconds)" >> $ST
    if [ "$ec" = "0" ]; then fails=0; else fails=$((fails+1)); fi
    if [ "$fails" -ge 2 ]; then touch "$LOCK"; echo "ABORT: 2 consecutive failures $(date -Iseconds)" >> $ST; break; fi
  done
}
awk 'NR%2==1' $S/bin/remaining24.txt | lane &
awk 'NR%2==0' $S/bin/remaining24.txt | lane &
wait
echo "batch end $(date -Iseconds)" >> $ST
