from pathlib import Path
import re
root = Path(r'D:\PROJECTS\ENDOSCOPE')
mon = root / 'services' / 'monitor'
mon.mkdir(parents=True, exist_ok=True)
script = r'''#!/bin/sh
# ENDOSCOPE wireless sniffer/monitor helper.
# Runtime-only: no persistent config or flash writes.
# Findings:
#   ra0 is STA with zero MAC and is unsafe to bring UP on this firmware.
#   ra1 is the active AP. Standard WEXT monitor mode is not supported.
#   safe path: ra1 promiscuous flag.
#   disruptive lab path: ra1 ATE RXFRAME; it deauths clients and temporarily breaks Wi-Fi.

LOG=/tmp/ra0-monitor-experiment.log
WD=/tmp/ra0-monitor-watchdog.pid
TMP=/tmp/ra0-monitor-command.out

stamp() { date '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo no-date; }
log() { line="[$(stamp)] $*"; echo "$line"; echo "$line" >> "$LOG"; }
section() { echo "--- $* ---"; echo "--- $* ---" >> "$LOG"; }
run_sh() {
    log "RUN $*"
    rm -f "$TMP"
    sh -c "$*" > "$TMP" 2>&1
    rc=$?
    cat "$TMP" 2>/dev/null
    cat "$TMP" >> "$LOG" 2>/dev/null
    log "RC $rc"
    return $rc
}
watchdog_start() {
    sec="$1"; [ -n "$sec" ] || sec=120
    cancel_watchdog >/dev/null 2>&1
    log "watchdog start ${sec}s"
    (sleep "$sec"; reboot -f) &
    echo $! > "$WD"
    log "watchdog pid $(cat "$WD" 2>/dev/null)"
}
cancel_watchdog() {
    if [ -f "$WD" ]; then
        pid=$(cat "$WD" 2>/dev/null)
        [ -n "$pid" ] && kill "$pid" 2>/dev/null
        rm -f "$WD"
        log "watchdog canceled"
    fi
}
inspect() {
    : > "$LOG"
    log "inspect begin"
    section "/proc/mtd"; run_sh 'cat /proc/mtd'
    section "/proc/net/dev"; run_sh 'cat /proc/net/dev'
    section "ifconfig -a"; run_sh 'ifconfig -a'
    section "iwconfig ra0"; run_sh 'iwconfig ra0'
    section "iwconfig ra1"; run_sh 'iwconfig ra1'
    section "iwpriv ra0"; run_sh 'iwpriv ra0'
    section "iwpriv ra1"; run_sh 'iwpriv ra1'
    section "modules"; run_sh 'cat /proc/modules'
    section "ps"; run_sh 'ps'
    log "inspect end"
}
driver_log() {
    section "dmesg tail"
    run_sh 'dmesg | tail -80 2>/dev/null || dmesg'
}
ra1_promisc_on() {
    : > "$LOG"
    log "ra1-promisc-on begin"
    section "before ra1"; run_sh 'ifconfig ra1; iwconfig ra1; cat /proc/net/dev'
    run_sh 'ifconfig ra1 promisc'
    section "after ra1"; run_sh 'ifconfig ra1; iwconfig ra1; cat /proc/net/dev'
    log "ra1-promisc-on end"
}
ra1_promisc_off() {
    log "ra1-promisc-off begin"
    run_sh 'ifconfig ra1 -promisc'
    section "after ra1"; run_sh 'ifconfig ra1; iwconfig ra1'
    log "ra1-promisc-off end"
}
ra1_ate_rx_sample() {
    if [ "$1" != "--yes" ]; then
        echo "DISRUPTIVE: ra1 ATE RXFRAME deauths Wi-Fi clients and may require reconnect/power-cycle."
        echo "Run via UART only: $0 ra1-ate-rx-sample --yes [channel] [seconds]"
        echo "Example: $0 ra1-ate-rx-sample --yes 11 3"
        return 2
    fi
    chan="$2"; [ -n "$chan" ] || chan=11
    sec="$3"; [ -n "$sec" ] || sec=3
    : > "$LOG"
    log "ra1-ate-rx-sample begin channel=$chan seconds=$sec"
    watchdog_start 120
    section "pre ra1"; run_sh 'ifconfig ra1; iwconfig ra1; cat /proc/net/dev'
    run_sh 'iwpriv ra1 set ATE=ATESTART'
    run_sh "iwpriv ra1 set ATECHANNEL=$chan"
    run_sh 'iwpriv ra1 set ATE=RXFRAME'
    run_sh "sleep $sec"
    run_sh 'iwpriv ra1 set ATE=ATESHOW'
    run_sh 'iwpriv ra1 set ATE=ATESTOP'
    run_sh 'ifconfig ra1 192.168.10.123 netmask 255.255.255.0 up'
    run_sh 'killall udhcpd 2>/dev/null; udhcpd /etc_ro/udhcpd.conf'
    section "post ra1"; run_sh 'ifconfig ra1; iwconfig ra1; cat /proc/net/dev'
    section "driver log"; run_sh 'dmesg | tail -120 2>/dev/null || dmesg'
    cancel_watchdog
    log "ra1-ate-rx-sample end; reconnect Wi-Fi client if needed"
}
ra1_ate_stop() {
    log "ra1-ate-stop begin"
    run_sh 'iwpriv ra1 set ATE=ATESTOP'
    run_sh 'ifconfig ra1 192.168.10.123 netmask 255.255.255.0 up'
    run_sh 'killall udhcpd 2>/dev/null; udhcpd /etc_ro/udhcpd.conf'
    section "after stop"; run_sh 'ifconfig ra1; iwconfig ra1'
    log "ra1-ate-stop end"
}
try_ra0_monitor_disabled() {
    echo "DISABLED: ra0 monitor attempt is unsafe on this device."
    echo "Observed: ra0 is Ralink STA with MAC 00:00:00:00:00:00; ra0 up can drop/hang radio path."
    echo "Use instead:"
    echo "  $0 ra1-promisc-on"
    echo "  $0 ra1-promisc-off"
    echo "  $0 ra1-ate-rx-sample --yes 11 3   # UART only; disruptive"
    return 3
}
case "$1" in
    inspect) inspect ;;
    driver-log) driver_log ;;
    watchdog-start) shift; watchdog_start "$1" ;;
    cancel-watchdog) cancel_watchdog ;;
    ra1-promisc-on) ra1_promisc_on ;;
    ra1-promisc-off) ra1_promisc_off ;;
    ra1-ate-rx-sample) shift; ra1_ate_rx_sample "$@" ;;
    ra1-ate-stop) ra1_ate_stop ;;
    try-ra0-monitor) try_ra0_monitor_disabled ;;
    restore-ra0) try_ra0_monitor_disabled ;;
    *)
        echo "Usage: $0 [inspect|driver-log|ra1-promisc-on|ra1-promisc-off|ra1-ate-rx-sample --yes [channel] [seconds]|ra1-ate-stop|cancel-watchdog]"
        exit 2
        ;;
esac
'''
readme = r'''ENDOSCOPE ra0 monitor experiment
=================================

This firmware variant is connectivity/internet plus a manual monitor-mode experiment helper.
Normal boot path is unchanged: the helper is not auto-started.

Runtime helper:
  /bin/ra0-monitor-experiment inspect
  /bin/ra0-monitor-experiment try-ra0-monitor --yes
  /bin/ra0-monitor-experiment cancel-watchdog
  /bin/ra0-monitor-experiment restore-ra0

Safety rules:
- writes only to /tmp/ra0-monitor-experiment.log and /tmp/ra0-monitor-watchdog.pid
- does not call nvram_set, flash, mtd_write, config_save.sh, or write /dev/mtd*
- does not change ra1 mode; ra1 is the active AP
- arms a reboot watchdog before risky ra0 runtime monitor attempts

Goal:
Verify whether ra0 can enter monitor/sniffer mode while ra1 remains usable as AP.
If ra0 disrupts ra1 or no monitor ioctl is exposed, stop and reboot/power-cycle.
'''
probe_c = r'''/*
 * Reference source for a minimal AF_PACKET metadata probe.
 * Not compiled into this image because no MIPS cross-compiler is currently present in the project.
 * Intended future behavior: bind to ra0 and print only packet metadata / first header bytes to stdout.
 * No payload storage, no reconstruction, no flash writes.
 */
'''
(mon / 'ra0-monitor-experiment.sh').write_bytes(script.encode('utf-8'))
(mon / 'README.ra0-monitor.txt').write_bytes(readme.encode('utf-8'))
(mon / 'ra0_packet_probe.c').write_bytes(probe_c.encode('utf-8'))

src = root / 'services' / 'connectivity' / 'build-mtd4.py'
dst = root / 'services' / 'connectivity' / 'build-mtd4-connectivity-monitor.py'
s = src.read_text(encoding='utf-8')
s = s.replace('Builds a persistent ENDOSCOPE mtd4 image with the local connectivity service.',
              'Builds a persistent ENDOSCOPE mtd4 image with connectivity plus a manual ra0 monitor experiment helper.')
s = s.replace('OUTPUT_MTD4 = OUTPUT_DIR / "mtd4_connectivity.bin"',
              'OUTPUT_MTD4 = OUTPUT_DIR / "mtd4_connectivity_monitor.bin"')
s = s.replace('SERVICE = ROOT / "services" / "connectivity" / "endoscope-connectivity"',
              'SERVICE = ROOT / "services" / "connectivity" / "endoscope-connectivity"\nMONITOR_SCRIPT = ROOT / "services" / "monitor" / "ra0-monitor-experiment.sh"\nMONITOR_README = ROOT / "services" / "monitor" / "README.ra0-monitor.txt"\nMONITOR_PROBE_SOURCE = ROOT / "services" / "monitor" / "ra0_packet_probe.c"')
old = '''    if not inserted_service:
        raise ValueError("app_detect slot not found for connectivity daemon")

    return result
'''
new = '''    if not inserted_service:
        raise ValueError("app_detect slot not found for connectivity daemon")

    max_ino = max(entry.ino for entry in result)

    def add_monitor_file(name: str, data: bytes, mode: int) -> None:
        nonlocal max_ino
        max_ino += 1
        result.append(
            CpioEntry(
                name=name,
                ino=max_ino,
                mode=mode,
                uid=app_detect_template.uid,
                gid=app_detect_template.gid,
                nlink=1,
                mtime=app_detect_template.mtime,
                data=data,
                devmajor=app_detect_template.devmajor,
                devminor=app_detect_template.devminor,
                rdevmajor=0,
                rdevminor=0,
                check=0,
            )
        )

    add_monitor_file("bin/ra0-monitor-experiment", MONITOR_SCRIPT.read_bytes(), 0o100755)
    add_monitor_file("etc_ro/ra0-monitor-experiment.README", MONITOR_README.read_bytes(), 0o100644)
    add_monitor_file("etc_ro/ra0_packet_probe.c", MONITOR_PROBE_SOURCE.read_bytes(), 0o100644)

    return result
'''
if old not in s:
    raise SystemExit('transform_entries replacement anchor not found')
s = s.replace(old, new, 1)
s = s.replace('if "bin/endoscope-connectivity" not in new_names:\n        raise AssertionError("connectivity daemon missing from rebuilt rootfs")',
'''if "bin/endoscope-connectivity" not in new_names:
        raise AssertionError("connectivity daemon missing from rebuilt rootfs")
    if "bin/ra0-monitor-experiment" not in new_names:
        raise AssertionError("ra0 monitor experiment helper missing from rebuilt rootfs")
    if "etc_ro/ra0-monitor-experiment.README" not in new_names:
        raise AssertionError("ra0 monitor README missing from rebuilt rootfs")''')
dst.write_text(s, encoding='utf-8')
print('WROTE', dst)
print('WROTE', mon / 'ra0-monitor-experiment.sh')
print('WROTE', mon / 'README.ra0-monitor.txt')
print('WROTE', mon / 'ra0_packet_probe.c')
