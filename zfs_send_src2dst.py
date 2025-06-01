#!/usr/bin/env python3
import sys
import datetime
import os
import argparse
import subprocess

debug=True
def run_cmd(cmd, print_cmd=False):
    if print_cmd:
        print(cmd)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def run_cmd3(cmd, print_cmd=False, run=True):
    if debug or print_cmd:
        print(cmd)
    if run:
        os.system(cmd)

def get_snap_list(dataset, host=None):
    if not host:
        output = run_cmd(f"zfs list -Ht snapshot -o name '{dataset}'")[1]
    else:
        output = run_cmd(f"ssh {host} 'zfs list -Ht snapshot -o name \'{dataset}\''")[1]
    lines = output.splitlines()
    snap_list = []
    for line in lines:
        if line.startswith(dataset):
            snap_list.append(line)
    return snap_list

def ssh_cmd(cmd, ssh_host=''):
    if ssh_host:
        cmd = f"ssh {ssh_host} '{cmd}'"
    return cmd

def print_expired(dataset, delete=False, ssh_host=''):
    # use `ibug:retention` to identify how long to keep snapshot
    _, output, _ = run_cmd(ssh_cmd(f"zfs list -Hpt snapshot -o name,creation,ibug:retention '{dataset}'", ssh_host))
    for line in output.splitlines():
        zNAME, zCREATION, zRETENTION = line.split()
        if 'keep' in zNAME:
            print(f"skip {zNAME}")
            continue
        default_flag = False
        if zRETENTION == "-":  # no custom property, use default value
            zRETENTION = 30 * 86400 - 3600  # default keep 7 day
            default_flag = True
        UNTIL = int(zCREATION) + int(zRETENTION)
        UNTIL_DATE = datetime.datetime.fromtimestamp(UNTIL).strftime("%Y-%m-%d %H:%M:%S")
        expired = int(datetime.datetime.now().timestamp()) >= UNTIL
        print(f"{zNAME}: {UNTIL_DATE} {'E'if expired else ' '} {'D' if default_flag else ' '}")
        if delete and expired:
            print(f"Delete {zNAME}")
            run_cmd(ssh_cmd(f"zfs destroy -rv '{zNAME}'", ssh_host))

def process_one_dst(SRC, DST, progress=True, dry_run=False, no_compress=False, ssh_host=None):
    src_snaps = get_snap_list(SRC)
    dst_snaps = get_snap_list(DST, host=ssh_host)

    # find common
    src_date_list = [snap.split('@')[1] for snap in src_snaps]
    dst_date_list = [snap.split('@')[1] for snap in dst_snaps]
    common_date_list = list(set(src_date_list).intersection(set(dst_date_list)))
    common_date_list.sort()
    print(f"common_date_list: {common_date_list}")

    if not src_snaps:
        print(f"No snapshot in source, exit")
        return
    if dst_snaps and dst_date_list[-1] >= src_date_list[-1]:
        print(f"Destination is newer than source, exit")
        print('delete dst expired snapshot')
        print_expired(DST, delete = not dry_run, ssh_host = ssh_host)
        return

    SRC_LATEST = src_snaps[-1]  # snapshot to send

    pv_str = " pv |" if progress else ""
    c = '' if no_compress else 'c'
    zfs_recv = ssh_cmd(f'zfs recv -s -F -x mountpoint \'{DST}\'', ssh_host)
    if common_date_list:
        print(f"Increment send")
        SRCLAST=f"{SRC}@{common_date_list[-1]}"
        run_cmd3(f"zfs send -w -{c}LRI '{SRCLAST}' '{SRC_LATEST}' |{pv_str} {zfs_recv}", print_cmd=True, run=not dry_run)
    else:
        print(f"Clean send")
        run_cmd3(f"zfs send -w -{c}LR '{SRC_LATEST}' |{pv_str} {zfs_recv}", print_cmd=True, run=not dry_run)

    print('delete dst expired snapshot')
    print_expired(DST, delete = not dry_run, ssh_host = ssh_host)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send zfs snapshot from src to dst, keep specified number of snapshots.')
    parser.add_argument('-s', '--src', required=True, help='src dataset')
    parser.add_argument('-d', '--dst_list', nargs='+', required=True, help='dst dataset')
    parser.add_argument('-P', '--progress', action='store_true', default=True, help='add pv for progress bar')
    parser.add_argument('-n', '--dry-run', action='store_true', help='don\'t make any changes, just print command')
    parser.add_argument('-S', '--snapshot', action='store_true', help='snapshot src')
    parser.add_argument('-r', '--retention-days', type=int, default=7, help='snapshot src retention days, default 7 days')
    parser.add_argument('-C', '--no-compress', action='store_true', help='add pv for progress bar')
    parser.add_argument('-H', '--ssh-host', help='remote host user@host')
    args = parser.parse_args()

    if args.snapshot:
        RETENTION = args.retention_days * 86400 - 3600
        DATE = datetime.datetime.now().strftime('%Y%m%d')
        # check exist
        # zfs list -Hpo name "$SNAPSHOT"
        print(f"Snapshot {args.src}@{DATE}")
        code, _, _ = run_cmd(f"zfs list -Hpo name '{args.src}@{DATE}'")
        if code == 0:
            print(f"Snapshot {args.src}@{DATE} already exist")
        else:
            run_cmd3(f"zfs snapshot -ro ibug:retention={RETENTION} '{args.src}@{DATE}'", run=not args.dry_run)
    
    print('delete src expired snapshot')
    print_expired(args.src, delete = not args.dry_run)
    for dst in args.dst_list:
        print(f"\n{args.src} ---> {dst}")
        start_time = datetime.datetime.now()
        process_one_dst(args.src, dst, progress=args.progress, dry_run=args.dry_run, no_compress=args.no_compress, ssh_host=args.ssh_host)
        print(f"elapsed time: {datetime.datetime.now() - start_time}")
