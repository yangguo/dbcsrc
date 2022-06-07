# import matplotlib
import datetime
import glob
import json
import os
import time
from ast import literal_eval

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import requests
import streamlit as st
from bs4 import BeautifulSoup
from plotly.subplots import make_subplots
from pyecharts import options as opts
from pyecharts.charts import Bar, Grid, Line
from streamlit_echarts import st_pyecharts

from checkrule import get_lawdtlbyid, get_rulelist_byname
from utils import df2aggrid, df2echartstable

pencsrc = "data/penalty/csrc"
# mapfolder = 'data/temp/citygeo.csv'

BASE_URL = (
    "https://neris.csrc.gov.cn/falvfagui/multipleFindController/solrSearchWrit?pageNo="
)

urldbase = (
    "https://neris.csrc.gov.cn/falvfagui/rdqsHeader/lawWritInfo?navbarId=1&lawWritId="
)


# @st.cache
def get_csvdf(penfolder, beginwith):
    files2 = glob.glob(penfolder + "**/" + beginwith + "*.csv", recursive=True)
    dflist = []
    # filelist = []
    for filepath in files2:
        pendf = pd.read_csv(filepath)
        dflist.append(pendf)
        # filelist.append(filename)
    if len(dflist) > 0:
        df = pd.concat(dflist)
        df.reset_index(drop=True, inplace=True)
    else:
        df = pd.DataFrame()
    return df


# @st.cache(suppress_st_warning=True)
def get_csrcdetail():
    pendf = get_csvdf(pencsrc, "sdresult")
    # format date
    pendf["发文日期"] = pd.to_datetime(pendf["发文日期"]).dt.date
    return pendf


# @st.cache(suppress_st_warning=True, allow_output_mutation=True)
def get_csrcsum():
    pendf = get_csvdf(pencsrc, "sumevent")
    # format date
    pendf["date1"] = pd.to_datetime(pendf["date"], errors="coerce").dt.date
    pendf.loc[pendf["date1"].isnull(), "date1"] = pd.to_datetime(
        pendf[pendf["date1"].isnull()]["date"], unit="ms", errors="coerce"
    ).dt.date
    return pendf


# get lawdetail
# @st.cache(suppress_st_warning=True)
def get_lawdetail():
    lawdf = get_csvdf(pencsrc, "lawdf")
    # format date
    lawdf["发文日期"] = pd.to_datetime(lawdf["发文日期"]).dt.date
    return lawdf


# get peopledetail
# @st.cache(suppress_st_warning=True)
def get_peopledetail():
    peopledf = get_csvdf(pencsrc, "peopledf")
    # format date
    peopledf["发文日期"] = pd.to_datetime(peopledf["发文日期"]).dt.date
    return peopledf


# search by filename, date, org, case, type
def searchcsrc(df, filename, start_date, end_date, org, case, type):
    col = ["文件名称", "发文日期", "发文单位", "案情经过", "文书类型", "id"]
    # convert date to datetime
    # df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    searchdf = df[
        (df["文件名称"].str.contains(filename))
        & (df["发文日期"] >= start_date)
        & (df["发文日期"] <= end_date)
        & (df["发文单位"].str.contains(org))
        & (df["案情经过"].str.contains(case))
        & (df["文书类型"].isin(type))
    ][col]
    # get summary
    # searchdf1['案情经过'] = searchdf1['案情经过'].apply(get_summary)
    # searchdf1['案情经过'] = searchdf1['案情经过'].apply(lambda x: x[:100] + '...')
    # sort by date desc
    searchdf.sort_values(by=["发文日期"], ascending=False, inplace=True)
    # reset index
    searchdf.reset_index(drop=True, inplace=True)

    return searchdf


# search law by filename_text,start_date,end_date , org_text,law_text,article_text,  type_text
def searchlaw(
    df, filename_text, start_date, end_date, org_text, law_text, article_text, type_text
):
    col = ["文件名称", "发文日期", "文书类型", "发文单位", "法律法规", "条文", "id"]
    # convert date to datetime
    # df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    searchdf = df[
        (df["文件名称"].str.contains(filename_text))
        & (df["发文日期"] >= start_date)
        & (df["发文日期"] <= end_date)
        & (df["发文单位"].str.contains(org_text))
        & (df["法律法规"].isin(law_text))
        & (df["条文"].str.contains(article_text))
        & (df["文书类型"].isin(type_text))
    ][col]
    # sort by date desc
    searchdf.sort_values(by=["发文日期"], ascending=False, inplace=True)
    # reset index
    searchdf.reset_index(drop=True, inplace=True)
    return searchdf


# search people by filename_text,start_date,end_date , org_text,people_type_text, people_name_text, people_position_text, penalty_type_text, penalty_result_text, type_text)
def searchpeople(
    df,
    filename_text,
    start_date,
    end_date,
    org_text,
    people_type_text,
    people_name_text,
    people_position_text,
    penalty_type_text,
    penalty_result_text,
    type_text,
):
    col = [
        "文件名称",
        "发文日期",
        "文书类型",
        "发文单位",
        "当事人类型",
        "当事人名称",
        "当事人身份",
        "违规类型",
        "处罚结果",
        "id",
    ]
    # convert date to datetime
    # df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    searchdf = df[
        (df["文件名称"].str.contains(filename_text))
        & (df["发文日期"] >= start_date)
        & (df["发文日期"] <= end_date)
        & (df["发文单位"].str.contains(org_text))
        & (df["当事人类型"].isin(people_type_text))
        & (df["当事人名称"].str.contains(people_name_text))
        & (df["当事人身份"].isin(people_position_text))
        & (df["违规类型"].isin(penalty_type_text))
        & (df["处罚结果"].str.contains(penalty_result_text))
        & (df["文书类型"].isin(type_text))
    ][col]
    # sort by date desc
    searchdf.sort_values(by=["发文日期"], ascending=False, inplace=True)
    # reset index
    searchdf.reset_index(drop=True, inplace=True)
    return searchdf


# convert eventdf to lawdf
def generate_lawdf(eventdf):
    law1 = eventdf[["id", "文件名称", "文号", "发文日期", "文书类型", "发文单位", "原文链接", "处理依据"]]

    law1["处理依据"] = law1["处理依据"].apply(literal_eval)

    law2 = law1.explode("处理依据")

    law3 = law2["处理依据"].apply(pd.Series)

    law4 = pd.concat([law2, law3], axis=1)

    law5 = law4.explode("条文")

    law6 = law5.drop(["处理依据"], axis=1)

    lawdf = law6[["id", "文件名称", "文号", "发文日期", "文书类型", "发文单位", "原文链接", "法律法规", "条文"]]

    # reset index
    lawdf.reset_index(drop=True, inplace=True)
    savedf(lawdf, "lawdf")
    return lawdf


# convert eventdf to peopledf
def generate_peopledf(eventdf):
    peopledf = eventdf[["id", "文件名称", "文号", "发文日期", "文书类型", "发文单位", "原文链接", "当事人信息"]]

    peopledf["当事人信息"] = peopledf["当事人信息"].apply(literal_eval)

    peopledf2 = peopledf.explode("当事人信息")

    peoplesp1 = peopledf2["当事人信息"].apply(pd.Series)

    peopledf3 = pd.concat([peopledf2, peoplesp1], axis=1)

    peopledf4 = peopledf3[
        [
            "id",
            "文件名称",
            "文号",
            "发文日期",
            "文书类型",
            "发文单位",
            "原文链接",
            "当事人类型",
            "当事人名称",
            "当事人身份",
            "违规类型",
            "处罚结果",
        ]
    ]

    # reset index
    peopledf4.reset_index(drop=True, inplace=True)
    savedf(peopledf4, "peopledf")
    return peopledf4


def savedf(df, basename):
    savename = basename + ".csv"
    savepath = os.path.join(pencsrc, savename)
    df.to_csv(savepath)


# count the number of df by month
def count_by_month(df):
    df_month = df.copy()
    # count by month
    df_month["month"] = df_month["发文日期"].apply(lambda x: x.strftime("%Y-%m"))
    df_month_count = (
        df_month.groupby(["month"])["id"].nunique().reset_index(name="count")
    )
    return df_month_count


# sum amount column of df by month
def sum_amount_by_month(df):
    df["发文日期"] = pd.to_datetime(df["发文日期"]).dt.date
    # df=df[df['发文日期']>=pd.to_datetime('2020-01-01')]
    df["month"] = df["发文日期"].apply(lambda x: x.strftime("%Y-%m"))
    df["amt"] = df["处罚结果"].str.extract("(.*)万元")
    df["amt"].fillna(0, inplace=True)
    df["amt"] = df["amt"].astype(float)
    df["amt"] = df["amt"] * 10000
    df_month_sum = df.groupby(["month"])["amt"].sum().reset_index(name="sum")
    return df_month_sum


def count_by_date(df):
    df["发文日期"] = pd.to_datetime(df["发文日期"]).dt.date
    df["发文日期"] = df["发文日期"].apply(lambda x: x.strftime("%Y-%m-%d"))
    df1 = df.groupby("发文日期").count()
    df1.reset_index(inplace=True)
    df1.rename(columns={"文件名称": "count"}, inplace=True)
    # draw plotly bar chart
    fig = go.Figure(data=[go.Bar(x=df1["发文日期"], y=df1["count"])])
    return fig


# display searchdf in plotly
def display_dfmonth(search_df):
    # get search_df id list
    search_df_id = search_df["id"].tolist()
    # get people detail
    peopledf = get_peopledetail()
    # search people detail by selected_rows_id
    selected_peopledetail = peopledf[peopledf["id"].isin(search_df_id)]
    # get lawdf
    lawdf = get_lawdetail()
    # search lawdetail by selected_rows_id
    selected_lawdetail = lawdf[lawdf["id"].isin(search_df_id)]
    # get eventdf count by month
    df_month = count_by_month(search_df)
    # get eventdf sum amount by month
    df_sum = sum_amount_by_month(selected_peopledetail)

    # display checkbox to show/hide graph1
    showgraph1 = st.sidebar.checkbox("案例数量和金额统计", key="showgraph1")

    if showgraph1:
        # fig = go.Figure()
        # trace1 = go.Bar(x=df_month['month'], y=df_month['count'], name='数量统计')
        # trace2 = go.Scatter(x=df_sum['month'], y=df_sum['sum'], name='金额统计')
        # fig = make_subplots(specs=[[{"secondary_y": True}]])
        # fig.add_trace(trace1)
        # fig.add_trace(trace2, secondary_y=True)
        # fig.update_layout(height=600,width=800,title_text="案例数量和金额统计")
        # st.plotly_chart(fig)
        x_data = df_month["month"].tolist()
        y_data = df_month["count"].tolist()
        sum_data = df_sum["sum"].tolist()

        bar = (
            Bar()
            .add_xaxis(xaxis_data=x_data)
            .add_yaxis(series_name="数量", y_axis=y_data, yaxis_index=0)
            .set_global_opts(title_opts=opts.TitleOpts(title="案例数量统计"))
        )
        line = (
            Line()
            .add_xaxis(x_data)
            .add_yaxis(
                "金额", sum_data, yaxis_index=1, label_opts=opts.LabelOpts(is_show=False)
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="案例金额统计", pos_top="48%"),
                legend_opts=opts.LegendOpts(pos_top="48%"),
            )
        )
        grid = Grid()
        grid.add(bar, grid_opts=opts.GridOpts(pos_bottom="60%"))
        grid.add(line, grid_opts=opts.GridOpts(pos_top="60%"))
        st_pyecharts(grid, height=600, width=800)

    # people type count
    peopletype = (
        selected_peopledetail.groupby("当事人身份")["id"].nunique().reset_index(name="数量统计")
    )
    # sort by count
    peopletype = peopletype.sort_values(by="数量统计", ascending=False)
    # penalty type count
    penaltytype = (
        selected_peopledetail.groupby("违规类型")["id"].nunique().reset_index(name="数量统计")
    )
    # sort by count
    penaltytype = penaltytype.sort_values(by="数量统计", ascending=False)
    # law type count
    lawtype = (
        selected_lawdetail.groupby("法律法规")["id"].nunique().reset_index(name="数量统计")
    )
    # sort by count
    lawtype = lawtype.sort_values(by="数量统计", ascending=False)

    # display checkbox to show/hide graph1
    showgraph2 = st.sidebar.checkbox("当事人身份统计", key="showgraph2")

    if showgraph2:
        # draw plotly bar chart
        # fig = go.Figure()
        # # make subplots of for three graphs in one figure,y label, with specs for the bar,bar,pie
        # fig = make_subplots(rows=3,
        #                     cols=1,
        #                     specs=[[{
        #                         "type": "bar"
        #                     }], [{
        #                         "type": "bar"
        #                     }], [{
        #                         "type": "bar"
        #                     }]])
        # # add trace of people type
        # fig.add_trace(go.Bar(x=peopletype['当事人身份'],
        #                      y=peopletype['数量统计'],
        #                      name='当事人身份',
        #                      legendgroup='peopletype'),
        #               row=1,
        #               col=1)
        # # add trace of penalty type
        # fig.add_trace(go.Bar(x=penaltytype['违规类型'],
        #                      y=penaltytype['数量统计'],
        #                      name='违规类型',
        #                      legendgroup='penaltytype'),
        #               row=2,
        #               col=1)
        # add trace of law type using pie chart
        # fig.add_trace(go.Pie(labels=lawtype['法律法规'],
        #                         values=lawtype['数量统计'],
        #                         textinfo='value+percent',

        #                         name='法律法规',legendgroup='lawtype'),
        #                 row=3, col=1)
        # set layout of legend
        # fig.update_layout(legend_orientation="h",
        #                     legend=dict(x=0, y=1.2))
        # fig.add_trace(go.Bar(x=lawtype['法律法规'], y=lawtype['数量统计'],
        #                      name='法律法规'),
        #               row=3,
        #               col=1)
        # # update layout of subplots
        # fig.update_layout(height=1200,
        #                   width=800,
        #                   title_text="当事人身份、违规类型、法律法规统计")
        # st.plotly_chart(fig)

        x_data1 = peopletype["当事人身份"].tolist()
        y_data1 = peopletype["数量统计"].tolist()
        bar1 = (
            Bar()
            .add_xaxis(xaxis_data=x_data1)
            .add_yaxis(series_name="数量", y_axis=y_data1)
            .set_global_opts(
                xaxis_opts=opts.AxisOpts(
                    axislabel_opts=opts.LabelOpts(is_show=True, rotate=-15)
                ),
                title_opts=opts.TitleOpts(title="当事人身份统计"),
            )
        )
        # display bar chart
        st_pyecharts(bar1, width=800, height=400)

    showgraph3 = st.sidebar.checkbox("违规类型统计", key="showgraph3")
    if showgraph3:
        x_data2 = penaltytype["违规类型"].tolist()
        y_data2 = penaltytype["数量统计"].tolist()
        bar2 = (
            Bar()
            .add_xaxis(xaxis_data=x_data2)
            .add_yaxis(
                series_name="数量",
                y_axis=y_data2,
                # label_opts=opts.LabelOpts(is_show=True, position="inside")
            )
            .set_global_opts(
                xaxis_opts=opts.AxisOpts(
                    axislabel_opts=opts.LabelOpts(is_show=True, rotate=-15)
                ),
                # yaxis_opts=opts.AxisOpts(
                #     axislabel_opts=opts.LabelOpts(is_show=True, rotate=-15),
                #     # axisline_opts=opts.AxisLineOpts(
                #     #     linestyle_opts=opts.LineStyleOpts(color="#5793f3", )),
                #     # axislabel_opts=opts.LabelOpts(formatter="{value} ml"),
                # ),
                title_opts=opts.TitleOpts(title="违规类型统计"),
            )
        )
        # display bar chart
        st_pyecharts(bar2, width=800, height=400)

    showgraph4 = st.sidebar.checkbox("法律法规统计", key="showgraph4")
    if showgraph4:
        x_data3 = lawtype["法律法规"].tolist()
        y_data3 = lawtype["数量统计"].tolist()
        bar3 = (
            Bar()
            .add_xaxis(xaxis_data=x_data3)
            .add_yaxis(series_name="数量", y_axis=y_data3)
            .set_global_opts(
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-15)),
                title_opts=opts.TitleOpts(title="法律法规统计"),
            )
        )
        # display bar chart
        st_pyecharts(bar3, width=800, height=400)


def json2df(site_json):
    idls = []
    namels = []
    issueorgls = []
    filenols = []
    datels = []
    for i in range(20):
        idls.append(site_json["pageUtil"]["pageList"][i]["lawWritId"])
        namels.append(site_json["pageUtil"]["pageList"][i]["name"])
        issueorgls.append(site_json["pageUtil"]["pageList"][i]["issueOrgName"])
        filenols.append(site_json["pageUtil"]["pageList"][i]["fileno"])
        datels.append(site_json["pageUtil"]["pageList"][i]["dsptDate"])

    eventdf = pd.DataFrame(
        {
            "id": idls,
            "name": namels,
            "issueorg": issueorgls,
            "fileno": filenols,
            "date": datels,
        }
    )
    eventdf["date"] = (
        eventdf["date"].astype(str).apply(lambda x: pd.to_datetime(x[:10], unit="s"))
    )

    return eventdf


# get sumeventdf in page number range
def get_sumeventdf(start, end):
    resultls = []
    for pageno in range(start, end + 1):
        st.info("page:" + str(pageno))
        url = BASE_URL + str(pageno)
        pp = requests.get(url, verify=False)
        ss = BeautifulSoup(pp.content, "html.parser")
        ss_json = json.loads(ss.text)
        resultdf = json2df(ss_json)
        resultls.append(resultdf)
        st.info("OK")
        time.sleep(5)

    resultsum = pd.concat(resultls).reset_index(drop=True)
    # savedf(resultsum,'sumeventdf')
    return resultsum


# get current date and time string
def get_now():
    now = datetime.datetime.now()
    now_str = now.strftime("%Y%m%d%H%M%S")
    return now_str


# update sumeventdf
def update_sumeventdf(currentsum):
    oldsum = get_csrcsum()
    if oldsum.empty:
        oldidls = []
    else:
        oldidls = oldsum["id"].tolist()
    currentidls = currentsum["id"].tolist()
    # print('oldidls:',oldidls)
    # print('currentidls:', currentidls)
    # get current idls not in oldidls
    newidls = [x for x in currentidls if x not in oldidls]
    # print('newidls:', newidls)
    # newidls=list(set(currentidls)-set(oldidls))
    newdf = currentsum[currentsum["id"].isin(newidls)]
    # if newdf is not empty, save it
    if newdf.empty == False:
        newdf.reset_index(drop=True, inplace=True)
        nowstr = get_now()
        savename = "sumevent" + nowstr
        savedf(newdf, savename)
    return newdf


def title2detail(sdtitlels, detail):
    detail["文件名称"] = sdtitlels[0].text
    detail["文号"] = sdtitlels[1].text.strip()
    detail["发文日期"] = sdtitlels[2].text.strip()
    detail["文书类型"] = sdtitlels[3].text.strip()
    detail["发文单位"] = sdtitlels[4].text.strip()
    detail["原文链接"] = sdtitlels[5].text.strip()


def law2detail(sdlawls, detail):
    lawdetaills = []
    for i in range(3, len(sdlawls)):
        try:
            span = sdlawls[i]["rowspan"]
        except Exception as e:
            st.error(e)
            span = None
        if span:
            lawdetail = dict()
            itemls = []
            lawdetail["法律法规"] = sdlawls[i].text.strip()
            itemls = [sdlawls[j].text.strip() for j in range(i + 1, i + 1 + int(span))]
            lawdetail["条文"] = itemls
            lawdetaills.append(lawdetail)
        else:
            pass
    detail["处理依据"] = lawdetaills


def people2detail(sdpeoplels, detail):
    peoplenum = (len(sdpeoplels) - 6) // 5

    pdetail = dict()
    pdetaills = []
    for pno in range(peoplenum):
        #     print(pno)
        pdetail = dict()
        pdetail["当事人类型"] = sdpeoplels[6 + pno * 5].text.strip()
        pdetail["当事人名称"] = sdpeoplels[6 + pno * 5 + 1].text.strip()
        pdetail["当事人身份"] = sdpeoplels[6 + pno * 5 + 2].text.strip()
        pdetail["违规类型"] = sdpeoplels[6 + pno * 5 + 3].text.strip()
        pdetail["处罚结果"] = sdpeoplels[6 + pno * 5 + 4].text.strip()
        pdetaills.append(pdetail)
    detail["当事人信息"] = pdetaills


def fact2detail(sdfactls, detail):
    detail["案情经过"] = sdfactls[0].text.replace("\u3000", "").replace("\n", "")


# get event detail
def get_eventdetail(eventsum):
    # outputfile = pencsrc+'sdresult_0-'
    idls = eventsum["id"].tolist()

    sdresultls = []
    count = 0
    for i in idls:
        st.info("id: " + str(i))
        st.info(str(count) + " begin")
        url = urldbase + str(i)
        dd = requests.get(url, verify=False)
        sd = BeautifulSoup(dd.content, "html.parser")

        detail = dict()
        detail["id"] = i
        sdtitlels = sd.find_all(class_="text-left")

        sdlawls = sd.find_all("td", class_="text-center")

        sdpeoplels = sd.find_all(class_="table table-bordered table-condensed")[
            1
        ].find_all("td")

        sdfactls = sd.find_all(class_="pre_law")

        title2detail(sdtitlels, detail)
        law2detail(sdlawls, detail)
        people2detail(sdpeoplels, detail)
        fact2detail(sdfactls, detail)
        sdresultls.append(detail)

        # save temp result
        mod = (count + 1) % 5
        batch = (count + 1) // 5
        if mod == 0 and count > 0:
            sdresultdf = pd.DataFrame.from_dict(sdresultls)
            savename = "temp" + str(count + 1)
            savedf(sdresultdf, savename)
            st.info("batch:{} is ok".format(batch))

        st.info(str(count) + " is ok")
        count = count + 1
        time.sleep(5)

    alldf = pd.DataFrame.from_dict(sdresultls)
    # if alldf is not empty, save it
    if alldf.empty == False:
        nowstr = get_now()
        savename = "sdresult" + nowstr
        savedf(alldf, savename)
    return alldf


# display event detail
def display_eventdetail(search_df):
    total = len(search_df)
    st.sidebar.metric("总数:", total)
    # count by month
    # df_month = count_by_month(search_df)
    # draw plotly figure
    display_dfmonth(search_df)
    # display search result
    st.markdown("### 搜索结果")
    # st.table(search_df)
    data = df2aggrid(search_df)
    # display download button
    st.sidebar.download_button(
        "下载搜索结果", data=search_df.to_csv().encode("utf-8"), file_name="搜索结果.csv"
    )
    # display data
    selected_rows = data["selected_rows"]
    if selected_rows == []:
        st.error("请先选择查看案例")
        st.stop()
    # convert selected_rows to dataframe
    selected_rows_df = pd.DataFrame(selected_rows)

    # get selected_rows_df's id
    selected_rows_id = selected_rows_df["id"].tolist()
    # get lawdf
    lawdf = get_lawdetail()
    # search lawdetail by selected_rows_id
    selected_rows_lawdetail = lawdf[lawdf["id"].isin(selected_rows_id)]
    # display lawdetail
    st.write("处罚依据")
    # st.table(selected_rows_lawdetail[['法律法规', '条文']])
    lawdata = selected_rows_lawdetail[["法律法规", "条文"]]
    lawdtl = df2aggrid(lawdata)
    selected_law = lawdtl["selected_rows"]
    if selected_law == []:
        st.error("请先选择查看监管条文")
    else:
        # get selected_law's rule name
        selected_law_name = selected_law[0]["法律法规"]
        # get selected_law's rule article
        selected_law_article = selected_law[0]["条文"]
        # get selected_law's rule df
        # name_text=selected_law_name
        # industry_choice='证券市场'
        # ruledf, choicels = searchByName(name_text, industry_choice)
        # # search lawdetail by article
        # articledf=ruledf[ruledf['结构'].str.contains(selected_law_article)]
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
    # get people detail
    peopledf = get_peopledetail()
    # search people detail by selected_rows_id
    selected_rows_peopledetail = peopledf[peopledf["id"].isin(selected_rows_id)]
    # display people detail
    # st.write('当事人信息')
    # st.dataframe(
    #     selected_rows_peopledetail[['当事人类型', '当事人名称', '当事人身份', '违规类型',
    #                                 '处罚结果']])
    people_data = selected_rows_peopledetail[
        ["当事人类型", "当事人名称", "当事人身份", "违规类型", "处罚结果"]
    ]
    df2echartstable(people_data, "当事人信息")
    # get event detail
    eventdf = get_csrcdetail()
    # search event detail by selected_rows_id
    selected_rows_eventdetail = eventdf[eventdf["id"].isin(selected_rows_id)]
    # display event detail
    # st.write('案情经过')
    # st.table(selected_rows_eventdetail[['文件名称', '发文日期', '发文单位', '文书类型']])
    # get event detail
    event_data = selected_rows_eventdetail[["文件名称", "发文日期", "发文单位", "文书类型"]]
    df2echartstable(event_data, "案情经过")
    # transpose and display event detail
    st.table(selected_rows_eventdetail[["案情经过"]])
    # get event detail
    # eventdtl_data=selected_rows_eventdetail[['案情经过']]
    # df2echartstable(eventdtl_data,'案情经过')
