import glob
import os

import pandas as pd
import streamlit.components.v1 as components
from pyecharts import options as opts
from pyecharts.components import Table
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode

rulefolder = "../data/rules"


# @st.cache
def get_csvdf(rulefolder):
    files2 = glob.glob(rulefolder + "*.csv", recursive=False)
    dflist = []
    for filepath in files2:
        basename = os.path.basename(filepath)
        filename = os.path.splitext(basename)[0]
        newdf = rule2df(filename, filepath)[["监管要求", "结构", "条款"]]
        dflist.append(newdf)
    alldf = pd.concat(dflist, axis=0)
    return alldf


def rule2df(filename, filepath):
    docdf = pd.read_csv(filepath)
    docdf["监管要求"] = filename
    return docdf


def get_rulefolder(industry_choice):
    # join folder with industry_choice
    folder = os.path.join(rulefolder, industry_choice)
    return folder


def df2aggrid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination()
    # gb.configure_side_bar()
    # gb.configure_auto_height()
    gb.configure_default_column(
        # genablePivot=True,
        # enableValue=True,
        # enableRowGroup=True,
        groupable=True,
        editable=True,
    )
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    # configure column visibility
    gb.configure_column(field="lawid", hide=True)
    gb.configure_column(field="id", hide=True)
    gridOptions = gb.build()
    ag_grid = AgGrid(
        df,
        theme="material",
        #  height=800,
        fit_columns_on_grid_load=True,  # fit columns to grid width
        gridOptions=gridOptions,  # grid options
        #  key='select_grid', # key is used to identify the grid
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        # data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        #  update_mode=GridUpdateMode.NO_UPDATE,
        # enable_enterprise_modules=True
    )
    return ag_grid


# split string by space into words, add brackets before and after words, combine into text
def split_words(text):
    words = text.split()
    words = ["(?=.*" + word + ")" for word in words]
    new = "".join(words)
    return new


# display dataframe in echarts table
def df2echartstable(df, title):
    """
    Display dataframe in echarts table with title

    Parameters:
    df (pandas.DataFrame): dataframe to display
    title (str): title of the table

    Example:
    df2echartstable(df, "Table Title")
    """

    table = Table()
    headers = df.columns.tolist()
    rows = df.values.tolist()
    table.add(headers, rows)
    table.set_global_opts(title_opts=opts.ComponentTitleOpts(title=title, subtitle=""))
    # st_pyecharts(table)
    components.html(table.render_embed(), width=800)
