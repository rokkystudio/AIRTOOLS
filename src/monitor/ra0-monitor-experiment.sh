#!/bin/sh
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
