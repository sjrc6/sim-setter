param(
    [string]$Name = "SimSetter"
)

$ErrorActionPreference = "Stop"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name $Name run_gui.py

Write-Host "Built dist\$Name.exe"
