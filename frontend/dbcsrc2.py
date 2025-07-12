import glob
import json
import os
import random
import re
import time

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from bs4 import BeautifulSoup
from database import get_collection, get_data, insert_data
from dbcsrc import get_csvdf, get_now, get_nowdate
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from snapshot import get_chrome_driver
from collections import Counter

# from streamlit_tags import st_tags
from utils import split_words

# from doc2text import convert_uploadfiles
# from pyecharts import options as opts
# from pyecharts.charts import Map, Pie
# from streamlit_echarts import Map as st_Map
# from streamlit_echarts import st_pyecharts


# Use absolute paths to ensure data loading works from any working directory
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
pencsrc2 = os.path.join(project_root, "data", "penalty", "csrc2")
tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
mappath = os.path.join(project_root, "data", "map", "chinageo.json")
# backendurl = "http://backend.docker:8000"
backendurl = "http://localhost:8000"

# orgid map to orgname
org2id = {
    "山西": "94bf3c5d8e5b4265a7916f19fb8b65ef",
    "四川": "88a03b16f60e4d16a62bd494d6530495",
    "新疆": "baa8f6e40657486bb0d7cc8525c857e6",
    "山东": "4bd2094f91c14fcc84ffc4df0cd29d2b",
    "大连": "d5247fa1384f4a46b17f2d33f025bdca",
    "湖北": "a4478a6efb074823959f782bf7ad23c2",
    "湖南": "53d1eac8c4c145db8ca62c99bda5c058",
    "陕西": "00d7790e259b4d3dbaefe2935b1ec05f",
    "天津": "882ff9eb82b346999ab45e9a597bc461",
    "宁夏": "9e622bf25828428996182a74dea32057",
    "安徽": "1d14687d160f4fe09642c86fc33501bd",
    "总部": "29ae08ca97d44d6ea365874aa02d44f6",
    "北京": "313639c4d05a43e5b86b1f356066f22d",
    "江苏": "47d5896f8fc1486c89208dbdf00e937b",
    "黑龙江": "19044145cb714a7cbd9cad1b2a810809",
    "甘肃": "7a78277d94df4057a9ad6cb9db7fca2a",
    "宁波": "da83ebb77019448c912dbcdec571d3d7",
    "深圳": "51840ec0710b4221b27cf3f7d52c0781",
    "河北": "9b55d0917b8c45239e04815ad7d684dd",
    "广东": "a281797dea33433e93c30bcc4fa2e907",
    "厦门": "b5eabe7e6d0847ebae3ea9b1abd2a230",
    "福建": "ca335b3bbc51408da8a64f89bce67c95",
    "西藏": "da2deae04a2a412e896d05d31b603804",
    "青岛": "47f0814210b64db681be188da7f21b22",
    "贵州": "1d15ee7b6389461eb45b7de8fc742615",
    "河南": "fa3997ef7b7549049b59451451e03623",
    "广西": "cad5c39b4cae415fb576ceffc5d197ec",
    "内蒙古": "afc4ff6ea7644244ba66b79b296aaa36",
    "海南": "aa24b402e1df434bbb68baa256fef9d4",
    "浙江": "ac4e1875e53f4cb185195265376c8550",
    "云南": "0ce80bd1aaae430c8511b1a282e582f8",
    "辽宁": "25ae72513b9a4e96a18823d4b1844f22",
    "吉林": "ee414472c92443479e16c250e69840e1",
    "江西": "d7cae17b8d824e768ec1f7e86fd7f36a",
    "重庆": "c28e1398b3054af694b769291a1c8952",
    "上海": "0dd09598f7f2470fb269732ec5b8ddc8",
    "青海": "1747a405d9a6437e8688f25c48c6205a",
}

# cityls = [
#     "北京市",
#     "天津市",
#     "河北省",
#     "山西省",
#     "内蒙古自治区",
#     "辽宁省",
#     "吉林省",
#     "黑龙江省",
#     "上海市",
#     "江苏省",
#     "浙江省",
#     "安徽省",
#     "福建省",
#     "江西省",
#     "山东省",
#     "河南省",
#     "湖北省",
#     "湖南省",
#     "广东省",
#     "广西壮族自治区",
#     "海南省",
#     "重庆市",
#     "四川省",
#     "贵州省",
#     "云南省",
#     "西藏自治区",
#     "陕西省",
#     "甘肃省",
#     "青海省",
#     "宁夏回族自治区",
#     "新疆维吾尔自治区",
#     "台湾省",
#     "香港特别行政区",
#     "澳门特别行政区",
# ]

city2province = {
    "山西": "山西省",
    "四川": "四川省",
    "新疆": "新疆维吾尔自治区",
    "山东": "山东省",
    "大连": "辽宁省",
    "湖北": "湖北省",
    "湖南": "湖南省",
    "陕西": "陕西省",
    "天津": "天津市",
    "宁夏": "宁夏回族自治区",
    "安徽": "安徽省",
    "总部": "北京市",
    "北京": "北京市",
    "江苏": "江苏省",
    "黑龙江": "黑龙江省",
    "甘肃": "甘肃省",
    "宁波": "浙江省",
    "深圳": "广东省",
    "河北": "河北省",
    "广东": "广东省",
    "厦门": "福建省",
    "福建": "福建省",
    "西藏": "西藏自治区",
    "青岛": "山东省",
    "贵州": "贵州省",
    "河南": "河南省",
    "广西": "广西壮族自治区",
    "内蒙古": "内蒙古自治区",
    "海南": "海南省",
    "浙江": "浙江省",
    "云南": "云南省",
    "辽宁": "辽宁省",
    "吉林": "吉林省",
    "江西": "江西省",
    "重庆": "重庆市",
    "上海": "上海市",
    "青海": "青海省",
}


# @st.cache(allow_output_mutation=True)
def get_csrc2detail():
    pendf = get_csvdf(pencsrc2, "csrcdtlall")
    if not pendf.empty:
        # Format date - handle both timestamp and date formats
        if "发文日期" in pendf.columns:
            # First try to convert timestamps (numeric values) to datetime
            def convert_date(date_val):
                if pd.isna(date_val) or date_val == "":
                    return ""
                
                # If it's a numeric timestamp, convert it
                try:
                    # Check if it's a numeric timestamp (seconds or milliseconds)
                    if str(date_val).replace('.', '').isdigit():
                        timestamp = float(date_val)
                        # If timestamp is in milliseconds (> 1e10), convert to seconds
                        if timestamp > 1e10:
                            timestamp = timestamp / 1000
                        return pd.to_datetime(timestamp, unit='s').date()
                    else:
                        # Try to parse as regular date string
                        return pd.to_datetime(date_val, errors='coerce').date()
                except (ValueError, TypeError, OverflowError):
                    # If conversion fails, return empty string
                    return ""
            
            pendf["发文日期"] = pendf["发文日期"].apply(convert_date)
        # fillna
        pendf = pendf.fillna("")
    return pendf


def get_lawdetail2():
    lawdf = get_csvdf(pencsrc2, "csrc2lawdf")
    # format date
    # lawdf["发文日期"] = pd.to_datetime(lawdf["发文日期"]).dt.date
    # format lawls
    # lawdf["处理依据"] = lawdf["处理依据"].apply(literal_eval)
    # fillna
    lawdf = lawdf.fillna("")
    return lawdf


def get_csrc2label():
    labeldf = get_csvdf(pencsrc2, "csrc2label")
    # literal_eval apply to labels and scores
    # labeldf["labels"] = labeldf["labels"].apply(literal_eval)
    # labeldf["scores"] = labeldf["scores"].apply(literal_eval)
    # set label column from first item of labels
    # labeldf["label"] = labeldf["labels"].apply(lambda x: x[0])
    # fillna
    labeldf = labeldf.fillna("")
    return labeldf


def get_csrclenanalysis():
    pendf = get_csvdf(tempdir, "csrclenanalysis")
    if not pendf.empty:
        # fillna
        pendf = pendf.fillna("")  # [["名称", "链接", "内容", "len", "filename"]]
    return pendf


def get_csrcdownload():
    pendf = get_csvdf(tempdir, "csrcmiscontent")
    if not pendf.empty:
        # fillna
        pendf = pendf.fillna("")[["url", "filename", "text"]]
    return pendf


def get_csrc2textupdate():
    pendf = get_csvdf(tempdir, "csrc2textupdate")
    if not pendf.empty:
        # fillna
        pendf = pendf.fillna("")[["url", "filename", "text"]]
    return pendf


def get_csrc2analysis():
    pendf = get_csvdf(pencsrc2, "csrc2analysis")
    # collection = get_collection('pencsrc2', 'csrc2analysis')
    # pendf= get_data(collection)
    if not pendf.empty:
        # format date with error handling
        if "发文日期" in pendf.columns:
            pendf["发文日期"] = pd.to_datetime(pendf["发文日期"], errors='coerce').dt.date
        # fillna
        pendf = pendf.fillna("")
    return pendf


def lawls2dict(ls):
    try:
        result = []
        for item in ls:
            lawdict = dict()
            lawls = re.findall(r"《(.*?)》", item)
            #         print(lawls)
            artls = re.findall(r"(第[^《》、和章节款（）\(\)]*?条)", item)
            #         print(artls)
            lawdict["法律法规"] = lawls[0]
            lawdict["条文"] = artls
            result.append(lawdict)
        return result
    except Exception as e:
        st.error(str(e))
        return np.nan


def fix_abb(x, abbdict):
    result = []
    for regdict in x:
        newdict = dict()
        old = regdict["法律法规"]
        #         print(abbdict)
        if old in abbdict.keys():
            new = abbdict[old]
        else:
            new = old
        #         print(old)
        #         print(new)
        newdict["法律法规"] = new
        newdict["条文"] = regdict["条文"]
        result.append(newdict)
    return result


# convert eventdf to lawdf
def generate_lawdf2(d1):
    d1["doc1"] = d1["内容"].str.replace(r"\r|\n|\t|\xa0|\u3000|\s|\xa0", "", regex=True)
    compat = "(?!《).(《[^,，；。]*?》[^；。]*?第[^,，；。《]*条)"
    compat2 = "(?!《).(《[^,，；。]*?》)"
    compat3 = "《([^,，；。]*?)》[^；。]*?简称.*?《([^,，；。]*?)》"

    # generate abbrevation dict
    g1 = d1["doc1"].str.extractall(compat3).reset_index(level=1)
    g1.columns = ["match", "f1", "f2"]
    abb = (
        g1.groupby(g1.index)
        .apply(lambda x: dict(zip(x["f2"], x["f1"])))
        .reset_index(name="abbdict")
    )
    abb.index = abb["index"]

    d1["lawls"] = d1["doc1"].str.extractall(compat).groupby(level=0)[0].apply(list)
    d1["lawls"].fillna(
        d1["doc1"].str.extractall(compat2).groupby(level=0)[0].apply(list), inplace=True
    )
    d1["处理依据"] = d1["lawls"].fillna("").apply(lawls2dict)

    d11 = pd.merge(d1, abb, left_index=True, right_index=True, how="left")
    d22 = d11[d11["lawls"].notnull()][["链接", "处理依据", "abbdict"]]
    d22.loc[d22["abbdict"].notnull(), "fix"] = d22[d22["abbdict"].notnull()].apply(
        lambda row: fix_abb(row["处理依据"], row["abbdict"]), axis=1
    )
    d22.loc[d22["abbdict"].notnull(), "处理依据"] = d22.loc[
        d22["abbdict"].notnull(), "fix"
    ]

    d2 = d22[["链接", "处理依据"]]
    d3 = d2.explode("处理依据")
    d4 = d3["处理依据"].apply(pd.Series)
    d5 = pd.concat([d3, d4], axis=1)
    d6 = d5.explode("条文")
    # reset index
    d6.reset_index(drop=True, inplace=True)
    savedf2(d6, "csrc2lawdf")
    return d6


# summary of csrc2
def display_summary2():
    # get old sumeventdf
    oldsum2 = get_csrc2detail()
    # get length of old eventdf
    oldlen2 = len(oldsum2)
    
    # Check if date column exists before processing
    if "发文日期" in oldsum2.columns and not oldsum2.empty:
        # get min and max date of old eventdf
        min_date2 = oldsum2["发文日期"].min()
        max_date2 = oldsum2["发文日期"].max()
        date_range = f"{min_date2} - {max_date2}"
        
        # sum max,min date and size by org
        if "机构" in oldsum2.columns:
            sumdf2 = (
                oldsum2.groupby("机构")["发文日期"].agg(["max", "min", "count"]).reset_index()
            )
            sumdf2.columns = ["机构", "最近发文日期", "最早发文日期", "案例总数"]
            # sort by date
            sumdf2.sort_values(by=["最近发文日期"], ascending=False, inplace=True)
            # reset index
            sumdf2.reset_index(drop=True, inplace=True)
        else:
            sumdf2 = pd.DataFrame()
    else:
        date_range = "无日期数据"
        sumdf2 = pd.DataFrame()
    
    # use metric
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("案例总数", oldlen2)
    with col2:
        st.metric("案例日期范围", date_range)

    # display
    if not sumdf2.empty:
        st.markdown("#### 按机构统计")
        st.table(sumdf2)
    else:
        st.warning("无法生成机构统计数据")

    return sumdf2


# search by filename, date, wenhao,case,org,law,label
def searchcsrc2(
    df,
    # filename,
    start_date,
    end_date,
    wenhao,
    people,
    case,
    org,
    min_penalty,
    law_select,
):
    # col = ["名称", "发文日期", "文号", "内容", "链接", "机构", "amount", "label"]
    # convert date to datetime
    # df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    # split words
    # if filename != "":
    #     filename = split_words(filename)
    if wenhao != "":
        wenhao = split_words(wenhao)
    if case != "":
        case = split_words(case)

    # Start with all rows as True
    mask = pd.Series([True] * len(df), index=df.index)
    
    # Date filter - only apply if date column exists
    if "发文日期" in df.columns:
        mask = mask & (df["发文日期"] >= start_date) & (df["发文日期"] <= end_date)
    
    # Other filters - check column existence
    if "wenhao" in df.columns:
        mask = mask & df["wenhao"].str.contains(wenhao)
    if "event" in df.columns:
        mask = mask & df["event"].str.contains(case)
    if "机构" in df.columns:
        mask = mask & df["机构"].isin(org)
    if "amount" in df.columns:
        mask = mask & (df["amount"] >= min_penalty)
    if "law" in df.columns:
        mask = mask & df["law"].str.contains(law_select)
    if "people" in df.columns:
        mask = mask & df["people"].str.contains(people)
    
    # Apply the mask
    searchdf = df[mask]

    # sort by date desc if date column exists
    if "发文日期" in searchdf.columns:
        sorteddf = searchdf.sort_values(by=["发文日期"], ascending=False)
    else:
        sorteddf = searchdf.copy()
    # drop duplicates
    unidf = sorteddf.drop_duplicates(subset=["链接"])
    # reset index
    resultdf = unidf.reset_index(drop=True)
    return resultdf


# display event detail
def display_eventdetail2(search_df):
    # count by month
    # df_month = count_by_month(search_df)
    # st.write(search_df)
    # get filename from path

    # draw plotly figure
    display_search_df(search_df)
    # get search result from session
    search_dfnew = st.session_state["search_result_csrc2"]
    total = len(search_dfnew)
    # st.sidebar.metric("总数:", total)
    # display search result
    st.markdown("### 搜索结果" + "(" + str(total) + "条)")
    # add download button to left
    st.download_button(
        "下载搜索结果",
        data=search_dfnew.to_csv().encode("utf_8_sig"),
        file_name="搜索结果.csv",
    )
    # display columns - check if columns exist
    discols = ["发文日期", "名称", "机构", "category", "链接"]
    available_discols = [col for col in discols if col in search_dfnew.columns]
    
    if not available_discols:
        st.error("没有找到可显示的列")
        return
    
    # get display df
    display_df = search_dfnew[available_discols]
    # update columns name - map original to new names
    column_mapping = {
        "发文日期": "发文日期",
        "名称": "发文名称", 
        "机构": "发文机构",
        "category": "案例类型",
        "链接": "链接"
    }
    new_column_names = [column_mapping.get(col, col) for col in available_discols]
    display_df.columns = new_column_names

    # reset index
    display_df.reset_index(drop=True, inplace=True)

    data = st.dataframe(display_df, on_select="rerun", selection_mode="single-row")

    selected_rows = data["selection"]["rows"]

    # st.table(search_df)
    # data = df2aggrid(display_df)
    # display download button
    # st.sidebar.download_button(
    #     "下载搜索结果", data=search_dfnew.to_csv().encode("utf-8"), file_name="搜索结果.csv"
    # )
    # display data
    # selected_rows = data["selected_rows"]
    if selected_rows == []:
        st.error("请先选择查看案例")
        st.stop()
    # # convert selected_rows to dataframe
    # selected_rows_df = pd.DataFrame(selected_rows)

    # get url from selected_rows
    # url = selected_rows[0]["链接"]
    url = display_df.loc[selected_rows[0], "链接"]

    selected_rows_df = search_dfnew[search_dfnew["链接"] == url]
    # display event detail
    st.markdown("##### 案情经过")
    # update columns name
    # selected_rows_df.columns = ["发文名称", "发文日期", "文号", "内容", "链接", "发文机构"]
    # select display columns - check if columns exist
    detail_cols = [
        "发文日期",
        "summary",
        "wenhao",
        "people",
        "event",
        "law",
        "penalty",
        "机构",
        "date",
        "category",
        "amount",
        "province",
        "industry",
        "内容",
    ]
    available_detail_cols = [col for col in detail_cols if col in selected_rows_df.columns]
    
    if not available_detail_cols:
        st.error("没有找到可显示的详细信息列")
        return
    
    selected_rows_df = selected_rows_df[available_detail_cols]
    # rename columns - map original to new names
    detail_column_mapping = {
        "发文日期": "发布日期",
        "summary": "摘要",
        "wenhao": "文号",
        "people": "当事人",
        "event": "违法事实",
        "law": "处罚依据",
        "penalty": "处罚决定",
        "机构": "处罚机关",
        "date": "处罚日期",
        "category": "案件类型",
        "amount": "罚款金额",
        "province": "处罚地区",
        "industry": "行业类型",
        "内容": "内容",
    }
    new_detail_column_names = [detail_column_mapping.get(col, col) for col in available_detail_cols]
    selected_rows_df.columns = new_detail_column_names
    # transpose dataframe
    selected_rows_df = selected_rows_df.T
    # set column name
    selected_rows_df.columns = ["案情内容"]
    # display
    st.table(selected_rows_df.astype(str))

    st.markdown("##### 案例链接")
    st.markdown(url)
    # # get amtdf
    # amtdf = get_csrc2amt()
    # # search amt by url
    # amtdata = amtdf[amtdf["url"] == url]
    # # display amount if amtdata is not empty
    # if amtdata.empty:
    #     st.error("没有找到相关罚款金额信息")
    # else:
    #     # display penalty amount
    #     amount = amtdata["amount"].values[0]
    #     st.metric("罚款金额", amount)

    # # get labeldf
    # labeldf = get_csrc2label()
    # # search labels by url
    # labeldata = labeldf[labeldf["id"] == url]
    # # display labels if labeldata is not empty
    # if labeldata.empty:
    #     st.error("没有找到相关标签")
    # else:
    #     # display labels
    #     labels = labeldata["labels"].values[0]
    #     scorels = labeldata["scores"].values[0]
    #     # convert scores to string
    #     scorels2 = ["%.3f" % x for x in scorels]
    #     scorestr = "/".join(scorels2)
    #     # st.markdown(scorestr)
    #     keywords = st_tags(
    #         label="##### 案件类型", text=scorestr, value=labels, suggestions=labels
    #     )

    # get lawdetail
    # lawdf = get_lawdetail2()
    # # search lawdetail by selected_rows_id
    # selected_rows_lawdetail = lawdf[lawdf["链接"] == url]

    # if len(selected_rows_lawdetail) > 0:
    #     # display lawdetail
    #     st.markdown("##### 处罚依据")
    #     lawdata = selected_rows_lawdetail[["法律法规", "条文"]]
    #     # display lawdata
    #     lawdtl = df2aggrid(lawdata)
    #     selected_law = lawdtl["selected_rows"]
    #     if selected_law == []:
    #         st.error("请先选择查看监管条文")
    #     else:
    #         # get selected_law's rule name
    #         selected_law_name = selected_law[0]["法律法规"]
    #         # get selected_law's rule article
    #         selected_law_article = selected_law[0]["条文"]
    #         # get law detail by name
    #         ruledf = get_rulelist_byname(selected_law_name, "", "", "", "")
    #         # get law ids
    #         ids = ruledf["lawid"].tolist()
    #         # get law detail by id
    #         metadf, dtldf = get_lawdtlbyid(ids)
    #         # display law meta
    #         st.write("监管法规")
    #         st.table(metadf)
    #         # get law detail by article
    #         articledf = dtldf[dtldf["标题"].str.contains(selected_law_article)]
    #         # display law detail
    #         st.write("监管条文")
    #         st.table(articledf)
    # else:
    #     st.write("没有相关监管法规")


# get sumeventdf in page number range
def get_sumeventdf2(orgname, start, end):
    resultls = []
    errorls = []
    count = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for pageno in range(start, end + 1):
        st.info("page:" + str(pageno))
        url = get_url2(orgname) + str(pageno)
        try:
            dd = requests.get(url, headers=headers, verify=False)
            dd.raise_for_status()  # Raise an error for bad status codes
            sd = BeautifulSoup(dd.content, "html.parser")
            # Strip any extra data outside JSON content
            json_text = str(sd.text).strip()
            json_data = json.loads(json_text, strict=False)
            # json_data = json.loads(str(sd.text), strict=False)
            itemls = json_data["data"]["results"]

            # st.write("itemls:", itemls)
            titlels = []
            wenhaols = []
            datels = []
            snls = []
            urlls = []
            docls = []

            for idx, item in enumerate(itemls):
                headerls = item["domainMetaList"][0]["resultList"]
                headerdf = pd.DataFrame(headerls)
                wenhao = headerdf[headerdf["key"] == "wh"]["value"].item()
                # date = headerdf[headerdf["key"] == "fwrq"]["value"].item()
                sn = headerdf[headerdf["key"] == "syh"]["value"].item()
                title = item["subTitle"]
                url = item["url"]
                # update date extracting
                date = item["publishedTimeStr"]
                try:
                    doc = (
                        item["contentHtml"]
                        .replace("\r", "")
                        .replace("\n", "")
                        .replace("\u2002", "")
                        .replace("\u3000", "")
                    )
                except Exception as e:
                    st.error("error item!: " + str(e))
                    st.error("idx: " + str(idx))
                    doc = (
                        item["content"]
                        .replace("\r", "")
                        .replace("\n", "")
                        .replace("\u2002", "")
                        .replace("\u3000", "")
                    )

                titlels.append(title)
                wenhaols.append(wenhao)
                datels.append(date)
                snls.append(sn)
                urlls.append(url)
                docls.append(doc)
            csrceventdf = pd.DataFrame(
                {
                    "名称": titlels,
                    "文号": wenhaols,
                    "发文日期": datels,
                    "序列号": snls,
                    "链接": urlls,
                    "内容": docls,
                }
            )
            # update orgname
            csrceventdf["机构"] = orgname
            resultls.append(csrceventdf)

        except requests.exceptions.HTTPError as e:
            if dd.status_code == 403:
                print(
                    "403 Forbidden error. Check if the URL requires authentication or if your IP is blocked."
                )
            print(f"HTTP error!: {e}")
            print(f"check url: {url}")
            errorls.append(url)
        except json.JSONDecodeError as e:
            st.error(f"JSON decode error: {e}")
            st.error(f"check url: {url}")
            errorls.append(url)
        except Exception as e:
            st.error("error!: " + str(e))
            st.error("check url: " + str(url))
            errorls.append(url)

        mod = (count + 1) % 5
        if mod == 0 and count > 0:
            tempdf = pd.concat(resultls)
            savename = "temp-" + orgname + "-0-" + str(count + 1) + ".csv"
            savedf2(tempdf, savename)

    wait = random.randint(2, 20)
    time.sleep(wait)
    st.info("finish: " + str(count))
    count += 1

    resultsum = pd.concat(resultls).reset_index(drop=True)
    savedf2(resultsum, "tempall-" + orgname)
    return resultsum


# update sumeventdf
def update_sumeventdf2(currentsum):
    oldsum2 = get_csrc2detail()
    if oldsum2.empty:
        oldidls = []
    else:
        oldidls = oldsum2["链接"].tolist()
    currentidls = currentsum["链接"].tolist()
    # print('oldidls:',oldidls)
    # print('currentidls:', currentidls)
    # get current idls not in oldidls
    newidls = [x for x in currentidls if x not in oldidls]
    # print('newidls:', newidls)
    # newidls=list(set(currentidls)-set(oldidls))
    newdf = currentsum[currentsum["链接"].isin(newidls)]
    # if newdf is not empty, save it
    if newdf.empty is False:
        newdf.reset_index(drop=True, inplace=True)
        nowstr = get_now()
        savename = "csrcdtlall" + nowstr
        savedf2(newdf, savename)
    return newdf


# get url by orgname
def get_url2(orgname):
    id = org2id[orgname]
    url = (
        "http://www.csrc.gov.cn/searchList/"
        + id
        + "?_isAgg=true&_isJson=true&_pageSize=10&_template=index&_rangeTimeGte=&_channelName=&page="
    )
    return url


def savedf2(df, basename):
    savename = basename + ".csv"
    savepath = os.path.join(pencsrc2, savename)
    # df.to_csv(savepath)
    df.to_csv(savepath, index=False, escapechar="\\")


# display bar chart in plotly
def display_search_df(searchdf):
    df_month = searchdf.copy()
    if "发文日期" in df_month.columns:
        df_month["发文日期"] = pd.to_datetime(df_month["发文日期"], errors='coerce').dt.date
        # count by month
        df_month["month"] = df_month["发文日期"].apply(lambda x: x.strftime("%Y-%m") if pd.notna(x) else "")
    else:
        # If no date column, create empty month column
        df_month["month"] = ""
    df_month_count = df_month.groupby(["month"]).size().reset_index(name="count")
    # count by month
    # fig = go.Figure(
    #     data=[go.Bar(x=df_month_count['month'], y=df_month_count['count'])])
    # fig.update_layout(title='处罚数量统计', xaxis_title='月份', yaxis_title='处罚数量')
    # st.plotly_chart(fig)

    # display checkbox to show/hide graph1
    # showgraph1 = st.sidebar.checkbox("按发文时间统计", key="showgraph1")
    # fix value of showgraph1
    showgraph1 = True
    if showgraph1:
        x_data = df_month_count["month"].tolist()
        y_data = df_month_count["count"].tolist()
        # draw echarts bar chart
        # bar = (
        #     Bar()
        #     .add_xaxis(xaxis_data=x_data)
        #     .add_yaxis(series_name="数量", y_axis=y_data, yaxis_index=0)
        #     .set_global_opts(
        #         title_opts=opts.TitleOpts(title="按发文时间统计"),
        #         visualmap_opts=opts.VisualMapOpts(max_=max(y_data), min_=min(y_data)),
        #     )
        # )
        # use events
        # events = {
        #     "click": "function(params) { console.log(params.name); return params.name }",
        #     # "dblclick":"function(params) { return [params.type, params.name, params.value] }"
        # }
        # use events
        # yearmonth = st_pyecharts(bar, events=events)
        bar, yearmonth = print_bar(x_data, y_data, "处罚数量", "按发文时间统计")
        # st.write(yearmonth)
        if yearmonth is not None:
            # get year and month value from format "%Y-%m"
            # year = int(yearmonth.split("-")[0])
            # month = int(yearmonth.split("-")[1])
            # filter date by year and month
            searchdfnew = df_month[df_month["month"] == yearmonth]
            # drop column "month"
            searchdfnew.drop(columns=["month"], inplace=True)

            # set session state
            st.session_state["search_result_csrc2"] = searchdfnew
            # refresh page
            # st.experimental_rerun()

        # 图一解析开始
        maxmonth = df_month["month"].max()
        minmonth = df_month["month"].min()
        # get total number of count
        num_total = len(df_month["month"])
        # get total number of month count
        month_total = len(set(df_month["month"].tolist()))
        # get average number of count per month count
        num_avg = num_total / month_total
        # get month value of max count
        top1month = max(
            set(df_month["month"].tolist()), key=df_month["month"].tolist().count
        )
        top1number = df_month["month"].tolist().count(top1month)

        image1_text = (
            "图一解析：从"
            + minmonth
            + "至"
            + maxmonth
            + "，共发生"
            + str(num_total)
            + "起处罚事件，"
            + "平均每月发生"
            + str(round(num_avg))
            + "起处罚事件。其中"
            + top1month
            + "最高发生"
            + str(top1number)
            + "起处罚事件。"
        )

        # display total coun
        st.markdown("##### " + image1_text)

    # get eventdf sum amount by month
    df_sum, df_sigle_penalty = sum_amount_by_month(df_month)

    sum_data = df_sum["sum"].tolist()
    line, yearmonthline = print_line(x_data, sum_data, "处罚金额", "案例金额统计")

    if yearmonthline is not None:
        # filter date by year and month
        searchdfnew = df_month[df_month["month"] == yearmonthline]
        # drop column "month"
        searchdfnew.drop(columns=["month"], inplace=True)
        # set session state
        st.session_state["search_result_csrc2"] = searchdfnew
        # refresh page
        # st.experimental_rerun()

    # 图二解析：
    sum_data_number = 0  # 把案件金额的数组进行求和
    more_than_100 = 0  # 把案件金额大于100的数量进行统计
    case_total = 0  # 把案件的总数量进行统计

    # Check if amount column exists before processing
    if "amount" in df_sigle_penalty.columns:
        penaltycount = df_sigle_penalty["amount"].tolist()
    else:
        penaltycount = []
    for i in penaltycount:
        sum_data_number = sum_data_number + i / 10000
        if i > 100 * 10000:
            more_than_100 = more_than_100 + 1
        if i != 0:
            case_total = case_total + 1

    # for i in sum_data:
    #     sum_data_number = sum_data_number + i / 10000
    #     if i > 100 * 10000:
    #         more_than_100 = more_than_100 + 1
    # sum_data_number=round(sum_data_number,2)
    if case_total > 0:
        avg_sum = round(sum_data_number / case_total, 2)
    else:
        avg_sum = 0
    # get index of max sum
    topsum1 = df_sum["sum"].nlargest(1)
    topsum1_index = df_sum["sum"].idxmax()
    # get month value of max count
    topsum1month = df_sum.loc[topsum1_index, "month"]
    image2_text = (
        "图二解析：从"
        + minmonth
        + "至"
        + maxmonth
        + "，共发生罚款案件"
        + str(case_total)
        + "起;期间共涉及处罚金额"
        + str(round(sum_data_number, 2))
        + "万元，处罚事件平均处罚金额为"
        + str(avg_sum)
        + "万元，其中处罚金额高于100万元处罚事件共"
        + str(more_than_100)
        + "起。"
        + topsum1month
        + "发生最高处罚金额"
        + str(round(topsum1.values[0] / 10000, 2))
        + "万元。"
    )
    st.markdown("##### " + image2_text)

    # count by orgname
    df_org_count = df_month.groupby(["机构"]).size().reset_index(name="count")
    # sort by count
    df_org_count = df_org_count.sort_values(by="count", ascending=False)
    org_ls = df_org_count["机构"].tolist()
    count_ls = df_org_count["count"].tolist()
    new_orgls, new_countls = count_by_province(org_ls, count_ls)
    # new_orgls1 = fix_cityname(new_orgls, cityls)
    map_data = print_map(new_orgls, new_countls, "处罚地图")
    # st_pyecharts(map_data, map=map, width=800, height=650)
    # display map
    # components.html(map.render_embed(), height=650)

    pie, orgname = print_pie(
        df_org_count["机构"].tolist(), df_org_count["count"].tolist(), "按发文机构统计"
    )
    if orgname is not None:
        # filter searchdf by orgname
        searchdfnew = searchdf[searchdf["机构"] == orgname]
        # set session state
        st.session_state["search_result_csrc2"] = searchdfnew
        # refresh page
        # st.experimental_rerun()

    # 图四解析开始
    # orgls = df_month["机构"].value_counts().keys().tolist()
    # countls = df_month["机构"].value_counts().tolist()
    result = ""

    for org, count in zip(org_ls[:3], count_ls[:3]):
        result = result + org + "（" + str(count) + "起）,"

    image4_text = (
        "图四解析："
        + minmonth
        + "至"
        + maxmonth
        + "，共"
        + str(len(org_ls))
        + "家地区监管机构提出处罚意见，"
        + "排名前三的机构为："
        + result[: len(result) - 1]
    )
    st.markdown("#####  " + image4_text)

    # 图五解析：
    # penalty type count
    # penaltytype = searchdf.groupby("违规类型")["链接"].nunique().reset_index(name="数量统计")
    # # sort by count
    # penaltytype = penaltytype.sort_values(by="数量统计", ascending=False)
    # x_data2 = penaltytype["违规类型"].tolist()
    # y_data2 = penaltytype["数量统计"].tolist()
    # bar2, pentype_selected = print_bar(x_data2[:20], y_data2[:20], "处罚数量", "前20违规类型统计")

    # result5 = ""
    # for i in range(5):
    #     try:
    #         result5 = (
    #             result5
    #             + str(penaltytype.iloc[i, 0])
    #             + "("
    #             + str(penaltytype.iloc[i, 1])
    #             + "起),"
    #         )
    #     except Exception as e:
    #         print(e)
    #         break
    # image5_text = "图五解析：处罚事件中，各违规类型中处罚数量排名前五分别为:" + result5[: len(result5) - 1]
    # st.markdown("##### " + image5_text)

    # 图六解析：
    # get url list from searchdf
    # urllist = searchdf["链接"].tolist()
    # # get lawdetail
    # lawdf = get_lawdetail2()
    # # search lawdetail by selected_rows_id
    # selected_lawdetail = lawdf[lawdf["链接"].isin(urllist)]

    # # law type count
    # lawtype = (
    #     selected_lawdetail.groupby("法律法规")["链接"].nunique().reset_index(name="数量统计")
    # )
    # # sort by count
    # lawtype = lawtype.sort_values(by="数量统计", ascending=False)

    # x_data3 = lawtype["法律法规"].tolist()
    # y_data3 = lawtype["数量统计"].tolist()
    # bar3, lawtype_selected = print_bar(x_data3[:20], y_data3[:20], "处罚数量", "前20法律法规统计")

    # 图六解析开始
    # lawtype_count = lawtype[["法律法规", "数量统计"]]  # 把法律法规的数量进行统计
    # # pandas数据排序
    # lawtype_count = lawtype_count.sort_values("数量统计", ascending=False)
    # result6a = ""
    # for i in range(5):
    #     try:
    #         result6a = (
    #             result6a
    #             + str(lawtype_count.iloc[i, 0])
    #             + "("
    #             + str(lawtype_count.iloc[i, 1])
    #             + "起),"
    #         )
    #     except Exception as e:
    #         print(e)
    #         break
    # # st.markdown(
    # #     "##### 图五解析:法律法规统计-不同法规维度：处罚事件中，各违规类型中处罚数量排名前五分别为:"
    # #     + result5[: len(result5) - 1]
    # # )
    # # by具体条文
    # # lawdf["数量统计"] = ""
    # new_lawtype = (
    #     selected_lawdetail.groupby(["法律法规", "条文"])["链接"]
    #     .nunique()
    #     .reset_index(name="数量统计")
    # )
    # # new_lawtype=lawdf.groupby(['法律法规','条文'])#%%%
    # new_lawtype["法律法规明细"] = new_lawtype["法律法规"] + "(" + new_lawtype["条文"] + ")"

    # lawtype_count = new_lawtype[["法律法规明细", "数量统计"]]  # 把法律法规的数量进行统计
    # # pandas数据排序
    # lawtype_count = lawtype_count.sort_values("数量统计", ascending=False)
    # result6b = ""
    # for i in range(5):
    #     try:
    #         result6b = (
    #             result6b
    #             + str(lawtype_count.iloc[i, 0])
    #             + "("
    #             + str(lawtype_count.iloc[i, 1])
    #             + "起),"
    #         )
    #     except Exception as e:
    #         print(e)
    #         break
    # image6_text = (
    #     " 图六解析:法律法规统计-不同法规维度：处罚事件中，各违规类型中处罚数量排名前五分别为:"
    #     + result6a[: len(result6a) - 1]
    #     + "\n"
    #     + "法律法规统计-具体条文维度：处罚事件中，各违规类型中处罚数量排名前五分别为:"
    #     + result6b[: len(result6b) - 1]
    # )
    # st.markdown("##### " + image6_text)

    # display summary
    # st.markdown("### 分析报告下载")

    # if st.button("生成分析报告"):
    #     # 建title
    #     title = st.session_state["keywords_csrc2"]
    #     title_str = ""
    #     # st.write(str(title[1]))
    #     title_str = "(分析范围：期间:" + str(title[1]) + "至" + str(title[2]) + ","
    #     if len(title[0]) != 0:
    #         title_str = title_str + "发文名称为:" + title[0] + "，"
    #     # if len(str(title[1]))!=0:
    #     #     title_str=title_str+'开始日期为:'+str(title[1])+'，'
    #     # if len(str(title[2]))!=0:
    #     #     title_str=title_str+'结束日期为:'+str(title[2])+'，'
    #     if len(title[3]) != 0:
    #         title_str = title_str + "文号为:" + title[3] + "，"
    #     if len(title[4]) != 0:
    #         title_str = title_str + "案件关键词为:" + title[4] + "，"
    #     if len(title[5]) == 37:
    #         title_str = title_str + "包括总局在内的37家机构，"
    #     else:
    #         title_str = title_str + "发文机构为:" + "、".join(title[5]) + "，"
    #     title_str = title_str[: len(title_str) - 1] + ")"
    #     title_str = "处罚事件分析报告\n" + title_str
    #     # 建图表
    #     t1 = time.localtime()
    #     t1 = time.strftime("%Y-%m-%d %H%M%S", t1)

    #     image3_text = "图三解析：处罚地图"
    #     image1 = bar.render(path=os.path.join(pencsrc2, t1 + "image1.html"))
    #     image2 = line.render(path=os.path.join(pencsrc2, t1 + "image2.html"))
    #     image3 = pie.render(path=os.path.join(pencsrc2, t1 + "image3.html"))
    #     image4 = map_data.render(path=os.path.join(pencsrc2, t1 + "image4.html"))
    #     image5 = bar2.render(path=os.path.join(pencsrc2, t1 + "image5.html"))
    #     image6 = bar3.render(path=os.path.join(pencsrc2, t1 + "image6.html"))
    #     file_name = make_docx(
    #         title_str,
    #         [
    #             image1_text,
    #             image2_text,
    #             image3_text,
    #             image4_text,
    #             image5_text,
    #             image6_text,
    #         ],
    #         [image1, image2, image3, image4, image5, image6],
    #     )
    #     st.download_button(
    #         "下载分析报告", data=file_name.read(), file_name="分析报告.docx"
    #     )  # ,on_click=lambda: os.remove(file_name)
    #     # "下载搜索结果", data=search_dfnew.to_csv().encode("utf_8_sig"), file_name="搜索结果.csv"


# combine count by province
# def count_by_province(orgls, countls):
#     result = dict()
#     for org in orgls:
#         if org == "总部":
#             result["北京"] = result.get("北京", 0) + countls[orgls.index(org)]
#         elif org == "深圳":
#             result["广东"] = result.get("广东", 0) + countls[orgls.index(org)]
#         elif org == "大连":
#             result["辽宁"] = result.get("辽宁", 0) + countls[orgls.index(org)]
#         elif org == "宁波":
#             result["浙江"] = result.get("浙江", 0) + countls[orgls.index(org)]
#         elif org == "厦门":
#             result["福建"] = result.get("福建", 0) + countls[orgls.index(org)]
#         elif org == "青岛":
#             result["山东"] = result.get("山东", 0) + countls[orgls.index(org)]
#         else:
#             result[org] = result.get(org, 0) + countls[orgls.index(org)]
#     new_orgls = result.keys()
#     new_countls = result.values()
#     return new_orgls, new_countls


# def fix_cityname(orgls, cityls):
#     result_ls = []
#     for org in orgls:
#         if org == "总部":
#             result_ls.append("北京市")
#         elif org == "深圳":
#             result_ls.append("广东省")
#         elif org == "大连":
#             result_ls.append("辽宁省")
#         elif org == "宁波":
#             result_ls.append("浙江省")
#         elif org == "厦门":
#             result_ls.append("福建省")
#         elif org == "青岛":
#             result_ls.append("山东省")
#         else:
#             res = [s for s in cityls if org in s]
#             result_ls.append(res[0])
#     return result_ls


def count_by_province(city_ls, count_ls):
    if len(city_ls) != len(count_ls):
        raise ValueError("城市列表和计数列表的长度必须相同")

    # Use Counter for efficient counting
    province_counts = Counter()

    # Use list comprehension for faster iteration
    province_counts.update(
        {city2province[loc]: count for loc, count in zip(city_ls, count_ls)}
    )

    # Use sorted with key function for efficient sorting
    sorted_provinces = sorted(province_counts.items(), key=lambda x: (-x[1], x[0]))

    # Use zip for efficient unpacking
    provinces, counts = zip(*sorted_provinces)

    return list(provinces), list(counts)


# print pie charts
# def print_pie(namels, valuels, title):
#     pie = (
#         Pie()
#         .add(
#             "",
#             [list(z) for z in zip(namels, valuels)],
#             radius=["30%", "60%"],
#             # center=["35%", "50%"]
#         )
#         # set legend position
#         .set_global_opts(
#             title_opts=opts.TitleOpts(title=title)
#             # set legend position to down
#             ,
#             legend_opts=opts.LegendOpts(pos_bottom="bottom"),
#             visualmap_opts=opts.VisualMapOpts(max_=max(valuels)),
#         )
#         .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c}"))
#     )
#     events = {
#         "click": "function(params) { console.log(params.name); return params.name }",
#         # "dblclick":"function(params) { return [params.type, params.name, params.value] }"
#     }
#     clickevent = st_pyecharts(pie, events=events, height=650)  # width=800)
#     return pie, clickevent


def print_pie(namels, valuels, title):
    # Sort data by values in descending order
    sorted_data = sorted(zip(namels, valuels), key=lambda x: x[1], reverse=True)
    
    # Limit to top 10 items and group others
    if len(sorted_data) > 10:
        top_data = sorted_data[:10]
        others_sum = sum(value for _, value in sorted_data[10:])
        
        # Add "其他" category if there are remaining items
        if others_sum > 0:
            top_data.append(("其他", others_sum))
        
        names, values = zip(*top_data)
    else:
        names, values = namels, valuels
    
    data = pd.DataFrame({"names": names, "values": values})

    fig = px.pie(
        data,
        names="names",
        values="values",
        title=title,
        labels={"names": "名称", "values": "数量"},
    )
    
    # Improve layout for better readability
    fig.update_traces(
        textinfo="label+percent", 
        insidetextorientation="radial",
        textfont_size=10,
        # Show percentage only for slices smaller than 3%
        texttemplate="%{label}<br>%{percent}" if len(names) <= 8 else "%{percent}",
        hole=0.3,  # Create donut chart for better readability
    )
    
    # Update layout for better spacing
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        ),
        margin=dict(t=80, b=80, l=50, r=50),
        height=500,
    )
    
    # Display the chart
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    monthselected = event["selection"]["point_indices"]

    if monthselected == []:
        clickevent = None
    else:
        clickevent = names[monthselected[0]]

    return fig, clickevent


def print_bar(x_data, y_data, y_axis_name, title):
    # Create a DataFrame from the input data
    data = pd.DataFrame({"月份": x_data, y_axis_name: y_data})
    # Create the bar chart
    fig = px.bar(
        data,
        x="月份",
        y=y_axis_name,
        title=title,
        color=y_axis_name,
        text=y_axis_name,
        color_continuous_scale=px.colors.sequential.Viridis,
    )

    # Display the chart
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    monthselected = event["selection"]["point_indices"]

    if monthselected == []:
        clickevent = None
    else:
        clickevent = x_data[monthselected[0]]

    return fig, clickevent


def print_line(x_data, y_data, y_axis_name, title):
    # Create a DataFrame from the input data
    data = pd.DataFrame({"月份": x_data, y_axis_name: y_data})
    # Create the line chart
    fig = px.line(data, x="月份", y=y_axis_name, title=title, text=y_axis_name)

    # Display the chart
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    monthselected = event["selection"]["point_indices"]

    if monthselected == []:
        clickevent = None
    else:
        clickevent = x_data[monthselected[0]]

    return fig, clickevent


# province_name为省份名称列表；province_values为各省份对应值；title_name为标题,dataname为值标签（如：处罚案例数量）
# def print_map(province_name, province_values, title_name, dataname):
#     with open(mappath, "r", encoding="utf-8-sig") as f:
#         map = st_Map(
#             "china",
#             json.loads(f.read()),
#         )

#     map_data = (
#         Map()
#         .add(
#             dataname,
#             [list(z) for z in zip(province_name, province_values)],
#             "china",
#             is_roam=False,
#             is_map_symbol_show=False,
#         )
#         .set_series_opts(label_opts=opts.LabelOpts(is_show=True))
#         .set_global_opts(
#             title_opts=opts.TitleOpts(title=title_name),
#             visualmap_opts=opts.VisualMapOpts(
#                 max_=max(province_values)  # , range_color=["#F3F781", "#D04A02"]
#             ),
#         )
#     )
#     # st_pyecharts(map_data, map=map, height=700)  # ,width=800 )
#     return map_data, map


def print_map(province_name, province_values, title_name):
    # load the GeoJSON file
    china_geojson = json.load(open(mappath, "r", encoding="utf-8-sig"))

    # st.write(china_geojson)

    # Create a DataFrame from the provided data
    data = pd.DataFrame({"省份": province_name, "处罚数量": province_values})
    # Create the choropleth map
    # fig = px.choropleth(
    fig = px.choropleth_mapbox(
        data,
        geojson=china_geojson,
        featureidkey="properties.name",
        locations="省份",
        color="处罚数量",
        color_continuous_scale="Viridis",
        mapbox_style="carto-positron",
        zoom=2,
        center={"lat": 35, "lon": 105},
        # scope='asia',
        title=title_name,
    )

    # Add text labels
    fig.update_traces(
        text=data["处罚数量"],
    )

    # Update geos
    fig.update_geos(
        visible=False,
        fitbounds="locations",
    )

    # Update layout
    fig.update_layout(title_text=title_name, title_x=0.5)

    # Display the chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)
    return fig


# content length analysis by length
def content_length_analysis(length, download_filter):
    # eventdf = get_csrc2detail()
    eventdf = get_csrc2analysis()
    eventdf["内容"] = eventdf["内容"].str.replace(
        r"\r|\n|\t|\xa0|\u3000|\s|\xa0", "", regex=True
    )
    eventdf["len"] = eventdf["内容"].astype(str).apply(len)
    misdf = eventdf[eventdf["len"] <= length]

    # filter out name by download_filter
    if download_filter:
        misdf = misdf[~misdf["名称"].str.contains(download_filter, case=False)]

    # get df by column name
    misdf1 = misdf[["发文日期", "名称", "链接", "内容", "len", "filename"]]
    # sort by 发文日期
    misdf1 = misdf1.sort_values(by="发文日期", ascending=False)
    # reset index
    misdf1.reset_index(drop=True, inplace=True)
    # savename
    savename = "csrclenanalysis"
    # save misdf
    savetemp(misdf1, savename)
    return misdf1


# download attachment
def download_attachment(down_list):
    # get csrclenanalysis df
    lendf = get_csrclenanalysis()
    # get misls from url
    misls = lendf["链接"].tolist()
    # get submisls by index list
    submisls = [misls[i] for i in down_list]

    resultls = []
    errorls = []
    count = 0

    driver = get_chrome_driver()

    for i, url in enumerate(submisls):
        st.info("id: " + str(i))
        st.info(str(count) + "begin")
        st.info("url:" + url)
        try:
            # response = requests.get(url, verify=False)
            # for _ in range(5):  # Retry mechanism to ensure page loads completely
            #     if response.status_code == 200:
            #         break
            #     time.sleep(10)
            #     response = requests.get(url, verify=False)

            # if response.status_code != 200:
            #     raise Exception(f"Failed to load page {url}")
            # sd = BeautifulSoup(response.content, "html.parser")

            driver.get(url)
            # Wait for the page to load and the specific element to be present
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "detail-news"))
            )

            page_source = driver.page_source
            sd = BeautifulSoup(page_source, "html.parser")  # Parse the page's HTML

            dirpath = url.rsplit("/", 1)[0]
            try:
                filepath = sd.find_all("div", class_="detail-news")[0].a["href"]
                datapath = dirpath + "/" + filepath
                st.info(datapath)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Referer": url,
                }
                file_response = requests.get(datapath, headers=headers, stream=True)
                file_response.raise_for_status()
                savename = get_now() + os.path.basename(datapath)
                filename = os.path.join(tempdir, savename)
                with open(filename, "wb") as f:
                    for chunk in file_response.iter_content(1024 * 1024 * 2):
                        if chunk:
                            f.write(chunk)
                text = ""
            except Exception as e:
                st.error(str(e))
                savename = ""
                text = sd.find_all("div", class_="detail-news")[0].text
            datals = {"url": url, "filename": savename, "text": text}
            df = pd.DataFrame(datals, index=[0])
            resultls.append(df)
        except Exception as e:
            st.error("error!: " + str(e))
            st.error("check url:" + url)
            errorls.append(url)

        mod = (count + 1) % 10
        if mod == 0 and count > 0:
            tempdf = pd.concat(resultls)
            savename = "temp-" + str(count + 1)
            savetemp(tempdf, savename)

        wait = random.randint(2, 20)
        time.sleep(wait)
        st.info("finish: " + str(count))
        count += 1

    driver.quit()

    misdf = pd.concat(resultls)
    savecsv = "csrcmiscontent" + get_now()
    # reset index
    misdf.reset_index(drop=True, inplace=True)
    savetemp(misdf, savecsv)
    return misdf


def savetemp(df, basename):
    savename = basename + ".csv"
    savepath = os.path.join(tempdir, savename)
    df.to_csv(savepath)


def remove_tempfiles():
    path = os.path.join(tempdir, "*.*")
    files = glob.glob(path, recursive=False)
    for f in files:
        try:
            os.remove(f)
        except OSError as e:
            st.error("Error: %s : %s" % (f, e.strerror))


def update_csrc2text():
    downdf = get_csrcdownload()
    # get filename ls
    txtls = downdf["filename"].tolist()
    # resls = convert_uploadfiles(txtls, tempdir)

    # Backend API disabled - no backend service available
    # try:
    #     url = backendurl + "/convertuploadfiles"
    #     payload = {
    #         "txtls": txtls,
    #         "dirpath": tempdir,
    #     }
    #     headers = {}
    #     res = requests.post(url, headers=headers, params=payload)
    #     st.write(res)
    #     result = res.json()
    #     resls = result["resls"]
    #     st.success("文件转换成功")
    # except Exception as e:
    #     st.error("转换错误: " + str(e))
    #     resls = []
    
    # Since no backend is available, return empty list
    resls = []
    st.warning("后端服务不可用，文件转换功能已禁用")
    downdf["text"] = resls
    savename = "csrc2textupdate"
    savetemp(downdf, savename)
    return downdf


def combine_csrc2text():
    olddf = get_csrc2analysis()
    newdf = get_csrc2textupdate()
    downdf = get_csrcdownload()

    # combine downdf with newdf merge the text column
    toupdf = pd.merge(downdf, newdf, on="url", suffixes=("_x", "_y"))
    # combine text columns
    toupdf["text"] = toupdf["text_x"] + toupdf["text_y"]
    # drop text_x and text_y
    toupdf.drop(columns=["text_x", "text_y"], inplace=True)
    # drop filename_x
    toupdf.drop(columns=["filename_x"], inplace=True)
    # rename filename_y to filename
    toupdf.rename(columns={"filename_y": "filename"}, inplace=True)
    st.markdown("#### 合并后数据")
    st.write(toupdf)

    # update text column match with url
    updf = pd.merge(olddf, toupdf, left_on="链接", right_on="url", how="left")
    updf.loc[updf["text"].notnull(), "内容"] = updf["text"]
    updf.loc[updf["text"].notnull(), "filename_x"] = updf["filename_y"]
    updf1 = updf[
        [
            "名称",
            "文号",
            "发文日期",
            "序列号",
            "链接",
            "内容",
            "机构",
            "org",
            "cat",
            "filename_x",
        ]
    ]
    updf1.columns = [
        "名称",
        "文号",
        "发文日期",
        "序列号",
        "链接",
        "内容",
        "机构",
        "org",
        "cat",
        "filename",
    ]
    updf1["内容"] = updf1["内容"].str.replace(
        r"\r|\n|\t|\xa0|\u3000|\s|\xa0", "", regex=True
    )
    # reset index
    updf1.reset_index(drop=True, inplace=True)
    savename = "csrc2analysis"
    savedf2(updf1, savename)


# update sumeventdf
def update_csrc2analysis():
    newdf = get_csrc2detail()
    newurlls = newdf["链接"].tolist()
    olddf = get_csrc2analysis()
    # if olddf is not empty
    if olddf.empty:
        oldurlls = []
    else:
        oldurlls = olddf["链接"].tolist()
    # get new urlls not in oldidls
    newidls = [x for x in newurlls if x not in oldurlls]

    upddf = newdf[newdf["链接"].isin(newidls)]
    # if newdf is not empty, save it
    if upddf.empty is False:
        updlen = len(upddf)
        st.info("更新了" + str(updlen) + "条数据")
        # combine with olddf
        upddf1 = pd.concat([upddf, olddf])
        # reset index
        upddf1.reset_index(drop=True, inplace=True)
        savename = "csrc2analysis"
        savedf2(upddf1, savename)


def update_label():
    newdf = get_csrc2analysis()
    newurlls = newdf["链接"].tolist()
    # labeldf = get_csrc2label()
    amtdf = get_csrc2cat()
    # if labeldf is not empty
    if amtdf.empty or "id" not in amtdf.columns:
        oldamtls = []
    else:
        oldamtls = amtdf["id"].tolist()

    # get new urlls not in oldamtls
    newamtls = [x for x in newurlls if x not in oldamtls]
    amtupddf = newdf[newdf["链接"].isin(newamtls)]
    # reset index
    amtupddf.reset_index(drop=True, inplace=True)
    # display update data
    st.markdown("#### 待更新分类数据")
    st.write(amtupddf)
    # if newdf is not empty, save it
    if amtupddf.empty is False:
        amtupdlen = len(amtupddf)
        st.info("待更新分类" + str(amtupdlen) + "条数据")
        savename = "csrc2_tocat" + get_nowdate() + ".csv"
        # savedf2(upddf, savename)
        # download detail data
        st.download_button(
            "下载案例数据",
            data=amtupddf.to_csv().encode("utf_8_sig"),
            file_name=savename,
        )
    else:
        st.info("分类数据已更新")

    splitdf = get_csrc2split()
    # if labeldf is not empty
    if splitdf.empty or "id" not in splitdf.columns:
        oldsplitls = []
    else:
        oldsplitls = splitdf["id"].tolist()

    # get new urlls not in oldsplitls
    newsplitls = [x for x in newurlls if x not in oldsplitls]
    splitupddf = newdf[newdf["链接"].isin(newsplitls)]
    # reset index
    splitupddf.reset_index(drop=True, inplace=True)
    # display update data
    st.markdown("#### 待更新拆分数据")
    st.write(splitupddf)
    # if newdf is not empty, save it
    if splitupddf.empty is False:
        splitupdlen = len(splitupddf)
        st.info("待更新拆分" + str(splitupdlen) + "条数据")
        savename = "csrc2_tosplit" + get_nowdate() + ".csv"
        # savedf2(upddf, savename)
        # download detail data
        st.download_button(
            "下载案例数据",
            data=splitupddf.to_csv().encode("utf_8_sig"),
            file_name=savename,
        )
    else:
        st.info("拆分数据已更新")


def download_csrcsum():
    st.markdown("#### 案例数据下载")

    # get old sumeventdf
    oldsum2 = get_csrc2detail()
    # get lengh
    oldlen = len(oldsum2)
    st.write("案例数据量：" + str(oldlen))
    # get id nunique
    oldidn = oldsum2["链接"].nunique()
    st.write("案例数据id数：" + str(oldidn))
    # drop duplicate by id
    oldsum2.drop_duplicates(subset=["链接"], inplace=True)

    # detailname
    detailname = "csrcdtlall" + get_nowdate() + ".csv"
    # download detail data
    st.download_button(
        "下载案例数据", data=oldsum2.to_csv().encode("utf_8_sig"), file_name=detailname
    )

    # download lawdf data
    # lawdf = get_lawdetail2()
    # # get lengh
    # lawlen = len(lawdf)
    # st.write("法律数据量：" + str(lawlen))
    # # get id nunique
    # lawidn = lawdf["链接"].nunique()
    # st.write("法律数据id数：" + str(lawidn))

    # # lawname
    # lawname = "csrc2lawdf" + get_nowdate() + ".csv"
    # st.download_button(
    #     "下载法律数据", data=lawdf.to_csv().encode("utf_8_sig"), file_name=lawname
    # )

    # download label data
    # labeldf = get_csrc2label()
    # # get lengh
    # labellen = len(labeldf)
    # st.write("标签数据量：" + str(labellen))
    # # get id nunique
    # labelidn = labeldf["id"].nunique()
    # st.write("标签数据id数：" + str(labelidn))
    # # drop duplicate by id
    # labeldf.drop_duplicates(subset=["id"], inplace=True)

    # labelname = "csrc2label" + get_nowdate() + ".csv"
    # st.download_button(
    #     "下载标签数据", data=labeldf.to_csv().encode("utf_8_sig"), file_name=labelname
    # )

    # download analysis data
    analysisdf = get_csrc2analysis()
    # get lengh
    analysislen = len(analysisdf)
    st.write("分析数据量：" + str(analysislen))
    # get id nunique
    analysisidn = analysisdf["链接"].nunique()
    st.write("分析数据id数：" + str(analysisidn))
    # drop duplicate by id
    analysisdf.drop_duplicates(subset=["链接"], inplace=True)

    analysisname = "csrc2analysis" + get_nowdate() + ".csv"
    st.download_button(
        "下载分析数据",
        data=analysisdf.to_csv().encode("utf_8_sig"),
        file_name=analysisname,
    )

    # download amount data
    amountdf = get_csrc2cat()
    # get lengh
    amountlen = len(amountdf)
    st.write("分类数据量：" + str(amountlen))
    # get id nunique
    if "id" in amountdf.columns:
        amountidn = amountdf["id"].nunique()
        st.write("分类数据id数：" + str(amountidn))
        # drop duplicate by id
        amountdf.drop_duplicates(subset=["id"], inplace=True)
    else:
        amountidn = 0
        st.write("分类数据id数：" + str(amountidn))

    amountname = "csrccat" + get_nowdate() + ".csv"
    st.download_button(
        "下载分类数据", data=amountdf.to_csv().encode("utf_8_sig"), file_name=amountname
    )

    # download split data
    splitdf = get_csrc2split()
    # get lengh
    splitlen = len(splitdf)
    st.write("拆分数据量：" + str(splitlen))
    # get id nunique
    if "id" in splitdf.columns:
        splitidn = splitdf["id"].nunique()
        st.write("拆分数据id数：" + str(splitidn))
        # drop duplicate by id
        splitdf.drop_duplicates(subset=["id"], inplace=True)
    else:
        splitidn = 0
        st.write("拆分数据id数：" + str(splitidn))

    splitname = "csrcsplit" + get_nowdate() + ".csv"
    st.download_button(
        "下载拆分数据", data=splitdf.to_csv().encode("utf_8_sig"), file_name=splitname
    )


def get_csrc2cat():
    amtdf = get_csvdf(pencsrc2, "csrccat")
    # process amount
    if "amount" in amtdf.columns:
        amtdf["amount"] = amtdf["amount"].astype(float)
    # rename columns law to lawlist
    if "law" in amtdf.columns:
        amtdf.rename(columns={"law": "lawlist"}, inplace=True)

    return amtdf

    # sum amount column of df by month


def sum_amount_by_month(df):
    # amtdf = get_csrc2amt()
    # df1 = pd.merge(
    #     df, amtdf.drop_duplicates("id"), left_on="链接", right_on="id", how="left"
    # )
    df1 = df
    if "发文日期" in df1.columns:
        df1["发文日期"] = pd.to_datetime(df1["发文日期"], errors='coerce').dt.date
        # df=df[df['发文日期']>=pd.to_datetime('2020-01-01')]
        df1["month"] = df1["发文日期"].apply(lambda x: x.strftime("%Y-%m") if pd.notna(x) else "")
    else:
        # If no date column, create empty month column
        df1["month"] = ""
    
    # Check if amount column exists before processing
    if "amount" in df1.columns:
        df_month_sum = df1.groupby(["month"])["amount"].sum().reset_index(name="sum")
        df_sigle_penalty = df1[["month", "amount"]]
    else:
        # If no amount column, create empty dataframes
        df_month_sum = pd.DataFrame(columns=["month", "sum"])
        df_sigle_penalty = pd.DataFrame(columns=["month", "amount"])
    
    return df_month_sum, df_sigle_penalty


def uplink_csrcsum():
    st.markdown("#### 案例数据上线")

    try:
        # get old sumeventdf
        oldsum2 = get_csrc2detail()
        # get lengh
        oldlen = len(oldsum2)
        st.write("案例数据量：" + str(oldlen))
        # get id nunique
        oldidn = oldsum2["链接"].nunique()
        st.write("案例数据id数：" + str(oldidn))
        # drop duplicate by id
        oldsum2.drop_duplicates(subset=["链接"], inplace=True)
    except Exception as e:
        st.error(f"获取案例数据时出错: {str(e)}")
        oldsum2 = pd.DataFrame()
        oldlen = 0
        oldidn = 0

    # detailname
    # detailname = "csrcdtlall" + get_nowdate() + ".csv"

    # download lawdf data
    # lawdf = get_lawdetail2()
    # # get lengh
    # lawlen = len(lawdf)
    # st.write("法律数据量：" + str(lawlen))
    # # get id nunique
    # lawidn = lawdf["链接"].nunique()
    # st.write("法律数据id数：" + str(lawidn))

    # # lawname
    # lawname = "csrc2lawdf" + get_nowdate() + ".csv"

    # download label data
    # labeldf = get_csrc2label()
    # # get lengh
    # labellen = len(labeldf)
    # st.write("标签数据量：" + str(labellen))
    # # get id nunique
    # labelidn = labeldf["id"].nunique()
    # st.write("标签数据id数：" + str(labelidn))
    # # drop duplicate by id
    # labeldf.drop_duplicates(subset=["id"], inplace=True)

    # labelname = "csrc2label" + get_nowdate() + ".csv"
    # download analysis data
    try:
        analysisdf = get_csrc2analysis()
        # get lengh
        analysislen = len(analysisdf)
        st.write("分析数据量：" + str(analysislen))
        # get id nunique
        analysisidn = analysisdf["链接"].nunique()
        st.write("分析数据id数：" + str(analysisidn))
        # drop duplicate by id
        analysisdf.drop_duplicates(subset=["链接"], inplace=True)
    except Exception as e:
        st.error(f"获取分析数据时出错: {str(e)}")
        analysisdf = pd.DataFrame()
        analysislen = 0
        analysisidn = 0

    # download amount data
    try:
        amountdf = get_csrc2cat()
        # get lengh
        amountlen = len(amountdf)
        st.write("分类数据量：" + str(amountlen))
        # get id nunique
        if "id" in amountdf.columns:
            amountidn = amountdf["id"].nunique()
            st.write("分类数据id数：" + str(amountidn))
            # drop duplicate by id
            amountdf.drop_duplicates(subset=["id"], inplace=True)
        else:
            amountidn = 0
            st.write("分类数据id数：" + str(amountidn))
    except Exception as e:
        st.error(f"获取分类数据时出错: {str(e)}")
        amountdf = pd.DataFrame()
        amountlen = 0
        amountidn = 0

    # amountname = "csrc2amt" + get_nowdate() + ".csv"

    # download split data
    try:
        splitdf = get_csrc2split()
        # get lengh
        splitlen = len(splitdf)
        st.write("拆分数据量：" + str(splitlen))
        # get id nunique
        if "id" in splitdf.columns:
            splitidn = splitdf["id"].nunique()
            st.write("拆分数据id数：" + str(splitidn))
            # drop duplicate by id
            splitdf.drop_duplicates(subset=["id"], inplace=True)
        else:
            splitidn = 0
            st.write("拆分数据id数：" + str(splitidn))
    except Exception as e:
        st.error(f"获取拆分数据时出错: {str(e)}")
        splitdf = pd.DataFrame()
        splitlen = 0
        splitidn = 0

    # st.write(analysisdf.head())
    # convert date to datetime
    # analysisdf["发文日期"] = pd.to_datetime(analysisdf["发文日期"])

    # analysisname = "csrc2analysis" + get_nowdate() + ".csv"

    try:
        collection = get_collection("pencsrc2", "csrc2analysis")

        # get all online data
        online_data = get_data(collection)

        # get unique id number from online data
        if "链接" in online_data.columns and not online_data.empty:
            online_id = online_data["链接"].nunique()
        else:
            online_id = 0

        # display online data
        st.write("在线案例数据量：" + str(online_id))

        # download online data
        onlinename = "online_csrc2analysis" + get_nowdate() + ".csv"
        st.download_button(
            "下载在线案例数据",
            data=online_data.to_csv().encode("utf_8_sig"),
            file_name=onlinename,
        )



        # get different data
        if "链接" in online_data.columns and not online_data.empty:
            diff_analysis = analysisdf[~analysisdf["链接"].isin(online_data["链接"])]
        else:
            diff_analysis = analysisdf  # If no online data, all analysis data is different

        # merge with csrc2cat and csrc2split data (使用inner join获取交集)
        try:
            # 首先确保三个数据集都不为空
            if not amountdf.empty and not splitdf.empty and not diff_analysis.empty:
                # 第一步：与csrc2cat数据进行inner join
                diff_data = pd.merge(
                    diff_analysis, 
                    amountdf, 
                    left_on="链接", 
                    right_on="id", 
                    how="inner"
                )
                
                # 第二步：与csrc2split数据进行inner join
                if not diff_data.empty:
                    # 如果diff_data中已有org字段，先删除它以确保使用splitdf中的org字段
                    if 'org' in diff_data.columns:
                        diff_data = diff_data.drop(columns=['org'])
                    
                    diff_data = pd.merge(
                        diff_data, 
                        splitdf, 
                        left_on="链接", 
                        right_on="id", 
                        how="inner",
                        suffixes=('', '_split')
                    )
                else:
                    st.warning("csrc2analysis与csrc2cat没有交集数据")
            else:
                st.warning("缺少必要的数据集，无法生成交集数据")
                diff_data = pd.DataFrame()
            
            # 只保留指定字段
            selected_columns = []
            
            # csrc2analysis字段（包含序列号）
            analysis_fields = ["名称", "文号", "发文日期", "序列号", "链接", "内容", "机构"]
            for field in analysis_fields:
                if field in diff_data.columns:
                    selected_columns.append(field)
            
            # csrc2cat字段
            cat_fields = ["amount", "category", "province", "industry"]
            for field in cat_fields:
                if field in diff_data.columns:
                    selected_columns.append(field)
            
            # csrc2split字段
            split_fields = ["wenhao", "people", "event", "law", "penalty", "org", "date"]
            for field in split_fields:
                if field in diff_data.columns:
                    selected_columns.append(field)
                else:
                    st.write(f"字段 {field} 不存在于合并后的数据中")
            

            
            # 只保留选定的字段
            if selected_columns:
                diff_data = diff_data[selected_columns]
                
        except Exception as e:
            st.error(f"合并关联数据时出错: {str(e)}")
            diff_data = diff_analysis

    except Exception as e:
        st.error(f"连接数据库时出错: {str(e)}")
        online_data = pd.DataFrame()
        online_id = 0
        diff_analysis = analysisdf  # Use all analysis data as diff data
        
        # merge with csrc2cat and csrc2split data for offline case (使用inner join获取交集)
        try:
            # 首先确保三个数据集都不为空
            if not amountdf.empty and not splitdf.empty and not diff_analysis.empty:
                # 第一步：与csrc2cat数据进行inner join
                diff_data = pd.merge(
                    diff_analysis, 
                    amountdf, 
                    left_on="链接", 
                    right_on="id", 
                    how="inner"
                )
                
                # 第二步：与csrc2split数据进行inner join
                if not diff_data.empty:
                    # 如果diff_data中已有org字段，先删除它以确保使用splitdf中的org字段
                    if 'org' in diff_data.columns:
                        diff_data = diff_data.drop(columns=['org'])
                    
                    diff_data = pd.merge(
                        diff_data, 
                        splitdf, 
                        left_on="链接", 
                        right_on="id", 
                        how="inner",
                        suffixes=('', '_split')
                    )
                else:
                    st.warning("csrc2analysis与csrc2cat没有交集数据（离线模式）")
            else:
                st.warning("缺少必要的数据集，无法生成交集数据（离线模式）")
                diff_data = pd.DataFrame()
            
            # 只保留指定字段
            selected_columns = []
            
            # csrc2analysis字段（包含序列号）
            analysis_fields = ["名称", "文号", "发文日期", "序列号", "链接", "内容", "机构"]
            for field in analysis_fields:
                if field in diff_data.columns:
                    selected_columns.append(field)
            
            # csrc2cat字段
            cat_fields = ["amount", "category", "province", "industry"]
            for field in cat_fields:
                if field in diff_data.columns:
                    selected_columns.append(field)
            
            # csrc2split字段
            split_fields = ["wenhao", "people", "event", "law", "penalty", "org", "date"]
            for field in split_fields:
                if field in diff_data.columns:
                    selected_columns.append(field)
                else:
                    st.write(f"字段 {field} 不存在于合并后的数据中（离线模式）")
            

            
            # 只保留选定的字段
            if selected_columns:
                diff_data = diff_data[selected_columns]
                
        except Exception as e:
            st.error(f"合并关联数据时出错: {str(e)}")
            diff_data = diff_analysis
        
        collection = None

    # display different data
    st.write("差异数据量（三表交集）：" + str(len(diff_data)))
    st.write("差异数据为csrc2analysis、csrc2cat、csrc2split三个表的交集，包含指定字段：")
    st.write("- csrc2analysis: 名称、文号、发文日期、链接、内容、机构、序列号")
    st.write("- csrc2cat: 金额、类别、省份、行业")
    st.write("- csrc2split: 文号、当事人、事件、处罚依据、处罚、监管机构、处罚日期")
    st.write(diff_data)

    # download different data
    diffname = "diff_csrc2analysis_with_cat_split_" + get_nowdate() + ".csv"
    st.download_button(
        "下载差异数据（含关联信息）",
        data=diff_data.to_csv().encode("utf_8_sig"),
        file_name=diffname,
    )

    # Insert data into the MongoDB collection
    if st.button("更新上线案例数据"):
        if collection is not None:
            try:
                insert_data(diff_data, collection)
                st.success("更新案例数据上线成功！")
            except Exception as e:
                st.error(f"更新数据时出错: {str(e)}")
        else:
            st.error("数据库连接失败，无法更新数据")


def get_csrc2split():
    pendf = get_csvdf(pencsrc2, "csrcsplit")
    # format date
    # pendf["发文日期"] = pd.to_datetime(pendf["发文日期"]).dt.date
    # # fillna
    # pendf = pendf.fillna("")
    return pendf
