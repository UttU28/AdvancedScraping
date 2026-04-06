#!/usr/bin/env python3
import subprocess
import os
import sys
import time
import glob
import threading
import msvcrt
from datetime import datetime
from PIL import Image
from colorama import Fore, Style, init

init(autoreset=True)

# Configuration
CROP_LEFT = 250
CROP_TOP = 400
CROP_RIGHT_OFFSET = 0
CROP_BOTTOM_OFFSET = 50

SCROLL_START_X = 500
SCROLL_START_Y = 800
SCROLL_END_X = 500
SCROLL_END_Y = 200
SCROLL_DELAY = 0.3

stopFlag = False

def checkQuitKey():
    global stopFlag
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'q':
                stopFlag = True
                break

def takeScreenshot(saveDir='screenshots', crop=True, count=0):
    os.makedirs(saveDir, exist_ok=True)

    # Generate sequential filename
    fileName = 'screen000.png'
    croppedFileName = f'screen{count:03d}_cropped.png'
    devicePath = f'/sdcard/{fileName}'
    tempLocalPath = os.path.join(saveDir, f'temp_{fileName}')
    croppedPath = os.path.join(saveDir, croppedFileName)

    try:
        subprocess.run(['adb', 'shell', 'screencap', '-p', devicePath], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['adb', 'pull', devicePath, tempLocalPath], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['adb', 'shell', 'rm', devicePath], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        image = Image.open(tempLocalPath)

        if crop:
            width, height = image.size
            cropBox = (CROP_LEFT, CROP_TOP, width - CROP_RIGHT_OFFSET, height - CROP_BOTTOM_OFFSET)
            croppedImage = image.crop(cropBox)
            croppedImage.save(croppedPath)

        # Remove the temporary file
        os.remove(tempLocalPath)
        return True

    except (subprocess.CalledProcessError, Exception):
        return False

if __name__ == "__main__":
    count = 0
    print(Fore.YELLOW + Style.BRIGHT + "Press 'q' to stop capturing screenshots.")

    keyThread = threading.Thread(target=checkQuitKey, daemon=True)
    keyThread.start()

    while not stopFlag:
        success = takeScreenshot(count=count)
        if not success:
            print(Fore.RED + Style.BRIGHT + "\nAn error occurred while taking screenshot. Stopping...")
            break

        count += 1
        print(Fore.GREEN + f"\rScreenshots captured: {count}", end='')

        subprocess.run(['adb', 'shell', 'input', 'swipe', 
            str(SCROLL_START_X), str(SCROLL_START_Y), 
            str(SCROLL_END_X), str(SCROLL_END_Y)], 
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(SCROLL_DELAY)

    print(Fore.CYAN + Style.BRIGHT + f"\nCapture session ended. Total screenshots: {count}")
