param([string]$RawLog,[string]$OutFile)
$ErrorActionPreference='Stop'
$sp=[System.IO.Ports.SerialPort]::new('COM3',57600,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$sp.Handshake=[System.IO.Ports.Handshake]::None; $sp.DtrEnable=$false; $sp.RtsEnable=$false; $sp.ReadTimeout=50; $sp.WriteTimeout=1000; $sp.Open()
$buf=New-Object System.Text.StringBuilder
function Drain($ms){$sw=[Diagnostics.Stopwatch]::StartNew(); while($sw.ElapsedMilliseconds -lt $ms){try{$s=$sp.ReadExisting(); if($s.Length){[Console]::Write($s); [void]$script:buf.Append($s)}}catch{}; Start-Sleep -Milliseconds 20}}
try{
  Write-Host "UART_HEX_OPEN $RawLog"
  Drain 500; $sp.Write("`r"); Drain 300
  $cmd='echo __HEX_BEGIN__; od -An -v -tx1 /dev/mtd2ro; echo __HEX_END__'
  Write-Host ">>> $cmd"
  $sp.Write($cmd+"`r")
  $deadline=(Get-Date).AddSeconds(75)
  while((Get-Date) -lt $deadline){
    try{$s=$sp.ReadExisting(); if($s.Length){[Console]::Write($s); [void]$buf.Append($s); if($buf.ToString().Contains('__HEX_END__')){break}}}catch{}
    Start-Sleep -Milliseconds 20
  }
} finally {
  if($sp.IsOpen){$sp.Close()}
}
$text=$buf.ToString()
[IO.File]::WriteAllText($RawLog,$text,[Text.UTF8Encoding]::new($false))
$start=$text.IndexOf('__HEX_BEGIN__')
$end=$text.IndexOf('__HEX_END__')
if($start -lt 0 -or $end -lt 0 -or $end -le $start){ throw 'markers not found' }
$hexText=$text.Substring($start+13, $end-$start-13)
$matches=[regex]::Matches($hexText,'(?i)\b[0-9a-f]{2}\b')
$bytes=New-Object byte[] $matches.Count
for($i=0;$i -lt $matches.Count;$i++){ $bytes[$i]=[Convert]::ToByte($matches[$i].Value,16) }
[IO.File]::WriteAllBytes($OutFile,$bytes)
Write-Host "UART_HEX_DONE bytes=$($bytes.Length) out=$OutFile raw=$RawLog"
