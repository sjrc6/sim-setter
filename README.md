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
sudo apt install python3-dev build-essential libgtk-3-dev libjpeg-dev libpng-dev libtiff-dev libsdl2-dev libnotify-dev libsm-dev freeglut3-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
```

```bash
bash build-linux.sh
```



