import pandas as pd
import glob,os
import plotly.express as px
import plotly.graph_objs as go
from utils import get_summary
from ast import literal_eval

import requests
from bs4 import BeautifulSoup
import json
import time
# import matplotlib

import streamlit as st

pencsrc = 'csrc'
# mapfolder = 'data/temp/citygeo.csv'

BASE_URL='https://neris.csrc.gov.cn/falvfagui/multipleFindController/solrSearchWrit?pageNo='

# @st.cache
def get_csvdf(penfolder):
    files2 = glob.glob(penfolder+'**/sdresult*.csv', recursive=True)
    dflist = []
    # filelist = []
    for filepath in files2:
        # basename = os.path.basename(filepath)
        # filename = os.path.splitext(basename)[0]
        # print(filename)
        pendf = pd.read_csv(filepath)
        # newdf = pendf[['监管要求', '章节', '小节', '条款']]
        dflist.append(pendf)
        # filelist.append(filename)
    alldf = pd.concat(dflist, axis=0)
    return alldf

# @st.cache
def get_csrcdetail():
    # print(industry_choice)
    penfolder = pencsrc
    pendf = get_csvdf(penfolder)

    return pendf

# search by date range
def searchcsrc_date(df, start_date, end_date):
    col=['文件名称', '发文日期', '文书类型', '发文单位',  '案情经过']

    searchdf = df[(df['发文日期']>=start_date) & (df['发文日期']<=end_date)][col]
    
    count=len(searchdf)
    if count>100:
        searchdf1=searchdf[:100]
    else:
        searchdf1=searchdf

    searchdf1['案情经过']=searchdf1['案情经过'].apply(get_summary)

    return searchdf1,count


def searchcsrc(df, search_text):
    # df['datetime']=pd.to_datetime(df['date']).dt.date
    # col = ['索引号', '分类', '发布机构', '发文日期', '文号', '名称',
    #    '内容']
    col=['文件名称', '发文日期', '文书类型', '发文单位',  '案情经过']

    searchdf = df[(df['案情经过'].str.contains(search_text))][col]
    

    count=len(searchdf)
    if count>100:
        searchdf1=searchdf[:100]
    else:
        searchdf1=searchdf
    if search_text!='':
        searchdf1['案情经过']=searchdf1['案情经过'].apply(get_summary)
    else:
        searchdf1['案情经过']=searchdf1['案情经过'].apply(lambda x: x[:100]+'...')
    
    return searchdf1,count


# convert eventdf to lawdf
def get_lawdf(eventdf):
    law1=eventdf[['文件名称', '文号', '发文日期', '文书类型', '发文单位', '原文链接', '处理依据']]

    law1['处理依据']=law1['处理依据'].apply(literal_eval)

    law2=law1.explode('处理依据')

    law3=law2['处理依据'].apply(pd.Series)

    law4=pd.concat([law2,law3],axis=1)

    law5=law4.explode('条文')

    law6=law5.drop(['处理依据'],axis=1)

    lawdf=law6[['文件名称', '文号', '发文日期', '文书类型', '发文单位', '原文链接','法律法规', '条文']]

    # reset index
    lawdf.reset_index(drop=True, inplace=True)
    return lawdf

# convert eventdf to peopledf
def get_peopledf(eventdf):
    peopledf=eventdf[['文件名称', '文号', '发文日期', '文书类型', '发文单位', '原文链接', '当事人信息']]

    peopledf['当事人信息']=peopledf['当事人信息'].apply(literal_eval)

    peopledf2=peopledf.explode('当事人信息')

    peoplesp1=peopledf2['当事人信息'].apply(pd.Series)

    peopledf3=pd.concat([peopledf2,peoplesp1],axis=1)

    peopledf4=peopledf3[['文件名称', '文号', '发文日期', '文书类型', '发文单位', '原文链接','当事人类型',
        '当事人名称', '当事人身份',  '违规类型',  '处罚结果']]

    # reset index
    peopledf4.reset_index(drop=True, inplace=True)
    return peopledf4

def savedf(df, basename):
    savename = basename + '.csv'
    savepath = os.path.join(pencsrc, savename)
    df.to_csv(savepath)

# count the number of df by month
def count_by_month(df):
    df['发文日期']=pd.to_datetime(df['发文日期']).dt.date
    df['month']=df['发文日期'].apply(lambda x: x.strftime('%Y-%m'))
    df['count']=1
    df_month=df.groupby(['month']).count()
    # reset index
    df_month.reset_index(inplace=True)
    return df_month

def count_by_date(df):
    df['发文日期']=pd.to_datetime(df['发文日期']).dt.date
    df['发文日期']=df['发文日期'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df1=df.groupby('发文日期').count()
    df1.reset_index(inplace=True)
    df1.rename(columns={'文件名称':'count'}, inplace=True)
    # draw plotly bar chart
    fig=go.Figure(data=[go.Bar(x=df1['发文日期'], y=df1['count'])])
    return fig

# display dfmonth in plotly
def display_dfmonth(df_month):
    fig=go.Figure(data=[go.Bar(x=df_month['month'], y=df_month['count'])])
    fig.update_layout(title='处罚数量统计',
                    xaxis_title='月份',
                    yaxis_title='处罚数量')
    st.plotly_chart(fig)


def json2df(site_json):
    idls=[]
    namels=[]
    issueorgls=[]
    filenols=[]
    datels=[]
    for i in range(20):
        idls.append(site_json['pageUtil']['pageList'][i]['lawWritId'])
        namels.append(site_json['pageUtil']['pageList'][i]['name'])
        issueorgls.append(site_json['pageUtil']['pageList'][i]['issueOrgName'])
        filenols.append(site_json['pageUtil']['pageList'][i]['fileno'])
        datels.append(site_json['pageUtil']['pageList'][i]['dsptDate'])

    eventdf=pd.DataFrame({'id':idls,'name':namels,'issueorg':issueorgls,'fileno':filenols,'date':datels})
    eventdf['date']=eventdf['date'].astype(str).apply(lambda x: pd.to_datetime(x[:10],unit='s'))
    
    return eventdf

# get sumeventdf in page number range
def get_sumeventdf(start, end):
    resultls=[]
    for pageno in range(start,end+1):
        print('page:',pageno)
        url=BASE_URL+str(pageno)
        pp=requests.get(url, verify=False)
        ss = BeautifulSoup(pp.content, 'html.parser')
        ss_json=json.loads(ss.text)
        resultdf=json2df(ss_json)
        resultls.append(resultdf)
        print('OK')
        time.sleep(5)

    result3=pd.concat(resultls).reset_index(drop=True)
    return result3