import os.path
import time
import sys
import configparser

import numpy as np
import cv2

import curses

path = ""
filename = ""

levelPal = ' .,:;<iIEX%@'


def main(sc):
    x, y = sc.getmaxyx() if sc else (50, 50)
    size = (min(x, y) - 1, min(x, y) - 1)

    vid = cv2.VideoCapture(path)
    fps = round(vid.get(cv2.CAP_PROP_FPS))

    npShape = (size[0], size[1], 1)

    tm = time.perf_counter()
    while True:
        ret, frame = vid.read()
        if ret:
            img = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), size, interpolation=cv2.INTER_AREA).astype(int)

            for y, x, _ in np.ndindex(npShape):
                sc.addstr(y, x * 2, levelPal[int(img[y, x] * len(levelPal) // 256)])

            sc.refresh()

            tm = time.perf_counter() - tm
            if tm < (1 / fps):
                time.sleep((1 / fps) - tm)
            tm = time.perf_counter()
        else:
            break
    return


def configure():
    global levelPal
    config = configparser.ConfigParser()
    config.read('config.cfg')
    try:
        levelPal = " " + config["VIDEO"]["characterPalette"]
        levelPal = [ch * 2 for ch in levelPal]
    except KeyError:
        config = configparser.ConfigParser()
        config["VIDEO"] = {"characterPalette": levelPal.replace("%", "%%")}
        levelPal = [ch * 2 for ch in levelPal]
        with open("config.cfg", "w") as cfgFile:
            config.write(cfgFile)


if __name__ == "__main__":

    input("Resize the window to your liking, then press enter")
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)
    elif __file__:
        application_path = os.path.dirname(__file__)
        os.chdir(application_path)

    configure()

    if len(sys.argv) < 2:
        print("No file path provided. Make sure to drag a video to the .exe when executing")
        input("press enter to exit...")
        sys.exit(1)

    path = sys.argv[1]
    filename = path.split("/")[-1].split("\\")[-1]
    if filename.split(".")[-1] != "mp4":
        print("The file is not an mp4!!")
        input("press enter to exit...")
        sys.exit(1)

    try:
        curses.wrapper(main)
    except curses.error:
        print("Error, the console is too small, please expand the window!!")
    except Exception:
        print("Error, the file could not be read")
    input("press enter to exit...")
