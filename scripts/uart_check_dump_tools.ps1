param([string]$LogPath)
$ErrorActionPreference='Stop'
$sp=[System.IO.Ports.SerialPort]::new('COM3',57600,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$sp.Handshake=[System.IO.Ports.Handshake]::None; $sp.DtrEnable=$false; $sp.RtsEnable=$false; $sp.ReadTimeout=50; $sp.WriteTimeout=1000; $sp.Open()
$buf=New-Object System.Text.StringBuilder
function Drain($ms){$sw=[Diagnostics.Stopwatch]::StartNew(); while($sw.ElapsedMilliseconds -lt $ms){try{$s=$sp.ReadExisting(); if($s.Length){[Console]::Write($s); [void]$script:buf.Append($s)}}catch{}; Start-Sleep -Milliseconds 20}}
function Cmd($cmd,$ms){Write-Host "`n>>> $cmd"; [void]$buf.Append("`n>>> $cmd`n"); $sp.Write($cmd+"`r"); Drain $ms}
try{Write-Host "UART_OPEN"; Drain 500; $sp.Write("`r"); Drain 300; Cmd 'for c in hexdump xxd base64 uuencode busybox flash dd cat tftp tftpd ftpput ftpget nc; do echo -n "$c="; which $c 2>/dev/null || echo no; done' 5000; Cmd 'busybox 2>&1 | head 2; busybox hexdump 2>&1 | head 3; flash -r 30000 -c 16 2>&1' 6000} finally {if($sp.IsOpen){$sp.Close()}; [IO.File]::WriteAllText($LogPath,$buf.ToString(),[Text.UTF8Encoding]::new($false)); Write-Host "`nUART_CLOSED log=$LogPath bytes=$($buf.Length)"}
