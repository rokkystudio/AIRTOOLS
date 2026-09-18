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
function Drain([int]$ms){
  $sw=[Diagnostics.Stopwatch]::StartNew()
  while($sw.ElapsedMilliseconds -lt $ms){
    try { $s=$sp.ReadExisting(); if($s.Length -gt 0){ [Console]::Write($s); [void]$script:buf.Append($s) } } catch {}
    Start-Sleep -Milliseconds 20
  }
}
function Cmd([string]$cmd,[int]$ms){
  Write-Host "`n>>> $cmd" -ForegroundColor Cyan
  [void]$buf.Append("`n>>> $cmd`n")
  $sp.Write($cmd+"`r")
  Drain $ms
}
try{
  Write-Host "UART_PING_FIXED_OPEN COM3 LOG=$LogPath"
  Drain 500
  $sp.Write("`r")
  Drain 500
  Cmd 'ps | grep -E "connectivity|ping|telnetd"' 3000
  Cmd 'route -n' 2500
  Cmd 'ping -c 2 -W 2 192.168.10.36' 7000
  Cmd 'ping -c 2 -W 2 8.8.8.8' 9000
} finally {
  if($sp.IsOpen){$sp.Close()}
  [IO.File]::WriteAllText($LogPath, $buf.ToString(), [Text.UTF8Encoding]::new($false))
  Write-Host "`nUART_PING_FIXED_CLOSED bytes=$($buf.Length) log=$LogPath"
}
