# Sim Setter

Utility for adding or removing 9ms offset from simfiles

Offset logic copied from [nine-or-null](https://github.com/telperion/nine-or-null)

Download Releases: https://github.com/sjrc6/sim-setter/releases

You can either download a release executable or run the python scripts directly with the instructions below


## Windows

```powershell
py -3.11 -m venv .venv-win
.\.venv-win\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run_gui.py
```
### Build executable

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

If wxPython does not install correctly try these

```bash
sudo apt update
sudo apt install libgtk-3-0 libnotify4 libsm6 libsdl2-2.0-0 libxtst6 freeglut3
```
### Build executable

```bash
bash build-linux.sh
```
