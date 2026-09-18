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
  $marker='__M_'+([guid]::NewGuid().ToString('N').Substring(0,10))+'__'
  $line="($cmd); echo $marker"
  Write-Host "`n>>> $cmd" -ForegroundColor Cyan
  [void]$buf.Append("`n>>> $cmd`n")
  $sp.Write($line+"`r")
  $deadline=(Get-Date).AddMilliseconds($wait)
  while((Get-Date) -lt $deadline){
    try {
      $s=$sp.ReadExisting()
      if($s.Length -gt 0){
        [Console]::Write($s); [void]$buf.Append($s)
        if(($buf.ToString()) -match [regex]::Escape($marker)){ break }
      }
    } catch {}
    Start-Sleep -Milliseconds 20
  }
  Read-For 300
}
try{
  Write-Host "UART_MTD2_WRITE_OPEN COM3 LOG=$LogPath"
  Read-For 300
  $sp.Write("`r")
  Read-For 500
  Send-Line 'echo READY; cat /proc/mtd; cd /tmp; rm -f mtd2_config_BootType3.bin; ls -l /tmp' 3000
  Send-Line 'cd /tmp; tftp -g -r mtd2_config_BootType3.bin -l mtd2_config_BootType3.bin 192.168.10.36' 30000
  Send-Line 'cd /tmp; echo FILE_CHECK; ls -l mtd2_config_BootType3.bin; wc -c mtd2_config_BootType3.bin 2>/dev/null || echo NO_WC' 4000
  Send-Line 'cd /tmp; echo START_MTD2_WRITE; mtd_write -w write mtd2_config_BootType3.bin Config; echo MTD2_WRITE_RET:$?; sync; echo MTD2_SYNC_DONE' 60000
} finally {
  if($sp.IsOpen){$sp.Close()}
  [IO.File]::WriteAllText($LogPath, $buf.ToString(), [Text.UTF8Encoding]::new($false))
  Write-Host "`nUART_MTD2_WRITE_CLOSED bytes=$($buf.Length) log=$LogPath"
}
