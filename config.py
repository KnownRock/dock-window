import json
import os
import sys
from pathlib import Path

import argparse


def getConfig():

    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('--config', help='config file path',
                        required=False,
                        type=str)
    
    parser.add_argument('--raw', help='config json string',
                        required=False,
                        type=str)
    
    args = parser.parse_args()

    baseDirPath = Path(os.path.dirname(os.path.abspath(sys.argv[0])))
    
    if(args.config):
        configFilePath = (baseDirPath / args.config).resolve()
        with open(configFilePath, "r", encoding="utf8") as f:
            data = json.load(f)
    elif(args.raw):
        data = json.loads(args.raw)
    else:
        raise Exception("No config file or raw config string provided")

    if data['main_is_relative_path']:
        main_path = str((baseDirPath / data["main_path"]).resolve())
    else:
        main_path = data['main_path']

    if data['dock_is_relative_path']:
        dock_path = str((baseDirPath / data["dock_path"]).resolve())
    else:
        dock_path = data['dock_path']    
        
    # TODO: check parameters and does main_window_handler load 

    return {
        "main_path": main_path,
        "main_args": data["main_args"],

        "dock_path": dock_path,
        "dock_args": data["dock_args"],
        
        "dock_location": data["dock_location"],

        "wait_time": data["wait_time"],

        "dock_offset_y": data["dock_offset_y"],
        "dock_offset_x": data["dock_offset_x"],
        
        "main_window_handler_path": data["main_window_handler_path"],
        "main_window_handler_args": data["main_window_handler_args"],

        "run_command_with_shell": data["run_command_with_shell"],
        
        "hook": data.get("hook", '')
    }
