ENDOSCOPE ra0 monitor experiment
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
