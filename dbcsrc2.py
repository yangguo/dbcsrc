import json
import os
import random
import re
import time
from ast import literal_eval

import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from pyecharts import options as opts
from pyecharts.charts import Bar, Pie
from streamlit_echarts import st_pyecharts

from checkrule import get_lawdtlbyid, get_rulelist_byname
from dbcsrc import get_csvdf, get_now
from utils import df2aggrid, split_words

pencsrc2 = "data/penalty/csrc2"

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
}


# @st.cache(allow_output_mutation=True)
def get_csrc2detail():
    pendf = get_csvdf(pencsrc2, "csrcdtlall")
    # format date
    pendf["发文日期"] = pd.to_datetime(pendf["发文日期"]).dt.date
    # fillna
    pendf = pendf.fillna("")
    return pendf


def get_lawdetail2():
    lawdf = get_csvdf(pencsrc2, "csrc2lawdf")
    # format date
    # lawdf["发文日期"] = pd.to_datetime(lawdf["发文日期"]).dt.date
    # format lawls
    lawdf["处理依据"] = lawdf["处理依据"].apply(literal_eval)
    # fillna
    lawdf = lawdf.fillna("")
    return lawdf


def lawls2dict(ls):
    try:
        result = []
        for item in ls:
            lawdict = dict()
            lawls = re.findall(r"《(.*?)》", item)
            #         print(lawls)
            artls = re.findall(r"(第[^《》（）]*?条)", item)
            #         print(artls)
            lawdict["法律法规"] = lawls[0]
            lawdict["条文"] = artls
            result.append(lawdict)
        return result
    except Exception as e:
        print(e)
        return np.nan


# convert eventdf to lawdf
def generate_lawdf2(d1):
    d1["doc1"] = d1["内容"].str.replace(r"\r|\n|\t|\xa0|\u3000|\s|\xa0", "")
    compat = "(?!《).(《[^,，；。]*?》[^；。]*?第[^,，；。《]*条)"
    compat2 = "(?!《).(《[^,，；。]*?》)"
    d1["lawls"] = d1["doc1"].str.extractall(compat).groupby(level=0)[0].apply(list)

    d1["lawls"].fillna(
        d1["doc1"].str.extractall(compat2).groupby(level=0)[0].apply(list), inplace=True
    )
    d1["处理依据"] = d1["lawls"].apply(lawls2dict)
    d2 = d1[d1["lawls"].notnull()][["链接", "处理依据"]]
    # reset index
    d2.reset_index(drop=True, inplace=True)
    savedf2(d2, "csrc2lawdf")
    return d2


# summary of csrc2
def display_summary2():
    # get old sumeventdf
    oldsum2 = get_csrc2detail()
    # get length of old eventdf
    oldlen2 = len(oldsum2)
    # get min and max date of old eventdf
    min_date2 = oldsum2["发文日期"].min()
    max_date2 = oldsum2["发文日期"].max()
    # use metric
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("案例总数", oldlen2)
    with col2:
        st.metric("案例日期范围", f"{min_date2} - {max_date2}")

    # sum max,min date and size by org
    sumdf2 = oldsum2.groupby("机构")["发文日期"].agg(["max", "min", "count"]).reset_index()
    sumdf2.columns = ["机构", "最近发文日期", "最早发文日期", "案例总数"]
    # sort by date
    sumdf2.sort_values(by=["最近发文日期"], ascending=False, inplace=True)
    # reset index
    sumdf2.reset_index(drop=True, inplace=True)
    # display
    st.markdown("#### 按机构统计")
    st.table(sumdf2)

    return sumdf2


# search by filename, date, wenhao,case,org
def searchcsrc2(df, filename, start_date, end_date, wenhao, case, org):
    col = ["名称", "发文日期", "文号", "内容", "链接", "机构"]
    # convert date to datetime
    # df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    # split words
    if filename != "":
        filename = split_words(filename)
    if wenhao != "":
        wenhao = split_words(wenhao)
    if case != "":
        case = split_words(case)

    searchdf = df[
        (df["名称"].str.contains(filename))
        & (df["发文日期"] >= start_date)
        & (df["发文日期"] <= end_date)
        & (df["文号"].str.contains(wenhao))
        & (df["内容"].str.contains(case))
        & (df["机构"].isin(org))
    ][col]

    # sort by date desc
    searchdf.sort_values(by=["发文日期"], ascending=False, inplace=True)
    # reset index
    searchdf.reset_index(drop=True, inplace=True)
    return searchdf


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
        "下载搜索结果", data=search_dfnew.to_csv().encode("utf_8_sig"), file_name="搜索结果.csv"
    )
    # display columns
    discols = ["发文日期", "名称", "机构", "链接"]
    # get display df
    display_df = search_dfnew[discols]
    # update columns name
    display_df.columns = ["发文日期", "发文名称", "发文机构", "链接"]

    # st.table(search_df)
    data = df2aggrid(display_df)
    # display download button
    # st.sidebar.download_button(
    #     "下载搜索结果", data=search_dfnew.to_csv().encode("utf-8"), file_name="搜索结果.csv"
    # )
    # display data
    selected_rows = data["selected_rows"]
    if selected_rows == []:
        st.error("请先选择查看案例")
        st.stop()
    # # convert selected_rows to dataframe
    # selected_rows_df = pd.DataFrame(selected_rows)
    # get url from selected_rows
    url = selected_rows[0]["链接"]

    selected_rows_df = search_dfnew[search_dfnew["链接"] == url]
    # display event detail
    st.write("案情经过")
    # update columns name
    selected_rows_df.columns = ["发文名称", "发文日期", "文号", "内容", "链接", "发文机构"]
    # transpose dataframe
    selected_rows_df = selected_rows_df.T
    # set column name
    selected_rows_df.columns = ["案情内容"]
    # display
    st.table(selected_rows_df.astype(str))

    # get lawdetail
    lawdf = get_lawdetail2()
    # search lawdetail by selected_rows_id
    selected_rows_lawdetail = lawdf[lawdf["链接"] == url]

    if len(selected_rows_lawdetail) > 0:

        # display lawdetail
        st.write("处罚依据")
        lawdata = pd.DataFrame(selected_rows_lawdetail["处理依据"].values[0])
        lawdata = lawdata.explode("条文")
        # display lawdata
        # st.write(lawdata)

        lawdtl = df2aggrid(lawdata)
        selected_law = lawdtl["selected_rows"]
        if selected_law == []:
            st.error("请先选择查看监管条文")
        else:
            # get selected_law's rule name
            selected_law_name = selected_law[0]["法律法规"]
            # get selected_law's rule article
            selected_law_article = selected_law[0]["条文"]
            # get law detail by name
            ruledf = get_rulelist_byname(selected_law_name, "", "", "", "")
            # get law ids
            ids = ruledf["lawid"].tolist()
            # get law detail by id
            metadf, dtldf = get_lawdtlbyid(ids)
            # display law meta
            st.write("监管法规")
            st.table(metadf)
            # get law detail by article
            articledf = dtldf[dtldf["标题"].str.contains(selected_law_article)]
            # display law detail
            st.write("监管条文")
            st.table(articledf)
    else:
        st.write("没有相关监管法规")


# get sumeventdf in page number range
def get_sumeventdf2(orgname, start, end):
    resultls = []
    resultls = []
    errorls = []
    count = 0
    for pageno in range(start, end + 1):
        st.info("page:" + str(pageno))
        url = get_url2(orgname) + str(pageno)
        try:
            dd = requests.get(url, verify=False)
            sd = BeautifulSoup(dd.content, "html.parser")
            json_data = json.loads(str(sd.text), strict=False)
            itemls = json_data["data"]["results"]

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
        except Exception as e:
            st.error("error!: " + str(e))
            st.error("check url:" + str(url))
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
    df.to_csv(savepath)


# display bar chart in plotly
def display_search_df(searchdf):
    df_month = searchdf.copy()
    df_month["发文日期"] = pd.to_datetime(df_month["发文日期"]).dt.date
    # count by month
    df_month["month"] = df_month["发文日期"].apply(lambda x: x.strftime("%Y-%m"))
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
        bar = (
            Bar()
            .add_xaxis(xaxis_data=x_data)
            .add_yaxis(series_name="数量", y_axis=y_data, yaxis_index=0)
            .set_global_opts(title_opts=opts.TitleOpts(title="按发文时间统计"))
        )
        # use events
        events = {
            "click": "function(params) { console.log(params.name); return params.name }",
            # "dblclick":"function(params) { return [params.type, params.name, params.value] }"
        }
        # use events
        yearmonth = st_pyecharts(bar, events=events)
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
        # display total coun
        st.markdown(
            "#####  图一解析：从"
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
    # display checkbox to show/hide graph2
    # showgraph2 = st.sidebar.checkbox("按发文机构统计", key="showgraph2")
    # fix value of showgraph2
    showgraph2 = True
    if showgraph2:
        # count by orgname
        df_org_count = df_month.groupby(["机构"]).size().reset_index(name="count")
        # draw echarts bar chart
        # bar = (Bar().add_xaxis(
        #     xaxis_data=df_org_count['机构'].tolist(),
        #     ).add_yaxis(
        #         series_name="数量",
        #         y_axis=df_org_count['count'].tolist(),
        #         yaxis_index=0).set_global_opts(title_opts=opts.TitleOpts(
        #             title="按发文机构统计")))
        # st_pyecharts(bar)
        # draw echarts pie chart
        pie = (
            Pie()
            .add(
                "",
                [
                    list(z)
                    for z in zip(
                        df_org_count["机构"].tolist(), df_org_count["count"].tolist()
                    )
                ],
                radius=["30%", "60%"],
                # center=["35%", "50%"]
            )
            # set legend position
            .set_global_opts(
                title_opts=opts.TitleOpts(title="按发文机构统计")
                # set legend position to down
                ,
                legend_opts=opts.LegendOpts(pos_bottom="bottom"),
            )
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c}"))
        )
        events = {
            "click": "function(params) { console.log(params.name); return params.name }",
            # "dblclick":"function(params) { return [params.type, params.name, params.value] }"
        }
        orgname = st_pyecharts(pie, width=800, height=650, events=events)
        if orgname is not None:
            # filter searchdf by orgname
            searchdfnew = searchdf[searchdf["机构"] == orgname]
            # set session state
            st.session_state["search_result_csrc2"] = searchdfnew

        # 图二解析开始
        orgenize = pd.value_counts(df_month["机构"]).keys().tolist()
        count = pd.value_counts(df_month["机构"]).tolist()
        result = ""
        for i in range(3):
            try:
                result = result + orgenize[i] + "所（" + str(count[i]) + "起）,"
            except Exception as e:
                print(e)
                break

        st.markdown(
            "#####  图二解析："
            + minmonth
            + "至"
            + maxmonth
            + "，共"
            + str(len(orgenize))
            + "家地区监管机构提出处罚意见，"
            + "排名前三的机构为："
            + result[: len(result) - 1].replace("总部所", "总部")
        )
