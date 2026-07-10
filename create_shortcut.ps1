$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut("C:\Users\frank\OneDrive\Desktop\Transkriptor.lnk")
$shortcut.TargetPath = "C:\Users\frank\First Try\transcriptor\start.bat"
$shortcut.WorkingDirectory = "C:\Users\frank\First Try\transcriptor"
$shortcut.WindowStyle = 1
$shortcut.Description = "NeuralNautic Transkriptor"
$shortcut.Save()
Write-Host "Shortcut erstellt!"
