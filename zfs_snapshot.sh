#!/bin/sh
# @credits: https://ibug.io/blog/2024/05/migrate-rootfs-to-zfs/

if [ $# != 1 ]; then
  echo "Usage: $0 <dataset>"
  exit 1
fi

DATASET=$1
DATE=$(date +%Y%m%d)
RETENTION_DAYS="${RETENTION_DAYS:-7}"
RETENTION="$((RETENTION_DAYS * 86400 - 3600))"

NOW="$(date +%s)"
SNAPSHOT="$DATASET@$DATE"
if [ "$(zfs list -Hpo name "$SNAPSHOT")" = "$SNAPSHOT" ]; then
  echo "Snapshot exists: $SNAPSHOT"
else
  zfs snapshot -o ibug:retention="$RETENTION" -r "$SNAPSHOT" || true
fi

zfs list -Hpt snapshot -o name,creation,ibug:retention "$DATASET" |
  while read -r zNAME zCREATION zRETENTION; do
  if [ "$zRETENTION" = "-" ]; then
    # assume default value
    zRETENTION="$((30 * 86400 - 3600))"
  fi
  UNTIL="$((zCREATION + zRETENTION))"
  UNTIL_DATE="$(date -d "@$UNTIL" "+%Y-%m-%d %H:%M:%S")"
  echo "$zNAME: $UNTIL_DATE"
  if [ "$NOW" -ge "$UNTIL" ]; then
    zfs destroy -rv "$zNAME"
  fi
done
