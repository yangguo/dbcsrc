import pandas as pd
import streamlit as st
from dbcsrc import get_csvdf, display_search_df
from utils import df2aggrid

pencsrc2 = 'data/penalty/csrc2'


# @st.cache(suppress_st_warning=True)
def get_csrc2detail():
    pendf = get_csvdf(pencsrc2, 'csrcdtlall')
    # format date
    pendf['发文日期'] = pd.to_datetime(pendf['发文日期']).dt.date
    return pendf


# summary of csrc2
def display_summary2():
    # get old sumeventdf
    oldsum2 = get_csrc2detail()
    # get length of old eventdf
    oldlen2 = len(oldsum2)
    # get min and max date of old eventdf
    min_date2 = oldsum2['发文日期'].min()
    max_date2 = oldsum2['发文日期'].max()
    # use metric
    st.metric('原案例总数', oldlen2)
    st.metric('原案例日期范围', f'{min_date2} - {max_date2}')

    # sum max,min date and size by org
    sumdf2 = oldsum2.groupby('机构')['发文日期'].agg(['max', 'min',
                                                'count']).reset_index()
    sumdf2.columns = ['机构', '最近发文日期', '最早发文日期', '案例总数']
    # display
    st.markdown('#### 按机构统计')
    st.table(sumdf2)


#search by filename, date, wenhao,case
def searchcsrc2(df, filename, start_date, end_date, wenhao, case):
    col = ['名称', '发文日期', '文号', '内容', '链接']
    # convert date to datetime
    # df['发文日期'] = pd.to_datetime(df['发文日期']).dt.date
    searchdf = df[(df['名称'].str.contains(filename))
                  & (df['发文日期'] >= start_date) & (df['发文日期'] <= end_date) &
                  (df['文号'].str.contains(wenhao)) &
                  (df['内容'].str.contains(case))][col]
    # sort by date desc
    searchdf.sort_values(by=['发文日期'], ascending=False, inplace=True)
    # reset index
    searchdf.reset_index(drop=True, inplace=True)
    return searchdf


# display event detail
def display_eventdetail2(search_df):
    total = len(search_df)
    st.sidebar.metric('总数:', total)
    # count by month
    # df_month = count_by_month(search_df)
    # st.write(search_df)
    # get filename from path

    # draw plotly figure
    display_search_df(search_df)
    # st.table(search_df)
    data = df2aggrid(search_df)
    # display data
    selected_rows = data["selected_rows"]
    if selected_rows == []:
        st.error('请先选择查看案例')
        st.stop()
    # convert selected_rows to dataframe
    selected_rows_df = pd.DataFrame(selected_rows)

    # display event detail
    st.write('案情经过')
    # transpose
    selected_rows_df = selected_rows_df.T
    # set column name
    selected_rows_df.columns = ['案情经过']
    # display
    st.table(selected_rows_df)

    # display download button
    st.sidebar.download_button('下载搜索结果',
                               data=search_df.to_csv().encode('utf-8'),
                               file_name='搜索结果.csv')
