import streamlit as st
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd

from dbcsrc import get_csrcdetail,searchcsrc,generate_lawdf,generate_peopledf,count_by_month,display_dfmonth,get_sumeventdf,update_sumeventdf,get_eventdetail
from dbcsrc import get_lawdetail,get_peopledetail,searchlaw,searchpeople
from dbcsrc import get_csrc2detail,searchcsrc2

def main():

    menu = ['案例更新', 
    # '案例分析', 
    '案例搜索1',
    '案例搜索2',]
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
            lawdf=generate_lawdf(eventdf)
            # savedf(lawdf,'lawdf')
            st.sidebar.success('处罚依据分析完成')
            st.write(lawdf[:50])

        # convert eventdf to peopledf
        peopledfconvert =st.sidebar.button('处罚人员分析')
        if peopledfconvert:
            eventdf=get_csrcdetail()
            peopledf=generate_peopledf(eventdf)
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
        
    elif choice == '案例搜索1':
        st.subheader('案例搜索1')
        # choose search type
        search_type = st.sidebar.selectbox('搜索类型', ['案情经过', '处罚依据', '处罚人员'])
        if search_type == '案情经过':
            # input filename keyword
            filename_text = st.sidebar.text_input('搜索文件名关键词')
            # get now date
            # now_date = pd.Timestamp.now()
            # get five years before now date
            # five_years_before = now_date - pd.Timedelta(days=365*5)
            # input date range
            start_date = st.sidebar.date_input('开始日期')# value=five_years_before)
            end_date = st.sidebar.date_input('结束日期')# value=now_date)
            # input org keyword
            org_text = st.sidebar.text_input('搜索机构关键词')
            # input case keyword
            case_text = st.sidebar.text_input('搜索案件关键词')
            df = get_csrcdetail()
            # get type list
            type_list = df['文书类型'].unique()
            # get type
            type_text = st.sidebar.multiselect('文书类型', type_list)
            if type_text == []:
                type_text = type_list
            # search button
            searchbutton = st.sidebar.button('搜索')
            if searchbutton:
                # search by filename, date, org, case, type
                search_df = searchcsrc(df, filename_text,start_date,end_date , org_text, case_text, type_text)
                total = len(search_df)
                st.sidebar.write('总数:', total)
                # count by month
                df_month = count_by_month(search_df)
                # draw plotly figure
                display_dfmonth(df_month)
                st.write(search_df)
        elif search_type == '处罚依据':
            # input filename keyword
            filename_text = st.sidebar.text_input('搜索文件名关键词')
            # get now date
            # now_date = pd.Timestamp.now()
            # get five years before now date
            # five_years_before = now_date - pd.Timedelta(days=365*5)
            # input date range
            start_date = st.sidebar.date_input('开始日期')# value=five_years_before)
            end_date = st.sidebar.date_input('结束日期')# value=now_date)
            # input org keyword
            org_text = st.sidebar.text_input('搜索机构关键词')
            df = get_lawdetail()
            # get law list
            law_list = df['法律法规'].unique()
            # get law
            law_text = st.sidebar.multiselect('法律法规', law_list)
            if law_text == []:
                law_text = law_list
            # input article keyword
            article_text = st.sidebar.text_input('搜索条文号')
            # get type list
            type_list = df['文书类型'].unique()
            # get type
            type_text = st.sidebar.multiselect('文书类型', type_list)
            if type_text == []:
                type_text = type_list
            # search button
            searchbutton = st.sidebar.button('搜索')
            if searchbutton:
                # search by filename, start date,end date, org,law, article, type
                search_df = searchlaw(df, filename_text,start_date,end_date , org_text,law_text,article_text,  type_text)
                total = len(search_df)
                st.sidebar.write('总数:', total)
                # count by month
                df_month = count_by_month(search_df)
                # draw plotly figure
                display_dfmonth(df_month)
                st.write(search_df)
        elif search_type == '处罚人员':
            # input filename keyword
            filename_text = st.sidebar.text_input('搜索文件名关键词')
            # get now date
            # now_date = pd.Timestamp.now()
            # get five years before now date
            # five_years_before = now_date - pd.Timedelta(days=365*5)
            # input date range
            start_date = st.sidebar.date_input('开始日期')# value=five_years_before)
            end_date = st.sidebar.date_input('结束日期')# value=now_date)
            # input org keyword
            org_text = st.sidebar.text_input('搜索机构关键词')
            
            df=get_peopledetail()
            # get people type list
            people_type_list = df['当事人类型'].unique()
            # get people type
            people_type_text = st.sidebar.multiselect('当事人类型', people_type_list)
            if people_type_text == []:
                people_type_text = people_type_list
            # get people name
            people_name_text = st.sidebar.text_input('搜索当事人名称')
            # get people position list
            people_position_list = df['当事人身份'].unique()
            # get people position
            people_position_text = st.sidebar.multiselect('当事人身份', people_position_list)
            if people_position_text == []:
                people_position_text = people_position_list
            # get penalty type list
            penalty_type_list = df['违规类型'].unique()
            # get penalty type
            penalty_type_text = st.sidebar.multiselect('违规类型', penalty_type_list)
            if penalty_type_text == []:
                penalty_type_text = penalty_type_list
            # get penalty result
            penalty_result_text = st.sidebar.text_input('搜索处罚结果')
            # get type list
            type_list = df['文书类型'].unique()
            # get type
            type_text = st.sidebar.multiselect('处罚类型', type_list)
            if type_text == []:
                type_text = type_list
            # search button
            searchbutton = st.sidebar.button('搜索')
            if searchbutton:
                # search by filename, start date,end date, org,people type, people name, people position, penalty type, penalty result, type
                search_df = searchpeople(df, filename_text,start_date,end_date , org_text,people_type_text, people_name_text, people_position_text, penalty_type_text, penalty_result_text, type_text)
                total = len(search_df)
                st.sidebar.write('总数:', total)
                # count by month
                df_month = count_by_month(search_df)
                # draw plotly figure
                display_dfmonth(df_month)
                st.write(search_df)
    elif choice == '案例搜索2':
        st.subheader('案例搜索2')
        # choose search type
        search_type = st.sidebar.selectbox('搜索类型', ['案情经过'])
        if search_type == '案情经过':
            # input filename keyword
            filename_text = st.sidebar.text_input('名称')
            # input date range
            start_date = st.sidebar.date_input('开始日期')# value=five_years_before)
            end_date = st.sidebar.date_input('结束日期')# value=now_date)
            # input wenhao keyword
            wenhao_text = st.sidebar.text_input('文号')
            # input case keyword
            case_text = st.sidebar.text_input('搜索案件关键词')
            df = get_csrc2detail()
            # search button
            searchbutton = st.sidebar.button('搜索')
            if searchbutton:
                # search by filename, date, wenhao, case
                search_df = searchcsrc2(df, filename_text,start_date,end_date , wenhao_text, case_text)
                total = len(search_df)
                st.sidebar.write('总数:', total)
                # count by month
                df_month = count_by_month(search_df)
                # draw plotly figure
                display_dfmonth(df_month)
                st.write(search_df)

if __name__ == '__main__':
    main()