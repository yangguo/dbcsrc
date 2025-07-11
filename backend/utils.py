import datetime
import os
import glob
import datetime

# Lazy import pandas to reduce memory usage during startup
pd = None

def get_pandas():
    """Lazy import pandas to reduce startup memory usage"""
    global pd
    if pd is None:
        try:
            import pandas as pandas_module
            pd = pandas_module
        except ImportError as e:
            print(f"Failed to import pandas: {e}")
            raise
    return pd

pencsrc2 = "../data/penalty/csrc2"
tempdir = "../data/penalty/csrc2/temp"
rulefolder = "../data/rules"


# get current date and time string
def get_nowdate():
    now = datetime.datetime.now()
    now_str = now.strftime("%Y%m%d")
    return now_str


def savetemp(df, basename):
    savename = basename + ".csv"
    savepath = os.path.join(tempdir, savename)
    df.to_csv(savepath, encoding='utf-8-sig')


def savedf2(df, basename):
    savename = basename + ".csv"
    savepath = os.path.join(pencsrc2, savename)
    df.to_csv(savepath, encoding='utf-8-sig')


def get_csvdf(rulefolder):
    files2 = glob.glob(rulefolder + "*.csv", recursive=False)
    dflist = []
    for filepath in files2:
        basename = os.path.basename(filepath)
        filename = os.path.splitext(basename)[0]
        newdf = rule2df(filename, filepath)[["监管要求", "结构", "条款"]]
        dflist.append(newdf)
    alldf = get_pandas().concat(dflist, axis=0)
    return alldf


def rule2df(filename, filepath):
    docdf = get_pandas().read_csv(filepath, encoding='utf-8-sig')
    docdf["监管要求"] = filename
    return docdf


def get_rulefolder(industry_choice):
    # join folder with industry_choice
    folder = os.path.join(rulefolder, industry_choice)
    return folder


# split string by space into words, add brackets before and after words, combine into text
def split_words(text):
    words = text.split()
    words = ["(?=.*" + word + ")" for word in words]
    new = "".join(words)
    return new


# simplified df2aggrid function for backend compatibility
def df2aggrid(df):
    # Return dataframe as-is since backend doesn't use streamlit AgGrid
    return df


# simplified df2echartstable function for backend compatibility  
def df2echartstable(df, title):
    # Return dataframe as-is since backend doesn't use echarts
    return df
