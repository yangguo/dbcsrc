import streamlit as st
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd

from dbcsrc import get_csrcdetail,searchcsrc,get_lawdf,get_peopledf,count_by_month,display_dfmonth,get_sumeventdf,update_sumeventdf,get_eventdetail

def main():

    menu = ['案例更新', '案例分析', '案例搜索']
    choice = st.sidebar.selectbox("选择", menu)

    if choice == '案例更新':
        st.subheader('案例更新')
        # st.write('案例更新')
        # choose page start number and end number
        start_num = st.sidebar.number_input('起始页', value=1, min_value=1, max_value=5)
        # convert to int
        start_num = int(start_num)
        end_num = st.sidebar.number_input('结束页', value=start_num, min_value=start_num, max_value=10)
        # convert to int
        end_num = int(end_num)
        # button to scrapy web
        sumeventbutton = st.sidebar.button('更新案例')
        if sumeventbutton:
            # get sumeventdf
            sumeventdf = get_sumeventdf(start_num, end_num)
            # get length of sumeventdf
            # length = len(sumeventdf)
            # display length
            # st.write(f'更新了{length}条案例')
            # update sumeventdf
            newsum=update_sumeventdf(sumeventdf)            
            # get length of newsum
            sumevent_len = len(newsum)
            # display sumeventdf
            st.sidebar.success(f'更新完成，共{sumevent_len}条案例列表')
            # get event detail
            eventdetail = get_eventdetail(newsum)
            # get length of eventdetail
            eventdetail_len = len(eventdetail)
            # display eventdetail
            st.sidebar.success(f'更新完成，共{eventdetail_len}条案例详情')
        
        # convert eventdf to lawdf
        lawdfconvert =st.sidebar.button('处罚依据分析')
        if lawdfconvert:
            eventdf=get_csrcdetail()
            lawdf=get_lawdf(eventdf)
            # savedf(lawdf,'lawdf')
            st.sidebar.success('处罚依据分析完成')
            st.write(lawdf[:50])

        # convert eventdf to peopledf
        peopledfconvert =st.sidebar.button('处罚人员分析')
        if peopledfconvert:
            eventdf=get_csrcdetail()
            peopledf=get_peopledf(eventdf)
            # savedf(peopledf,'peopledf')
            st.sidebar.success('处罚人员分析完成')
            st.write(peopledf[:50])

    elif choice == '案例分析':
        st.subheader('案例分析')
        st.write('案例分析')
        eventdf = get_csrcdetail()
        st.write(eventdf[:50])

        df_month=count_by_month(eventdf)

        # get min and max date
        min_date = eventdf['发文日期'].min()
        max_date = eventdf["发文日期"].max()
        # calculate the date five years before max_date
        five_years_before_max_date = max_date - pd.Timedelta(days=365*5)
        # filter by month range and display
        start_date = st.sidebar.date_input('开始日期',value=five_years_before_max_date)
        end_date = st.sidebar.date_input('结束日期', value=max_date)
        # datetime to x.strftime('%Y-%m')
        start_month = start_date.strftime('%Y-%m')
        end_month = end_date.strftime('%Y-%m')
        if start_month > end_month:
            st.error('开始日期不能大于结束日期')
            return
        # filter by month range
        df_month = df_month[(df_month['month'] >= start_month) & (df_month['month'] <= end_month)]
        # st.write(df_month)
        # draw plotly figure
        display_dfmonth(df_month)
        


    elif choice == '案例搜索':
        st.subheader('案例搜索')
        search_text = st.sidebar.text_input('搜索案例关键词')

        df = get_csrcdetail()
        st.write("处罚列表")

        sampledf, total = searchcsrc(df, search_text)
        # total = len(sampledf)
        st.sidebar.write('总数:', total)
        # pd.set_option('colwidth',40)

        st.table(sampledf)

if __name__ == '__main__':
    main()