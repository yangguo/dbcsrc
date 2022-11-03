import datetime
import os

pencsrc2 = "../data/penalty/csrc2"
tempdir = "../data/penalty/csrc2/temp"

# get current date and time string
def get_nowdate():
    now = datetime.datetime.now()
    now_str = now.strftime("%Y%m%d")
    return now_str


def savetemp(df, basename):
    savename = basename + ".csv"
    savepath = os.path.join(tempdir, savename)
    df.to_csv(savepath)


def savedf2(df, basename):
    savename = basename + ".csv"
    savepath = os.path.join(pencsrc2, savename)
    df.to_csv(savepath)
