$ErrorActionPreference = "Stop"
$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $Python -m pip install -r requirements.txt
& $Python plugins/sci-ppt/skills/sci-ppt/scripts/doctor.py
Write-Host "Sci-PPT installed successfully."
