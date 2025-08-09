## 说明

配合 crontab 实现 zfs dataset/volume 的定期快照和备份。

- `zfs_snapshot.sh`: 对 zfs 进行快照，并自动删除过期快照
  - 通过 `RETENTION_DAYS` 变量配置快照保留天数
  - 每个快照保留天数独立控制，实现 7 天和 30 天快照共存，减少快照数量
  - 对于没有设置保留天数的手动快照，默认保留 7 天
- `zfs_send.py`: 将一个 zfs 阵列 dataset/volume 备份到另一个 zfs 阵列（基于 zfs send/recv）
  - 支持增量备份，大大减少传输数据量
  - 支持跨机备份（需要配置 ssh 免密登录）
- `zfs_get_expired.py`: 列出快照的过期时间

## 使用

Crontab 配置示例：

每周五 3 点执行一次快照，保留 30 天，每周日到周四 3 点执行一次快照，保留 7 天。
```shell
7  3    * * 5           RETENTION_DAYS=30 /root/scripts/zfs_backup/zfs_snapshot.sh rpool/ROOT/pve-1
7  3    * * 0,1,2,3,4,6 RETENTION_DAYS=7  /root/scripts/zfs_backup/zfs_snapshot.sh rpool/ROOT/pve-1
```

每周一和周五 4 点执行备份，将 `rpool` 存储池中的 `rpool/vault/vm-100-disk-docker` 备份到 `Saturn` 存储池对应位置
```shell
20 4    * * 1,5 /root/scripts/zfs_backup/zfs_send.py -s rpool/vault/vm-100-disk-docker -d Saturn/backup/nas-pve/vm-100-disk-docker
```
将本地 pve 的根文件系统 `rpool/ROOT/pve-1` 备份到远程机器 nas-pve 的 Saturn 存储池 `Saturn/backup/ryzen-pve/pve-1`。
```shell
15 4    * * 1,5 /root/scripts/zfs_backup/zfs_send.py -s rpool/ROOT/pve-1 -d Saturn/backup/ryzen-pve/pve-1 -H nas-pve
```

## 参考

- snapshot 脚本来自 [ibug](https://ibug.io/blog/2024/05/migrate-rootfs-to-zfs/)