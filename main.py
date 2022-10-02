import os
import subprocess
import win32.win32process as win32process
import win32.win32process as process
import win32.win32gui as win32gui
import sys
import ctypes
import ctypes.wintypes
from time import sleep
from threading import Thread
from win32.win32gui import GetWindowRect, GetWindowText
from win32.win32api import CloseHandle, OpenProcess

from config import getConfig


import hooks.scrcpy as scrcpy


hooks = {
    'scrcpy': scrcpy.get_instance()
}


def isLiveProcess(processHandler):
    processList = process.EnumProcesses()
    for aProcess in processList:
        if (aProcess == processHandler):
            return True
    return False


def initProcess(exePath, args=None):
    print('initProcess', exePath, args)

    PORTABLE_APPLICATION_LOCATION = exePath

    return subprocess.Popen(PORTABLE_APPLICATION_LOCATION + ' ' + args)


def getHwndRect(hwnd):
    x, y, xpw, yph = GetWindowRect(hwnd)
    rx, ry, rxpw, ryph = x , y, xpw , yph
    return (rx, ry, rxpw, ryph)


def moveHwnd(hwnd, order, x, y, xpw, yph, b_repaint):
    win32gui.SetWindowPos(hwnd, order, x, y, xpw, yph, b_repaint)


def startListener(processHandler, onWindowChange, onOrderChange):
    listenerThreadIds = []
    # https://docs.microsoft.com/en-us/windows/win32/winauto/event-constants
    # https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwineventhook
    EVENT_OBJECT_LOCATIONCHANGE = 0x800B
    EVENT_OBJECT_REORDER = 0x8004
    EVENT_OBJECT_DESTROY = 0x8001
    WM_CLOSE = 0x0010
    events = [
        [
            onWindowChange,
            ctypes.WINFUNCTYPE( #WinEventProcType
                None,
                ctypes.wintypes.HANDLE,
                ctypes.wintypes.LONG,
                ctypes.wintypes.HWND,
                ctypes.wintypes.LONG,
                ctypes.wintypes.LONG,
                ctypes.wintypes.UINT,
                ctypes.wintypes.UINT
            ),
            EVENT_OBJECT_LOCATIONCHANGE,
            0x0003
        ],
        [
            onOrderChange,
            ctypes.WINFUNCTYPE( #WinEventProcType
                None,
                ctypes.wintypes.HANDLE,
                ctypes.wintypes.LONG,
                ctypes.wintypes.HWND,
                ctypes.wintypes.LONG,
                ctypes.wintypes.LONG,
                ctypes.wintypes.UINT,
                ctypes.wintypes.UINT
            ),
            EVENT_OBJECT_REORDER,
            0x0001
        ]
    ]
        


    def listenerFunction(processHandler, onChange, WinEventProcType, EventObject , WinEvent = 0x0003):
        nonlocal listenerThreadIds
        kernel32 = ctypes.windll.kernel32
        threadId = kernel32.GetCurrentThreadId()
        listenerThreadIds.append(threadId)

        EVENT_SYSTEM_DIALOGSTART = 0x0010
        WINEVENT_OUTOFCONTEXT = WinEvent

        # https://stackoverflow.com/questions/15849564/how-to-use-winapi-setwineventhook-in-python
        # https://stackoverflow.com/questions/48767318/move-window-when-external-applications-window-moves
        # https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwineventhook

        user32 = ctypes.windll.user32
        def callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
            
            if hwnd != None:
                # print((hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime))
                onChange(hwnd)
                # getHwndRect(hwnd)

        WinEventProc = WinEventProcType(callback)

        user32.SetWinEventHook.restype = ctypes.wintypes.HANDLE
        hook = user32.SetWinEventHook(
            EventObject,  # from
            EventObject,  # to
            0,
            WinEventProc,
            processHandler,  # process handler
            0,  # thread id
            WINEVENT_OUTOFCONTEXT
        )
        if hook == 0:
            print('SetWinEventHook failed')
            sys.exit(1)

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            user32.TranslateMessageW(msg)
            user32.DispatchMessageW(msg)

        print('thread {} exiting'.format(threadId))
        user32.UnhookWinEvent(hook)
        print('thread {} exit'.format(threadId))

    for event in events:
        t = Thread(target=listenerFunction, args=(processHandler, event[0], event[1],event[2]))
        t.daemon = True
        t.start()


    return listenerThreadIds


def getWindowHwndByProcessHandler(processHandler):
    def getWindowHwndByProcessHandlerRaw(processHandler):
        win_hwnd = -1

        def callback(hwnd, procid):
            nonlocal win_hwnd
            if procid in win32process.GetWindowThreadProcessId(hwnd):
                if win_hwnd == -1:
                    win_hwnd = hwnd

                print('procid:' + str(procid))
                print('hwnd:' + str(hwnd))

        win32gui.EnumWindows(callback, processHandler)
        return win_hwnd

    while True:
        win_hwnd = getWindowHwndByProcessHandlerRaw(processHandler)
        if win_hwnd != -1:
            break
        sleep(0.1)

    return win_hwnd

def cancelListenerTheads(listenerThreadIds):
    def PostThreadMessage(listenerThreadId):
        # https://stackoverflow.com/questions/50603171/python-user32-getmessage-never-exits
        WM_QUIT = 0x0012
        user32 = ctypes.windll.user32
        print('stop thread:' + str(listenerThreadId))
        user32.PostThreadMessageW(listenerThreadId, WM_QUIT, 0, 0)

    for listenerThreadId in listenerThreadIds:
        PostThreadMessage(listenerThreadId)

def killProcess(processHandler):
    print('kill process:' + str(processHandler))
    ph =  OpenProcess(0x0001, False, processHandler); 
    process.TerminateProcess(ph,1)
    CloseHandle(ph)



if __name__ == "__main__":
    
    # load configs
    config = getConfig()
    print("config:{}".format(config))
    
    hook = hooks.get(config['hook'], None)
    
    # start main process
    print("main_path:{}".format(config["main_path"]))
    mainProcess = initProcess(config["main_path"] , config["main_args"])
    mainProcessHandler = mainProcess.pid
    print('mainProcessHandler:' + str(mainProcessHandler))
    mainHwmd = getWindowHwndByProcessHandler(mainProcessHandler)
    print('mainHwmd:' + str(mainHwmd))  
    

    # start dock exe process
    dockWidth = 0 # config["dock_width"]
    dockHeight = 0 # config["dock_height"]
    
    wait_time = config["wait_time"]
    # dock item window
    dockItemProcess = initProcess(config["dock_path"], config["dock_args"])
    dockItemProcessHandler = dockItemProcess.pid
    print('dockItemProcessHandler:' + str(dockItemProcessHandler))

    # wired in window handler to electron application
    sleep(wait_time)

    dockItemHwmd = getWindowHwndByProcessHandler(dockItemProcessHandler)
    print('dockItemHwmd:' + str(dockItemHwmd))

    mainWindowHandlerArgs = config["main_window_handler_args"]
    mainWindowHandlerProcess = initProcess(
        config["main_window_handler_path"] ,
        mainWindowHandlerArgs
            .replace('{main_hwmd}', str(mainHwmd))
            .replace('{dock_hwmd}', str(dockItemHwmd))
            .replace('{main_pid}' , str(mainProcessHandler))
            .replace('{dock_pid}', str(dockItemProcessHandler))
    )
    

    dock_location_x, dock_location_y = config["dock_location"].split(' ')
    

    # par need fit callback
    def onWindowChange(hwnd):
        

        
        x, y, xpw, yph = getHwndRect(dockItemHwmd)
        main_x, main_y, main_xpw, main_yph = getHwndRect(mainHwmd)
        
        if (hook != None):
            # print(hook)
            is_set , rect = hook['on_main_size_change'](main_x, main_y, main_xpw, main_yph)
            if is_set == True:
                print('hook set rect')
                
                moveHwnd(mainHwmd, -1, rect[0], rect[1], rect[2], rect[3], False)
                moveHwnd(mainHwmd, -2, rect[0], rect[1], rect[2], rect[3], False)
                return            
        
        
        
        print(f'window size change [{x} {y} {xpw} {yph}] [{main_x} {main_y} {main_xpw} {main_yph}]', end="\r")
        # some hack to make it work
        # keep the dock item with same z order as main window
        dock_left = main_xpw
        dock_top = main_y
        if(dock_location_x == 'left'):
            dock_width = xpw - x
            dock_left = main_x - dock_width
        if(dock_location_x == 'center'):
            dock_width = xpw - x
            dock_left = int(main_x + (main_xpw - main_x - dock_width) / 2)
        if(dock_location_x == 'right'):
            dock_left = main_xpw
        if(dock_location_x == 'i-left'):
            dock_left = main_x
        if(dock_location_x == 'i-right'):
            dock_width = xpw - x
            dock_left = main_xpw - dock_width
            
        if(dock_location_y == 'top'):
            dock_height = yph - y
            dock_top = main_y - dock_height
        if(dock_location_y == 'center'):
            dock_height = yph - y
            dock_top = int(main_y + (main_yph - main_y - dock_height) / 2)    
        if(dock_location_y == 'bottom'):
            dock_top = main_yph
        if(dock_location_y == 'i-top'):
            dock_top = main_y
        if(dock_location_y == 'i-bottom'):
            dock_height = yph - y
            dock_top = main_yph - dock_height
            
        moveHwnd(dockItemHwmd, -1, dock_left  + config["dock_offset_x"], dock_top + config["dock_offset_y"] , dockWidth , dockHeight , True)
        moveHwnd(dockItemHwmd, -2,  dock_left  + config["dock_offset_x"] , dock_top + config["dock_offset_y"] , dockWidth , dockHeight , True)
        
        

    def onOrderChange(hwnd):
        print('window order change')
        x, y, xpw, yph = getHwndRect(dockItemHwmd)
        # some hack to make it work
        # keep the dock item with same z order as main window
        moveHwnd(dockItemHwmd, -1, x , y , dockWidth , dockHeight , True)
        moveHwnd(dockItemHwmd, -2, x , y , dockWidth , dockHeight , True)


    listenerThreadIds = startListener(mainProcessHandler, onWindowChange, onOrderChange)

    print('listenerThreadIds:{}'.format(listenerThreadIds))


    try:
        

        onWindowChange(mainHwmd)

        mainProcess.wait()
        
        sleep(0.2)
        # dockItemProcess.kill()
        os.system('taskkill /F /T /PID ' + str(dockItemProcessHandler))
        
        sleep(0.2)
        # mainWindowHandlerProcess.kill()
        os.system('taskkill /F /T /PID ' + str(mainWindowHandlerProcess.pid))

        cancelListenerTheads(listenerThreadIds)
    
    except:
        print('kill process by exception')
        
        os.system('taskkill /F /T /PID ' + str(mainProcessHandler))
    
    finally:
    
        print('\nAll proc exited.\nGood bye.')