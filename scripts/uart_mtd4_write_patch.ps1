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
function Send-Line([string]$cmd,[int]$wait=1000){
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
  Read-For 500
}
try{
  Write-Host "UART_MTD4_WRITE_OPEN COM3 LOG=$LogPath"
  Read-For 300
  $sp.Write("`r")
  Read-For 500
  Send-Line 'cd /tmp; ls -l mtd4_connectivity.bin; cat /proc/mtd' 3000
  Send-Line 'cd /tmp; echo START_MTD4_WRITE; mtd_write -w write mtd4_connectivity.bin Kernel; echo MTD_WRITE_RET:$?; sync; echo SYNC_DONE' 120000
} finally {
  if($sp.IsOpen){$sp.Close()}
  [IO.File]::WriteAllText($LogPath, $buf.ToString(), [Text.UTF8Encoding]::new($false))
  Write-Host "`nUART_MTD4_WRITE_CLOSED bytes=$($buf.Length) log=$LogPath"
}
