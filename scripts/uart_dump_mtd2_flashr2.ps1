param([string]$RawLog,[string]$OutFile)
$ErrorActionPreference='Stop'
$sp=[System.IO.Ports.SerialPort]::new('COM3',57600,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$sp.Handshake=[System.IO.Ports.Handshake]::None; $sp.DtrEnable=$false; $sp.RtsEnable=$false; $sp.ReadTimeout=50; $sp.WriteTimeout=1000; $sp.Open()
$buf=New-Object System.Text.StringBuilder
function Drain($ms){$sw=[Diagnostics.Stopwatch]::StartNew(); while($sw.ElapsedMilliseconds -lt $ms){try{$s=$sp.ReadExisting(); if($s.Length){[Console]::Write($s); [void]$script:buf.Append($s)}}catch{}; Start-Sleep -Milliseconds 20}}
function CountSub($text,$sub){ return ([regex]::Matches($text,[regex]::Escape($sub))).Count }
try{
  Write-Host "UART_FLASHR2_OPEN $RawLog"
  Drain 500; $sp.Write("`r"); Drain 300
  $cmd='echo __M2_BEGIN__; flash -r 30000 -c 65536; echo __M2_END__'
  Write-Host ">>> $cmd"
  $sp.Write($cmd+"`r")
  $deadline=(Get-Date).AddSeconds(100)
  while((Get-Date) -lt $deadline){
    try{$s=$sp.ReadExisting(); if($s.Length){[Console]::Write($s); [void]$buf.Append($s)}}catch{}
    if((CountSub $buf.ToString() '__M2_END__') -ge 2){break}
    Start-Sleep -Milliseconds 20
  }
} finally {if($sp.IsOpen){$sp.Close()}}
$text=$buf.ToString(); [IO.File]::WriteAllText($RawLog,$text,[Text.UTF8Encoding]::new($false))
# use content after first standalone begin line and before second end marker
$firstBegin=$text.IndexOf('__M2_BEGIN__')
$secondBegin=$text.IndexOf('__M2_BEGIN__',$firstBegin+1)
$firstEnd=$text.IndexOf('__M2_END__')
$secondEnd=$text.IndexOf('__M2_END__',$firstEnd+1)
if($secondEnd -lt 0){ throw 'second end marker not found' }
$start = if($secondBegin -ge 0){ $secondBegin + 12 } else { $firstBegin + 12 }
$body=$text.Substring($start, $secondEnd-$start)
$runs=[regex]::Matches($body,'(?i)[0-9a-f]{64,}')
if($runs.Count -eq 0){ throw 'no long hex run' }
$best=$runs | Sort-Object Length -Descending | Select-Object -First 1
$hex=$best.Value
if(($hex.Length % 2) -ne 0){ $hex=$hex.Substring(0,$hex.Length-1) }
$bytes=New-Object byte[] ($hex.Length/2)
for($i=0;$i -lt $bytes.Length;$i++){ $bytes[$i]=[Convert]::ToByte($hex.Substring($i*2,2),16) }
[IO.File]::WriteAllBytes($OutFile,$bytes)
Write-Host "UART_FLASHR2_DONE bytes=$($bytes.Length) out=$OutFile raw=$RawLog"
