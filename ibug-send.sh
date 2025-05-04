#!/bin/sh

set -e
if false [ -z "$SKIP_RSYNC" ]; then
  rsync -aHAXxv --delete \
    --exclude=/var/cache \
    --exclude=/var/tmp \
    --exclude='/core.*' \
    / /mnt/backup/rootfs/
fi

DATASET=pool0/ROOT/ubuntu
DATE=$(date +%Y%m%d)
SNAPSHOT="$DATASET@$DATE"
RETENTION_DAYS="${1:-7}"
RETENTION="$((RETENTION_DAYS * 86400))"

if [ "$(zfs list -Hpo name "$SNAPSHOT")" = "$SNAPSHOT" ]; then
  echo "Snapshot exists: $SNAPSHOT"
else
  zfs snapshot -ro ibug:retention="$RETENTION" "$SNAPSHOT"
fi

DST=pool1/backup/rootfs
DSTLAST="$(zfs list -Hpt snapshot -o name "$DST" | tail -1)"
SRCFROM="$DATASET@${DSTLAST##*@}"
if [ "$SRCFROM" != "$SNAPSHOT" ]; then
  zfs send -cLRI "$SRCFROM" "$SNAPSHOT" |
    pv |
    zfs recv -F -x mountpoint -x compression "$DST"
fi

purge() {
  local DATASET="$1"
  zfs list -Hpt snapshot -o name,creation,ibug:retention "$DATASET" |
    while read -r zNAME zCREATION zRETENTION; do
    if [ "$zRETENTION" = "-" ]; then
      # assume default value
      zRETENTION="$((7 * 86400))"
    fi
    UNTIL="$((zCREATION + zRETENTION))"
    UNTIL_DATE="$(date -d "@$UNTIL" "+%Y-%m-%d %H:%M:%S")"
    echo "$zNAME: $UNTIL_DATE"
    if [ "$NOW" -ge "$UNTIL" ]; then
      zfs destroy -rv "$zNAME"
    fi
  done
}

NOW="$(($(date +%s) - 3600))"
purge "$DATASET"
purge "$DST"
exit 0
