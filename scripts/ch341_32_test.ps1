$ErrorActionPreference='Stop'
Write-Host ('is64bit_process=' + [Environment]::Is64BitProcess)
$src = @"
using System;
using System.Runtime.InteropServices;
public static class Ch341 {
  [DllImport("CH341DLL.DLL", CallingConvention=CallingConvention.StdCall)] public static extern IntPtr CH341OpenDevice(UInt32 iIndex);
  [DllImport("CH341DLL.DLL", CallingConvention=CallingConvention.StdCall)] public static extern void CH341CloseDevice(UInt32 iIndex);
  [DllImport("CH341DLL.DLL", CallingConvention=CallingConvention.StdCall)] public static extern UInt32 CH341GetVersion();
  [DllImport("CH341DLL.DLL", CallingConvention=CallingConvention.StdCall)] public static extern UInt32 CH341GetDrvVersion();
  [DllImport("CH341DLL.DLL", CallingConvention=CallingConvention.StdCall)] public static extern bool CH341SetStream(UInt32 iIndex, UInt32 iMode);
  [DllImport("CH341DLL.DLL", CallingConvention=CallingConvention.StdCall)] public static extern bool CH341StreamSPI4(UInt32 iIndex, UInt32 iChipSelect, UInt32 iLength, byte[] ioBuffer);
}
"@
Add-Type $src
Write-Host ('dll_version=0x{0:X8}' -f [Ch341]::CH341GetVersion())
Write-Host ('drv_version=0x{0:X8}' -f [Ch341]::CH341GetDrvVersion())
for($idx=0; $idx -lt 16; $idx++){
  $h=[Ch341]::CH341OpenDevice([uint32]$idx)
  $ok=($h -ne [IntPtr]::Zero -and $h.ToInt64() -ne -1)
  Write-Host ('idx={0} handle={1} ok={2}' -f $idx,$h,$ok)
  if($ok){
    try{
      $s=[Ch341]::CH341SetStream([uint32]$idx, [uint32]0x81)
      Write-Host ('set_stream=' + $s)
      foreach($cs in @(0,128,1,129)){
        [byte[]]$buf = 0x9F,0,0,0
        $r=[Ch341]::CH341StreamSPI4([uint32]$idx, [uint32]$cs, [uint32]4, $buf)
        Write-Host ('cs=0x{0:X2} ok={1} data={2}' -f $cs,$r,([BitConverter]::ToString($buf)))
      }
    } finally { [Ch341]::CH341CloseDevice([uint32]$idx); Write-Host 'closed' }
  }
}
