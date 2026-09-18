param([string]$LogPath)
$ErrorActionPreference='Stop'
$sp=[System.IO.Ports.SerialPort]::new('COM3',57600,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$sp.Handshake=[System.IO.Ports.Handshake]::None
$sp.DtrEnable=$false
$sp.RtsEnable=$false
$sp.ReadTimeout=20
$sp.WriteTimeout=500
$sp.Open()
$buf=New-Object System.Text.StringBuilder
function Drain([int]$ms){
  $sw=[Diagnostics.Stopwatch]::StartNew()
  while($sw.ElapsedMilliseconds -lt $ms){
    try{$s=$sp.ReadExisting(); if($s.Length){[Console]::Write($s); [void]$script:buf.Append($s)}}catch{}
    Start-Sleep -Milliseconds 10
  }
}
try{
  Write-Host "UART_ESC_TEST_OPEN COM3 LOG=$LogPath"
  Drain 500
  Write-Host "SEND_REBOOT_THEN_SPAM_ESC_AND_4"
  $sp.Write("reboot`r")
  $sw=[Diagnostics.Stopwatch]::StartNew()
  while($sw.ElapsedMilliseconds -lt 16000){
    try{
      $s=$sp.ReadExisting(); if($s.Length){[Console]::Write($s); [void]$buf.Append($s)}
      if($sw.ElapsedMilliseconds -gt 200 -and $sw.ElapsedMilliseconds -lt 8000){
        $sp.Write([char]27)
        Start-Sleep -Milliseconds 15
        $sp.Write('4')
      }
    }catch{}
    Start-Sleep -Milliseconds 15
  }
  # If at CLI, ask a harmless command. If not at CLI/Linux shell, harmless text may be ignored or go to shell.
  $sp.Write("`r")
  Drain 500
  $sp.Write("version`r")
  Drain 2000
} finally {
  if($sp.IsOpen){$sp.Close()}
  [IO.File]::WriteAllText($LogPath,$buf.ToString(),[Text.UTF8Encoding]::new($false))
  Write-Host "`nUART_ESC_TEST_CLOSED bytes=$($buf.Length) log=$LogPath"
}
