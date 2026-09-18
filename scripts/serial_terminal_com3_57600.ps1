$ErrorActionPreference = 'Stop'
$portName = 'COM3'
$baud = 57600

Write-Host "Opening $portName @ $baud 8N1" -ForegroundColor Cyan
Write-Host "Keys: type normally to send; Esc exits; Ctrl+C also exits." -ForegroundColor Yellow
Write-Host "Power-cycle the board now if needed." -ForegroundColor Yellow
Write-Host ""

$sp = [System.IO.Ports.SerialPort]::new($portName, $baud, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
$sp.Handshake = [System.IO.Ports.Handshake]::None
$sp.DtrEnable = $false
$sp.RtsEnable = $false
$sp.ReadTimeout = 50
$sp.WriteTimeout = 500
$sp.NewLine = "`r`n"
$sp.Open()
try {
    while ($true) {
        try {
            $s = $sp.ReadExisting()
            if ($s.Length -gt 0) { [Console]::Write($s) }
        } catch {}

        while ([Console]::KeyAvailable) {
            $k = [Console]::ReadKey($true)
            if ($k.Key -eq [ConsoleKey]::Escape) { throw 'USER_EXIT' }
            if ($k.Key -eq [ConsoleKey]::Enter) {
                $sp.Write("`r")
                [Console]::WriteLine()
            } elseif ($k.Key -eq [ConsoleKey]::Backspace) {
                $sp.Write([byte[]](0x08), 0, 1)
                [Console]::Write("`b `b")
            } elseif ($k.KeyChar -ne 0) {
                $ch = [string]$k.KeyChar
                $bytes = [System.Text.Encoding]::ASCII.GetBytes($ch)
                $sp.Write($bytes, 0, $bytes.Length)
                [Console]::Write($ch)
            }
        }
        Start-Sleep -Milliseconds 10
    }
}
catch {
    if ($_.Exception.Message -ne 'USER_EXIT') { Write-Host $_ -ForegroundColor Red }
}
finally {
    if ($sp.IsOpen) { $sp.Close() }
    Write-Host "`nClosed $portName" -ForegroundColor Cyan
}
