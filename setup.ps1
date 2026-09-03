$ErrorActionPreference = "Stop"
$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $Python -m pip install -r requirements.txt
& $Python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/doctor.py
Write-Host "Codex Sci-PPT installed successfully."
