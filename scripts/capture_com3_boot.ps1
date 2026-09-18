param(
  [string]$LogPath,
  [int]$Seconds = 45
)
$ErrorActionPreference='Stop'
$portName='COM3'
$baud=57600
$sp=[System.IO.Ports.SerialPort]::new($portName,$baud,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$sp.Handshake=[System.IO.Ports.Handshake]::None
$sp.DtrEnable=$false
$sp.RtsEnable=$false
$sp.ReadTimeout=50
$sp.WriteTimeout=500
$sp.Open()
$sw=[System.Diagnostics.Stopwatch]::StartNew()
$buf = New-Object System.Text.StringBuilder
try {
  Write-Host "CAPTURE_OPEN $portName $baud 8N1 LOG=$LogPath"
  Write-Host 'CAPTURE_WAITING'
  while ($sw.Elapsed.TotalSeconds -lt $Seconds) {
    try {
      $s=$sp.ReadExisting()
      if ($s.Length -gt 0) {
        [Console]::Write($s)
        [void]$buf.Append($s)
      }
    } catch {}
    Start-Sleep -Milliseconds 20
  }
} finally {
  if ($sp.IsOpen) { $sp.Close() }
  $text=$buf.ToString()
  [System.IO.File]::WriteAllText($LogPath, $text, [System.Text.UTF8Encoding]::new($false))
  Write-Host "`nCAPTURE_CLOSED bytes=$($text.Length) log=$LogPath"
}
