---
name: linux-ops-cheatsheet
description: >-
  Linux system administration cheatsheet of memory/IO diagnostics, available-RAM
  capping via the bootloader, job backgrounding, and emergency reboot. Use when
  the user asks how to inspect memory or disk IO usage on Linux, limit usable RAM
  for testing, detach a running process to the background and survive a logout,
  or force a host to restart via SysRq. Covers Red Hat / Fedora (GRUB Legacy and
  GRUB2). NOT for algorithm or data-structure questions.
keywords:
  - linux
  - sysadmin
  - free
  - iostat
  - sysrq
  - reboot
  - grub
  - mem= boot parameter
  - disown
  - bg
  - background process
allowed-tools:
  - Bash
---

# Linux Ops Cheatsheet / Linux 运维速查

System-administration one-liners for Linux hosts. Read-only diagnostics are
safe to run as-is. Commands that touch the kernel, the bootloader, or running
processes carry explicit DANGER markers and confirmation gates — read them
before you paste.

## When to use / 何时使用

- Inspect memory usage (`free`) or disk IO (`iostat`).
- Cap the kernel's usable RAM for low-memory testing (`mem=` boot param).
- Detach a foreground job to the background so it survives logout (`bg` + `disown`).
- Force an unresponsive host to reboot via the SysRq interface — **last resort only**.

Do NOT use this skill for algorithm or data-structure design questions; the file
name in the upstream corpus was mislabeled "algorithms" but the content is Linux ops.

## Global preconditions / 全局前提

- Distro examples target **Red Hat / Fedora family**. Paths differ on Debian/Ubuntu/SUSE.
- Bootloader and SysRq actions require **root** (`sudo` or a root shell).
- `iostat` ships in the `sysstat` package (`sudo yum install sysstat` / `sudo dnf install sysstat`).

---

## 1. Memory usage (read-only / 只读) — 查看内存使用情况

No guard needed; this only reads counters.

```bash
free -m          # show memory usage in MB / 以 MB 为单位查看内存使用情况
```

Verify: output prints `Mem:` and `Swap:` rows. Add `-h` for human-readable units.

---

## 2. Disk IO statistics (read-only / 只读) — 查看系统的 IO 统计信息

No guard needed; this only samples kernel IO counters.

```bash
iostat -k 3      # print in KB, refresh every 3 seconds / 以 KB 打印结果，3 秒显示一次
```

Precondition: `sysstat` installed (see Global preconditions). Stop with Ctrl+C.
Verify: per-device `tps`/`kB_read/s`/`kB_wrtn/s` columns appear and update.

---

## 3. Run a job in the background, surviving logout — 进程放入后台并脱离前台

Useful over SSH so a long job is not killed when the connection drops.
Non-destructive to data, but `disown` removes the job from the shell's job
table, so you can no longer `fg`/`kill %n` it from this shell afterwards.

```bash
./test           # 1. start the program / 运行程序
# 2. press Ctrl+Z to suspend it / 按 Ctrl+Z 使程序暂停
bg %1            # 3. resume it in the background (%1 = job number from `jobs`) / 将程序放入后台运行
disown -h %1     # 4. shield it from SIGHUP on logout / 退出登录时不再收到 SIGHUP
```

Replace `%1` with the actual job id shown by `jobs`. The original upstream text
used the invalid placeholder `%(jobid)` — that is not real shell syntax.
Precondition: run inside the same interactive shell that started the job.
Verify: `jobs` lists it as `Running` after `bg`; after `disown` it disappears
from `jobs` but `ps aux | grep test` still shows the process.

Note: the original C-style `//` comments have been removed — `//` is **not** a
shell comment and pasting it verbatim would error or be misparsed. Shell uses `#`.

---

## 4. Cap usable RAM via the bootloader — 修改计算机的可用内存

> [!CAUTION]
> ⚠️ DANGER — PERSISTENT BOOT CHANGE / 危险：持久化引导修改
> Editing the GRUB config changes how the machine boots **on every subsequent
> reboot**, not just once. A typo in this file can leave the host unbootable.
> 编辑 GRUB 配置会影响**之后每一次重启**，写错可能导致系统无法启动。
> Confirmation required before applying. Back up the config first.

The `mem=1G` kernel parameter caps the RAM the kernel will use (e.g. to simulate
a low-memory box). It does not change physical RAM.

**Step 0 — back up the bootloader config first (mandatory):**

```bash
# GRUB Legacy (older RHEL/CentOS 5/6, Fedora ≤15):
sudo cp -a /etc/grub.conf /etc/grub.conf.bak.$(date +%F)

# GRUB2 (RHEL/CentOS 7+, modern Fedora):
sudo cp -a /etc/default/grub /etc/default/grub.bak.$(date +%F)
```

**GRUB Legacy** — append `mem=1G` to the end of the `kernel` line in
`/etc/grub.conf`:

```text
title Red Hat Enterprise Linux Server (2.6.27)
        root (hd0,1)
        kernel /vmlinuz-2.6.27 ro root=/dev/VolGroup00/LogVol00 rhgb quiet acpi=ht mem=1G
        initrd /initrd-2.6.27.img
```

**GRUB2** — do NOT hand-edit `/etc/grub.conf` (it is generated). Instead add the
parameter to `GRUB_CMDLINE_LINUX` in `/etc/default/grub`, then regenerate:

```bash
# Add mem=1G inside the GRUB_CMDLINE_LINUX="..." string, then:
sudo grub2-mkconfig -o /boot/grub2/grub.cfg
```

Verify (after the next reboot): `free -m` total drops to ~1 GB, and
`cat /proc/cmdline` shows `mem=1G`.
Roll back: restore the `.bak` file you created in Step 0 and regenerate (GRUB2)
or just reboot (GRUB Legacy).

---

## 5. Force-reboot a host via SysRq — 远程/强制重启计算机

> [!CAUTION]
> ⚠️⚠️ EXTREME DANGER — IMMEDIATE UNSYNCED REBOOT / 极度危险：立即强制重启
> `echo b > /proc/sysrq-trigger` reboots the machine **instantly**, equivalent
> to pulling the power cord. It does NOT flush disk buffers — any unwritten
> (dirty) data is **lost** and filesystems may need recovery on next boot.
> 该命令等同于直接拔电源，不会刷盘，脏数据会丢失，可能导致文件系统损坏。
> Confirmation required. This is a **last resort** for a hung host only.

**For normal reboots, use the safe path instead — these sync and shut services down cleanly:**

```bash
sudo reboot                 # graceful reboot / 正常重启
sudo shutdown -r now        # graceful reboot, now / 立即正常重启
```

**If you genuinely must use SysRq** (host is hung and won't respond to `reboot`),
use the safe "REISUB"-style sequence so data is flushed first — never `b` alone:

```bash
# Run as root. Each step is deliberate; do NOT skip s and u.
echo s > /proc/sysrq-trigger    # Sync: flush dirty buffers to disk / 刷盘
echo u > /proc/sysrq-trigger    # Unmount: remount all filesystems read-only / 重新只读挂载
echo b > /proc/sysrq-trigger    # Boot: reboot immediately (host restarts here) / 立即重启
```

Precondition: SysRq must be enabled — check `cat /proc/sys/kernel/sysrq`
(0 = disabled). Enable temporarily with `echo 1 > /proc/sys/kernel/sysrq`.
After `s`, wait a moment for the sync to complete before `u`/`b`.
Verify: the host reboots; on return, `dmesg`/journal should NOT report dirty
filesystem recovery if `s` and `u` were issued correctly.

---

## Safety summary / 安全摘要

| # | Command | Risk | Guard |
|---|---------|------|-------|
| 1 | `free -m` | none (read-only) | — |
| 2 | `iostat -k 3` | none (read-only) | — |
| 3 | `bg %1` / `disown -h %1` | loses shell job control | precondition + verify |
| 4 | edit GRUB `mem=1G` | PERSISTENT boot change | backup + confirm + GRUB2 path |
| 5 | `echo b > /proc/sysrq-trigger` | INSTANT data loss | sync-first REISUB + prefer `reboot` + confirm |
