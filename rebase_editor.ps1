param($file)
(Get-Content $file) | ForEach-Object { if ($_.ReadCount -le 2) { $_ -replace '^pick', 'edit' } else { $_ } } | Set-Content $file
