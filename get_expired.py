#!/usr/bin/env python3
import datetime
import argparse
import subprocess
from zfs_send_src2dst import print_expired
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send zfs snapshot from src to dst, keep specified number of snapshots.')
    parser.add_argument('-s', '--src', required=True, help='src dataset')
    parser.add_argument('-d', '--delete', action='store_true', help='delete expired snapshot')
    args = parser.parse_args()

    print_expired(args.src, delete=args.delete)
    
