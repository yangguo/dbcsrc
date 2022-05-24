from utils import get_csvdf, get_rulefolder,split_words
import pandas as pd
import streamlit as st

rulefolder = 'data/rules'
plcpath='data/rules/lawdfall0507.csv'
metapath='data/rules/lawmeta0517.csv'
dtlpath='data/rules/lawdtl0517.csv'


def get_samplerule(key_list, industry_choice):
    rulefolder = get_rulefolder(industry_choice)
    plcdf = get_csvdf(rulefolder)
    selectdf = plcdf[plcdf['监管要求'].isin(key_list)]
    tb_sample = selectdf[['监管要求', '结构', '条款']]
    return tb_sample.reset_index(drop=True)



def searchByName(search_text, industry_choice):
    rulefolder = get_rulefolder(industry_choice)
    plcdf = get_csvdf(rulefolder)
    plc_list = plcdf['监管要求'].drop_duplicates().tolist()

    choicels = []
    for plc in plc_list:
        if search_text in plc:
            choicels.append(plc)

    plcsam = get_samplerule(choicels, industry_choice)

    return plcsam, choicels



def get_lawdtlbyid(ids):
    metadf = pd.read_csv(metapath)
    metadf = metadf[metadf['secFutrsLawId'].isin(ids)]
    metacols=['secFutrsLawName', 'secFutrsLawNameAnno', 'wtAnttnSecFutrsLawName',
       'secFutrsLawVersion', 'fileno', 'body', 'bodyAgoCntnt']
    metadf=metadf[metacols]
    # fillna to empty
    metadf=metadf.fillna('')
    metadf.columns=['文件名称','文件名称注解','法律条文名称','法律条文版本','文号','正文','正文注解']
    metadf = metadf.reset_index(drop=True)
    dtldf=pd.read_csv(dtlpath)
    dtldf=dtldf[dtldf['id'].isin(ids)]
    dtlcol=['title', 'cntnt_x', 'cntnt_y']
    dtldf=dtldf[dtlcol]
    # fillna all columns with ''
    dtldf = dtldf.fillna('')
    # change column name
    dtldf.columns = ['标题', '内容', '法规条款']
    dtldf=dtldf.reset_index(drop=True)
    return metadf,dtldf



# get rule list by name,fileno,org,startdate,enddate
def get_rulelist_byname(name,fileno,org,startdate,enddate):
    plcdf=get_plcdf()
    # convert org list to str
    orgstr='|'.join(org)
    # name split words
    name_list=split_words(name)
    # fileno split words
    fileno_list=split_words(fileno)
    # if startdate is empty, set it to '1900-01-01'
    if startdate=='':
        startdate=pd.to_datetime('1900-01-01')
    # if enddate is empty, set it to '2100-01-01'
    if enddate=='':
        enddate=pd.to_datetime('2100-01-01')
    # search
    searchresult=plcdf[(plcdf['文件名称'].str.contains(name_list)) &
                          (plcdf['文号'].str.contains(fileno_list)) &
                            (plcdf['发文单位'].str.contains(orgstr)) &
                            (plcdf['发文日期']>=startdate) &
                            (plcdf['发文日期']<=enddate)]
    # reset index
    searchresult=searchresult.reset_index(drop=True)
    # sort by date
    searchresult=searchresult.sort_values(by='发文日期',ascending=False)
    return searchresult



# get plcdf
@st.cache(allow_output_mutation=True)
def get_plcdf():
    plcdf=pd.read_csv(plcpath)
    cols=['secFutrsLawName', 'fileno','lawPubOrgName','secFutrsLawVersion','secFutrsLawId','id']
    plcdf=plcdf[cols]
    # replace lawAthrtyStsCde mapping to chinese
    # plcdf['lawAthrtyStsCde']=plcdf['lawAthrtyStsCde'].astype(str).replace({'1':'现行有效','2':'已被修改','3':'已被废止'})
    # change column name
    plcdf.columns=['文件名称','文号','发文单位','发文日期','lawid','id']
    # convert column with format yyyymmdd to datetime
    plcdf['发文日期']=pd.to_datetime(plcdf['发文日期'],format='%Y%m%d',errors='coerce').dt.date
    plcdf=plcdf.reset_index(drop=True)
    return plcdf
