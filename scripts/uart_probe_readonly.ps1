param([string]$LogPath)
$ErrorActionPreference='Stop'
$sp=[System.IO.Ports.SerialPort]::new('COM3',57600,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$sp.Handshake=[System.IO.Ports.Handshake]::None
$sp.DtrEnable=$false
$sp.RtsEnable=$false
$sp.ReadTimeout=50
$sp.WriteTimeout=1000
$sp.Open()
$buf=New-Object System.Text.StringBuilder
function Read-For([int]$ms) {
  $sw=[Diagnostics.Stopwatch]::StartNew()
  while($sw.ElapsedMilliseconds -lt $ms){
    try { $s=$sp.ReadExisting(); if($s.Length -gt 0){ [Console]::Write($s); [void]$script:buf.Append($s) } } catch {}
    Start-Sleep -Milliseconds 20
  }
}
function Send-Line([string]$cmd,[int]$wait=900){
  $marker='__END_'+([guid]::NewGuid().ToString('N').Substring(0,8))+'__'
  $line=$cmd+"; echo $marker"
  Write-Host "`n>>> $cmd" -ForegroundColor Cyan
  [void]$buf.Append("`n>>> $cmd`n")
  $sp.Write($line+"`r")
  $deadline=(Get-Date).AddMilliseconds($wait)
  while((Get-Date) -lt $deadline){
    try { $s=$sp.ReadExisting(); if($s.Length -gt 0){ [Console]::Write($s); [void]$buf.Append($s); if($s -match [regex]::Escape($marker)){ break } } } catch {}
    Start-Sleep -Milliseconds 20
  }
  Read-For 250
}
try{
  Write-Host "UART_PROBE_OPEN COM3 57600 LOG=$LogPath"
  Read-For 700
  $sp.Write("`r")
  Read-For 500
  Send-Line 'echo READY; uname -a' 2000
  Send-Line 'cat /proc/mtd' 2000
  Send-Line 'cat /proc/cmdline' 2000
  Send-Line 'ls -l /dev/mtd* 2>/dev/null' 2000
  Send-Line 'for x in mtd_write mtd erase flashcp nandwrite dd wget tftp nc busybox md5sum sha256sum crc32; do which $x 2>/dev/null && $x --help 2>&1 | head -n 2; done' 5000
  Send-Line 'mount' 2500
  Send-Line 'df -h' 2500
  Send-Line 'ifconfig -a 2>/dev/null || ip addr 2>/dev/null' 5000
  Send-Line 'ps' 3000
  Send-Line 'dmesg | tail -n 80' 6000
} finally {
  if($sp.IsOpen){$sp.Close()}
  [IO.File]::WriteAllText($LogPath, $buf.ToString(), [Text.UTF8Encoding]::new($false))
  Write-Host "`nUART_PROBE_CLOSED bytes=$($buf.Length) log=$LogPath"
}
