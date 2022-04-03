import pandas as pd
import glob, os
import plotly.express as px
import plotly.graph_objs as go
from utils import get_summary
from ast import literal_eval

import requests
from bs4 import BeautifulSoup
import json
import time
# import matplotlib
import datetime

import streamlit as st

pencsrc = 'csrc'
# mapfolder = 'data/temp/citygeo.csv'

BASE_URL = 'https://neris.csrc.gov.cn/falvfagui/multipleFindController/solrSearchWrit?pageNo='

urldbase = 'https://neris.csrc.gov.cn/falvfagui/rdqsHeader/lawWritInfo?navbarId=1&lawWritId='


# @st.cache
def get_csvdf(penfolder, beginwith):
    files2 = glob.glob(penfolder + '**/' + beginwith + '*.csv', recursive=True)
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


def get_csrcdetail():
    pendf = get_csvdf(pencsrc, 'sdresult')
    return pendf


def get_csrcsum():
    pendf = get_csvdf(pencsrc, 'sumevent')
    return pendf

# get lawdetail
def get_lawdetail():
    lawdf = get_csvdf(pencsrc, 'lawdf')
    return lawdf

# get peopledetail
def get_peopledetail():
    peopledf= get_csvdf(pencsrc, 'peopledf')
    return peopledf


#search by filename, date, org, case, type
def searchcsrc(df, filename, start_date, end_date, org, case, type):
    col = ['文件名称', '发文日期', '发文单位', '案情经过', '文书类型']
    # convert date to datetime
    df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    searchdf = df[(df['文件名称'].str.contains(filename))
                  & (df['发文日期'] >= start_date) & (df['发文日期'] <= end_date) &
                  (df['发文单位'].str.contains(org)) &
                  (df['案情经过'].str.contains(case)) &
                  (df['文书类型'].isin(type))][col]
    # get summary
    # searchdf1['案情经过'] = searchdf1['案情经过'].apply(get_summary)
    # searchdf1['案情经过'] = searchdf1['案情经过'].apply(lambda x: x[:100] + '...')
    return searchdf


#search law by filename_text,start_date,end_date , org_text,law_text,article_text,  type_text
def searchlaw(df,filename_text,start_date,end_date , org_text,law_text,article_text,  type_text):
    col = ['文件名称', '发文日期', '文书类型', '发文单位', '法律法规', '条文']
    # convert date to datetime
    df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    searchdf = df[(df['文件名称'].str.contains(filename_text))
                  & (df['发文日期'] >= start_date) & (df['发文日期'] <= end_date) &
                  (df['发文单位'].str.contains(org_text)) &
                  (df['法律法规'].isin(law_text)) &
                  (df['条文'].str.contains(article_text)) &
                  (df['文书类型'].isin(type_text))][col]

    return searchdf

#search people by filename_text,start_date,end_date , org_text,people_type_text, people_name_text, people_position_text, penalty_type_text, penalty_result_text, type_text)
def searchpeople(df, filename_text,start_date,end_date , org_text,people_type_text, people_name_text, people_position_text, penalty_type_text, penalty_result_text, type_text):
    col = ['文件名称', '发文日期', '文书类型', '发文单位', '当事人类型', '当事人名称', '当事人身份', '违规类型', '处罚结果']
    # convert date to datetime
    df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    searchdf = df[(df['文件名称'].str.contains(filename_text))
                  & (df['发文日期'] >= start_date) & (df['发文日期'] <= end_date) &
                  (df['发文单位'].str.contains(org_text)) &
                  (df['当事人类型'].isin(people_type_text)) &
                  (df['当事人名称'].str.contains(people_name_text)) &
                  (df['当事人身份'].isin(people_position_text)) &
                  (df['违规类型'].isin(penalty_type_text)) &
                  (df['处罚结果'].str.contains(penalty_result_text)) &
                  (df['文书类型'].isin(type_text))][col]
   
    return searchdf
                                

# convert eventdf to lawdf
def generate_lawdf(eventdf):
    law1 = eventdf[['文件名称', '文号', '发文日期', '文书类型', '发文单位', '原文链接', '处理依据']]

    law1['处理依据'] = law1['处理依据'].apply(literal_eval)

    law2 = law1.explode('处理依据')

    law3 = law2['处理依据'].apply(pd.Series)

    law4 = pd.concat([law2, law3], axis=1)

    law5 = law4.explode('条文')

    law6 = law5.drop(['处理依据'], axis=1)

    lawdf = law6[['文件名称', '文号', '发文日期', '文书类型', '发文单位', '原文链接', '法律法规', '条文']]

    # reset index
    lawdf.reset_index(drop=True, inplace=True)
    savedf(lawdf, 'lawdf')
    return lawdf


# convert eventdf to peopledf
def generate_peopledf(eventdf):
    peopledf = eventdf[['文件名称', '文号', '发文日期', '文书类型', '发文单位', '原文链接', '当事人信息']]

    peopledf['当事人信息'] = peopledf['当事人信息'].apply(literal_eval)

    peopledf2 = peopledf.explode('当事人信息')

    peoplesp1 = peopledf2['当事人信息'].apply(pd.Series)

    peopledf3 = pd.concat([peopledf2, peoplesp1], axis=1)

    peopledf4 = peopledf3[[
        '文件名称', '文号', '发文日期', '文书类型', '发文单位', '原文链接', '当事人类型', '当事人名称',
        '当事人身份', '违规类型', '处罚结果'
    ]]

    # reset index
    peopledf4.reset_index(drop=True, inplace=True)
    savedf(peopledf4, 'peopledf')
    return peopledf4


def savedf(df, basename):
    savename = basename + '.csv'
    savepath = os.path.join(pencsrc, savename)
    df.to_csv(savepath)


# count the number of df by month
def count_by_month(df):
    df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    df['month'] = df['发文日期'].apply(lambda x: x.strftime('%Y-%m'))
    df['count'] = 1
    df_month = df.groupby(['month']).count()
    # reset index
    df_month.reset_index(inplace=True)
    return df_month


def count_by_date(df):
    df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    df['发文日期'] = df['发文日期'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df1 = df.groupby('发文日期').count()
    df1.reset_index(inplace=True)
    df1.rename(columns={'文件名称': 'count'}, inplace=True)
    # draw plotly bar chart
    fig = go.Figure(data=[go.Bar(x=df1['发文日期'], y=df1['count'])])
    return fig


# display dfmonth in plotly
def display_dfmonth(df_month):
    fig = go.Figure(data=[go.Bar(x=df_month['month'], y=df_month['count'])])
    fig.update_layout(title='处罚数量统计', xaxis_title='月份', yaxis_title='处罚数量')
    st.plotly_chart(fig)


# display bar chart in plotly
def display_search_df(searchdf):
    fig = go.Figure(data=[go.Bar(x=searchdf['文件名称'], y=searchdf['count'])])
    fig.update_layout(title='搜索结果', xaxis_title='文件名称', yaxis_title='处罚数量')
    st.plotly_chart(fig)


def json2df(site_json):
    idls = []
    namels = []
    issueorgls = []
    filenols = []
    datels = []
    for i in range(20):
        idls.append(site_json['pageUtil']['pageList'][i]['lawWritId'])
        namels.append(site_json['pageUtil']['pageList'][i]['name'])
        issueorgls.append(site_json['pageUtil']['pageList'][i]['issueOrgName'])
        filenols.append(site_json['pageUtil']['pageList'][i]['fileno'])
        datels.append(site_json['pageUtil']['pageList'][i]['dsptDate'])

    eventdf = pd.DataFrame({
        'id': idls,
        'name': namels,
        'issueorg': issueorgls,
        'fileno': filenols,
        'date': datels
    })
    eventdf['date'] = eventdf['date'].astype(str).apply(
        lambda x: pd.to_datetime(x[:10], unit='s'))

    return eventdf


# get sumeventdf in page number range
def get_sumeventdf(start, end):
    resultls = []
    for pageno in range(start, end + 1):
        print('page:', pageno)
        url = BASE_URL + str(pageno)
        pp = requests.get(url, verify=False)
        ss = BeautifulSoup(pp.content, 'html.parser')
        ss_json = json.loads(ss.text)
        resultdf = json2df(ss_json)
        resultls.append(resultdf)
        print('OK')
        time.sleep(5)

    resultsum = pd.concat(resultls).reset_index(drop=True)
    # savedf(resultsum,'sumeventdf')
    return resultsum


# get current date and time string
def get_now():
    now = datetime.datetime.now()
    now_str = now.strftime('%Y%m%d%H%M%S')
    return now_str


# update sumeventdf
def update_sumeventdf(currentsum):
    oldsum = get_csrcsum()
    if oldsum.empty:
        oldidls = []
    else:
        oldidls = oldsum['id'].tolist()
    currentidls = currentsum['id'].tolist()
    # print('oldidls:',oldidls)
    # print('currentidls:', currentidls)
    # get current idls not in oldidls
    newidls = [x for x in currentidls if x not in oldidls]
    # print('newidls:', newidls)
    # newidls=list(set(currentidls)-set(oldidls))
    newdf = currentsum[currentsum['id'].isin(newidls)]
    # if newdf is not empty, save it
    if newdf.empty == False:
        newdf.reset_index(drop=True, inplace=True)
        nowstr = get_now()
        savename = 'sumevent' + nowstr
        savedf(newdf, savename)
    return newdf


def title2detail(sdtitlels, detail):
    detail['文件名称'] = sdtitlels[0].text
    detail['文号'] = sdtitlels[1].text.strip()
    detail['发文日期'] = sdtitlels[2].text.strip()
    detail['文书类型'] = sdtitlels[3].text.strip()
    detail['发文单位'] = sdtitlels[4].text.strip()
    detail['原文链接'] = sdtitlels[5].text.strip()


def law2detail(sdlawls, detail):
    lawdetaills = []
    for i in range(3, len(sdlawls)):
        try:
            span = sdlawls[i]['rowspan']
        except Exception as e:
            #         print(e)
            span = None
        if span:
            lawdetail = dict()
            itemls = []
            lawdetail['法律法规'] = sdlawls[i].text.strip()
            itemls = [
                sdlawls[j].text.strip()
                for j in range(i + 1, i + 1 + int(span))
            ]
            lawdetail['条文'] = itemls
            lawdetaills.append(lawdetail)
        else:
            pass
    detail['处理依据'] = lawdetaills


def people2detail(sdpeoplels, detail):
    peoplenum = (len(sdpeoplels) - 6) // 5

    pdetail = dict()
    pdetaills = []
    for pno in range(peoplenum):
        #     print(pno)
        pdetail = dict()
        pdetail['当事人类型'] = sdpeoplels[6 + pno * 5].text.strip()
        pdetail['当事人名称'] = sdpeoplels[6 + pno * 5 + 1].text.strip()
        pdetail['当事人身份'] = sdpeoplels[6 + pno * 5 + 2].text.strip()
        pdetail['违规类型'] = sdpeoplels[6 + pno * 5 + 3].text.strip()
        pdetail['处罚结果'] = sdpeoplels[6 + pno * 5 + 4].text.strip()
        pdetaills.append(pdetail)
    detail['当事人信息'] = pdetaills


def fact2detail(sdfactls, detail):
    detail['案情经过'] = sdfactls[0].text.replace('\u3000', '').replace('\n', '')


# get event detail
def get_eventdetail(eventsum):
    # outputfile = pencsrc+'sdresult_0-'
    idls = eventsum['id'].tolist()

    sdresultls = []
    count = 0
    for i in idls:
        print('id: ', i)
        print(count, 'begin')
        url = urldbase + str(i)
        dd = requests.get(url, verify=False)
        sd = BeautifulSoup(dd.content, 'html.parser')

        detail = dict()

        sdtitlels = sd.find_all(class_='text-left')

        sdlawls = sd.find_all('td', class_='text-center')

        sdpeoplels = sd.find_all(
            class_='table table-bordered table-condensed')[1].find_all('td')

        sdfactls = sd.find_all(class_='pre_law')

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
            savename = 'temp' + str(count + 1)
            savedf(sdresultdf, savename)
            print('batch:{} is ok'.format(batch))

        print(count, 'is ok')
        count = count + 1
        time.sleep(5)

    alldf = pd.DataFrame.from_dict(sdresultls)
    # if alldf is not empty, save it
    if alldf.empty == False:
        nowstr = get_now()
        savename = 'sdresult' + nowstr
        savedf(alldf, savename)
    return alldf
