import win32.win32process as win32process
import win32.win32process as process
import win32.win32gui as win32gui
import sys
import os
import ctypes
import ctypes.wintypes
from time import sleep
from threading import Thread
from win32.win32gui import GetWindowRect, GetWindowText
from win32.win32api import CloseHandle, OpenProcess



from config import getConfig

# from typing import Optional
# from win32 import win32api, win32event
# from command import getCommandFunction, getCommandIdList
# import subprocess


def isLiveProcess(processHandler):
    processList = process.EnumProcesses()
    for aProcess in processList:
        if (aProcess == processHandler):
            return True
    return False


def initProcess(exePath, args=None):

    PORTABLE_APPLICATION_LOCATION = exePath

    def runProgram():
        processHandler = -1
        try:
            startObj = process.STARTUPINFO()
            myProcessTuple = process.CreateProcess(
                PORTABLE_APPLICATION_LOCATION, args, None, None, 8, 8, None, None, startObj)
            processHandler = myProcessTuple[2]
        except:
            print(sys.exc_info[0])
        return processHandler

    processHandler = runProgram()

    return processHandler


def getHwndRect(hwnd):
    x, y, xpw, yph = GetWindowRect(hwnd)
    rx, ry, rxpw, ryph = x , y, xpw , yph
    return (rx, ry, rxpw, ryph)


def moveHwnd(hwnd, order, x, y, xpw, yph, b_repaint):
    win32gui.SetWindowPos(hwnd, order, x, y, xpw, yph, b_repaint)


def startListener(processHandler, onWindowChange, onWindowClose, onOrderChange):
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
        ],
        [
            onWindowClose,
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
            WM_CLOSE,
            0x0003
        ],
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

    # def listenerFunction2(processHandler):
    #     ph =  OpenProcess(0x00100000, False, processHandler); 
    #     print('start 123')
    #     while 1:
    #         msg = win32event.WaitForSingleObject(ph, win32event.INFINITE)
    #         print(msg)
        

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
    ph =  OpenProcess(0x0001, False, processHandler); 
    process.TerminateProcess(ph,1)
    CloseHandle(ph)


if __name__ == "__main__":
    config = getConfig()

    listenerThreadId = None

    print("config:{}".format(config))
    print("main_path:{}".format(config["main_path"]))

    mainProcessHandler = initProcess(config["main_path"] , config["main_args"])
    print('mainProcessHandler:' + str(mainProcessHandler))
    mainHwmd = getWindowHwndByProcessHandler(mainProcessHandler)
    print('mainHwmd:' + str(mainHwmd))  
    
    mainWindowHandlerArgs = config["main_window_handler_args"]
    
    


    dockWidth = 0 # config["dock_width"]
    dockHeight = 0 # config["dock_height"]
    
    wait_time = config["wait_time"]
    # dock item window
    dockItemProcessHandler = initProcess(config["dock_path"], config["dock_args"])
    print('dockItemProcessHandler:' + str(dockItemProcessHandler))

    # wired in window handler to electron application
    sleep(wait_time)

    dockItemHwmd = getWindowHwndByProcessHandler(dockItemProcessHandler)
    print('dockItemHwmd:' + str(dockItemHwmd))
    
    mainWindowHandler = initProcess(
        config["main_window_handler_path"] , 
        mainWindowHandlerArgs 
            .replace('{main_hwmd}', str(mainHwmd))
            .replace('{dock_hwmd}', str(dockItemHwmd))
        )
    print('mainWindowHandler:' + str(mainWindowHandler))


    dock_location_x, dock_location_y = config["dock_location"].split(' ')
    

    def onWindowChange(hwnd):
        print('window size change')
        x, y, xpw, yph = getHwndRect(dockItemHwmd)
        # some hack to make it work
        # keep the dock item with same z order as main window
        dock_left = xpw
        dock_top = yph
        if(dock_location_x == 'left'):
            main_x, main_y, main_xpw, main_yph = getHwndRect(mainHwmd)
            dock_width = xpw - x
            dock_left = main_x - dock_width
        if(dock_location_x == 'center'):
            main_x, main_y, main_xpw, main_yph = getHwndRect(mainHwmd)
            dock_width = xpw - x
            dock_left = int(main_x + (main_xpw - main_x - dock_width) / 2)
        if(dock_location_x == 'right'):
            dock_left = xpw
            
        if(dock_location_y == 'top'):
            main_x, main_y, main_xpw, main_yph = getHwndRect(mainHwmd)
            dock_height = yph - y
            dock_top = main_y - dock_height
        if(dock_location_y == 'center'):
            main_x, main_y, main_xpw, main_yph = getHwndRect(mainHwmd)
            dock_height = yph - y
            dock_top = int(main_y + (main_yph - main_y - dock_height) / 2)
            
        if(dock_location_y == 'bottom'):
            dock_top = yph
        
        
        moveHwnd(dockItemHwmd, -1, dock_left  + config["dock_offset_x"], dock_top + config["dock_offset_y"] , dockWidth , dockHeight , True)
        moveHwnd(dockItemHwmd, -2,  dock_left  + config["dock_offset_x"] , dock_top + config["dock_offset_y"] , dockWidth , dockHeight , True)
        
        

    def onOrderChange(hwnd):
        print('window order change')
        x, y, xpw, yph = getHwndRect(dockItemHwmd)
        # some hack to make it work
        # keep the dock item with same z order as main window
        moveHwnd(dockItemHwmd, -1, x , y , dockWidth , dockHeight , True)
        moveHwnd(dockItemHwmd, -2, x , y , dockWidth , dockHeight , True)

    def onWindowClose(hwnd):
        print('window close')
        if isLiveProcess(dockItemProcessHandler):
            killProcess(dockItemProcessHandler)
        

    onWindowChange(mainHwmd)

    listenerThreadIds = startListener(mainProcessHandler, onWindowChange, onWindowClose, onOrderChange)

    print('listenerThreadIds:{}'.format(listenerThreadIds))


    while isLiveProcess(mainProcessHandler):
        try:
            sleep(0.5)
        except:
            break

    cancelListenerTheads(listenerThreadIds)

    sleep(0.2)
    # it likely auto close after process exit
    if isLiveProcess(dockItemProcessHandler):
        killProcess(dockItemProcessHandler)

    # it likely auto close after process exit
    sleep(0.2)
    if isLiveProcess(mainProcessHandler):
        killProcess(mainProcessHandler)
        
    sleep(0.2)
    if isLiveProcess(mainWindowHandler):
        killProcess(mainWindowHandler)


    sleep(1)
    print('\nAll proc exited.\nGood bye.')
