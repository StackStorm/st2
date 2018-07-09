[CmdletBinding()]
Param(
  [bool]$p_bool,
  [int]$p_integer,
  [double]$p_number,
  [string]$p_str,
  [array]$p_array,
  [hashtable]$p_obj,
  [Parameter(Position=0)]
  [string]$p_pos0,
  [Parameter(Position=1)]
  [string]$p_pos1
)


Write-Output "p_bool = $p_bool"
Write-Output "p_integer = $p_integer"
Write-Output "p_number = $p_number"
Write-Output "p_str = $p_str"
Write-Output "p_array = $($p_array | ConvertTo-Json -Compress)"
Write-Output "p_obj = $($p_obj | ConvertTo-Json -Compress)"
Write-Output "p_pos0 = $p_pos0"
Write-Output "p_pos1 = $p_pos1"
