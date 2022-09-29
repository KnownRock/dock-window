# dock window
Start two executable files, make one dock to another.

## installation
```bash
pip install pywin32
```

## build
```bash
pyinstaller main.spec
```

## run
```
.\main.exe --config config.json 
```

## config 
main_path: the path of the main executable file

dock_path: the path of the dock executable file

main_window_handler_path: the path of the main window handler file

main_window_handler_args: the args of the main window handler file({main_hwmd} will be replaced by the main window handler {dock_hwmd} will be replaced by the dock window handler)
(see [main.py](main.py))

