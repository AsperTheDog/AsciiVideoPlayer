import math
import os.path
import time
import sys
import configparser

from Lib import queue
import threading

import numpy as np
import cv2

import curses

path = ""
filename = ""

levelPal = ' .,:;<iIEX%@'
showBar = True

buffer = queue.Queue()
finished = False
fps = 30
b = threading.Barrier(2)
size = (50, 50)
res = (0, 0)
padding = (0, 0)

totalFrames = 0
rasterFrames = 0
videoFrames = 0

def feeder(vid):
    global buffer, finished, size, b, rasterFrames

    b.wait()

    trueWidth = size[0] * 2 + 1 + padding[0]
    frameData = [' '] * (trueWidth * (size[1] + padding[1]))

    for y in range(1, size[1]):
        frameData[(y * trueWidth) - 1] = "\n"

    while True:
        ret, frame = vid.read()
        if ret:
            img = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), size, interpolation=cv2.INTER_AREA).astype(int)

            for y, x in np.ndindex(img.shape):
                pos = y * trueWidth + (x * 2) + padding[0]
                newChar = levelPal[int(img[y, x] * len(levelPal) >> 8)]
                if newChar != frameData[pos]:
                    frameData[pos] = frameData[pos + 1] = newChar

            lastFrame = "\n" * padding[1] + "".join(frameData)
            buffer.put(lastFrame)
            rasterFrames += 1
        else:
            return


def renderer(sc):
    global buffer, fps, size, b, res, videoFrames, rasterFrames, totalFrames, showBar, padding

    curses.curs_set(0)

    ar = res[1] / res[0]
    y, x = sc.getmaxyx() if sc else (50, 50)

    y -= 1
    if showBar:
        y -= 2

    xr, yr = math.floor(y / ar), math.floor(x * ar)
    size = (min(xr, x), min(yr, y))

    padding = (math.floor((x - (size[0] * 2)) // 2), math.floor((y - size[1]) // 2))

    b.wait()

    frRatio = (x - 2) / totalFrames
    frameTime = (1 / fps)
    totalTime = 0
    tm = time.perf_counter()
    while True:
        if finished:
            if buffer.empty():
                return
            nextFrame = buffer.get(block=False)
        else:
            nextFrame = buffer.get()
        sc.addstr(0, 0, nextFrame)

        if showBar:
            adjVideo = math.ceil(videoFrames * frRatio)
            adjRaster = min(math.ceil(buffer.qsize() * frRatio), x - 2 - adjVideo)
            sc.addstr(y + 1, 0, "|" + ("-" * (x - 2)) + "|")
            sc.addstr(y + 1, 1, ("#" * adjVideo) + ("=" * adjRaster))

        sc.refresh()

        totalTime += time.perf_counter() - tm
        tm = time.perf_counter()
        target = frameTime * videoFrames
        if totalTime < target:
            time.sleep(target - totalTime)
        videoFrames += 1


def multiMain():
    global fps, res, totalFrames

    vid = cv2.VideoCapture(path)
    fps = round(vid.get(cv2.CAP_PROP_FPS))
    totalFrames = round(vid.get(cv2.CAP_PROP_FRAME_COUNT))

    width = vid.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

    res = (width, height)

    feed = threading.Thread(target=feeder, args=[vid])
    feed.start()
    curses.wrapper(renderer)


def configure():
    global levelPal, buffer, showBar
    config = configparser.ConfigParser()
    config.read('config.cfg')
    try:
        levelPal = " " + config["VIDEO"]["characterPalette"]
        try:
            if "maxBufferSize" in config["VIDEO"] and int(config["VIDEO"]["maxBufferSize"]) > 0:
                buffer = queue.Queue(int(config["VIDEO"]["maxBufferSize"]))
        except ValueError:
            pass
        showBar = config["VIDEO"]["showProgressBar"] == "True"
    except KeyError:
        config = configparser.ConfigParser()
        config["VIDEO"] = {
            "characterPalette": levelPal.replace("%", "%%"),
            "maxBufferSize": 0,
            "showProgressBar": True
        }
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
        multiMain()
    except curses.error:
        print("An error displaying the screen occured, please restart the program")
    except Exception:
        print("Error, the file could not be read")
    input("press enter to exit...")
