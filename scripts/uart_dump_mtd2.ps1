param([string]$LogPath)
$ErrorActionPreference='Stop'
$sp=[System.IO.Ports.SerialPort]::new('COM3',57600,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$sp.Handshake=[System.IO.Ports.Handshake]::None; $sp.DtrEnable=$false; $sp.RtsEnable=$false; $sp.ReadTimeout=50; $sp.WriteTimeout=1000; $sp.Open()
$buf=New-Object System.Text.StringBuilder
function Drain($ms){$sw=[Diagnostics.Stopwatch]::StartNew(); while($sw.ElapsedMilliseconds -lt $ms){try{$s=$sp.ReadExisting(); if($s.Length){[Console]::Write($s); [void]$script:buf.Append($s)}}catch{}; Start-Sleep -Milliseconds 20}}
function Cmd($cmd,$ms){Write-Host "`n>>> $cmd"; [void]$buf.Append("`n>>> $cmd`n"); $sp.Write($cmd+"`r"); Drain $ms}
try{
  Write-Host "UART_OPEN $LogPath"; Drain 500; $sp.Write("`r"); Drain 300
  Cmd 'cat /dev/mtd2ro > /tmp/mtd2_current.bin; sync; ls -l /tmp/mtd2_current.bin' 5000
  Cmd 'tftp -p -l /tmp/mtd2_current.bin -r mtd2_current.bin 192.168.10.36' 12000
  Cmd 'echo TFTP_SENT; ls -l /tmp/mtd2_current.bin' 2000
} finally {if($sp.IsOpen){$sp.Close()}; [IO.File]::WriteAllText($LogPath,$buf.ToString(),[Text.UTF8Encoding]::new($false)); Write-Host "`nUART_CLOSED bytes=$($buf.Length) log=$LogPath"}
