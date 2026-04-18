# Sim Setter


## Windows

```powershell
py -3.11 -m venv .venv-win
.\.venv-win\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run_gui.py
```

```powershell
.\build.ps1
```

## Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python run_gui.py
```
```bash
sudo apt update
sudo apt install libgtk-3-0 libnotify4 libsm6 libsdl2-2.0-0 libxtst6 freeglut3
```

```bash
bash build-linux.sh
```


