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
        # get csrc detail
        df=get_csrcdetail()
        # get max date
        max_date = df["发文日期"].max()
        # calculate the date five years before max_date
        five_years_before_max_date = max_date - pd.Timedelta(days=365*5)
        # choose search type
        search_type = st.sidebar.radio('搜索类型', ['案情经过', '处罚依据', '处罚人员'])
        if search_type == '案情经过':
            # get type list
            type_list = df['文书类型'].unique()

            with st.form('案情经过'):
                col1, col2 = st.columns(2)
                with col1:
                    # input filename keyword
                    filename_text = st.text_input('搜索文件名关键词')
                    # input date range
                    start_date = st.date_input('开始日期', value=five_years_before_max_date)
                    end_date = st.date_input('结束日期', value=max_date)

                with col2:
                    # input org keyword
                    org_text = st.text_input('搜索机构关键词')
                    # input case keyword
                    case_text = st.text_input('搜索案件关键词')
                    # get type
                    type_text = st.multiselect('文书类型', type_list)
                # search button
                searchbutton = st.form_submit_button('搜索')

            if searchbutton:
                if filename_text == '' and org_text == '' and case_text == '' and type_text == []:
                    st.error('请输入搜索条件')
                    return
                if type_text==[]:
                    type_text=type_list
                # search by filename, date, org, case, type
                search_df = searchcsrc(df, filename_text,start_date,end_date , org_text, case_text, type_text)
                total = len(search_df)
                st.sidebar.write('总数:', total)
                # count by month
                df_month = count_by_month(search_df)
                # draw plotly figure
                display_dfmonth(df_month)
                st.table(search_df)
                # display download button
                st.sidebar.download_button('下载搜索结果',data=search_df.to_csv(),file_name='搜索结果.csv')

        elif search_type == '处罚依据':
            lawdf = get_lawdetail()
            # get law list
            law_list = lawdf['法律法规'].unique()
            # get type list
            type_list = lawdf['文书类型'].unique()
 
            with st.form('处罚依据'):
                col1, col2 = st.columns(2)
                with col1:
                    # input filename keyword
                    filename_text = st.text_input('搜索文件名关键词')
                    # input date range
                    start_date = st.date_input('开始日期', value=five_years_before_max_date)
                    end_date = st.date_input('结束日期', value=max_date)
                    # input org keyword
                    org_text = st.text_input('搜索机构关键词')
                with col2:
                    # get law
                    law_text = st.multiselect('法律法规', law_list)
                    # input article keyword
                    article_text = st.text_input('搜索条文号')
                    # get type
                    type_text = st.multiselect('文书类型', type_list)
                # search button
                searchbutton = st.form_submit_button('搜索')

            if searchbutton:
                if filename_text == '' and org_text == '' and article_text == '' and law_text==[] and type_text == []:
                    st.error('请输入搜索条件')
                    return
                if law_text == []:
                    law_text = law_list
                if type_text == []:
                    type_text = type_list
                # search by filename, start date,end date, org,law, article, type
                search_df = searchlaw(lawdf, filename_text,start_date,end_date , org_text,law_text,article_text,  type_text)
                total = len(search_df)
                st.sidebar.write('总数:', total)
                # count by month
                df_month = count_by_month(search_df)
                # draw plotly figure
                display_dfmonth(df_month)
                st.table(search_df)
                # display download button
                st.sidebar.download_button('下载搜索结果',data=search_df.to_csv(),file_name='搜索结果.csv')

        elif search_type == '处罚人员':
            peopledf=get_peopledetail()
            # get people type list
            people_type_list = peopledf['当事人类型'].unique()
            # get people position list
            people_position_list = peopledf['当事人身份'].unique()
            # get penalty type list
            penalty_type_list = peopledf['违规类型'].unique()
            # get type list
            type_list = peopledf['文书类型'].unique()

            with st.form('处罚人员'):
                col1, col2 = st.columns(2)
                with col1:
                    # input filename keyword
                    filename_text = st.text_input('搜索文件名关键词')
                    # input date range
                    start_date = st.date_input('开始日期', value=five_years_before_max_date)
                    end_date = st.date_input('结束日期', value=max_date)
                    # input org keyword
                    org_text = st.text_input('搜索机构关键词')
                    
                    # get people type
                    people_type_text = st.multiselect('当事人类型', people_type_list)
                with col2:
                    # get people name
                    people_name_text = st.text_input('搜索当事人名称')
                    # get people position
                    people_position_text = st.multiselect('当事人身份', people_position_list)
                    # get penalty type
                    penalty_type_text = st.multiselect('违规类型', penalty_type_list)
                    # get penalty result
                    penalty_result_text = st.text_input('搜索处罚结果')
                    # get type
                    type_text = st.multiselect('处罚类型', type_list)
                # search button
                searchbutton = st.form_submit_button('搜索')

            if searchbutton:
                if filename_text == '' and org_text == '' and people_name_text == '' and people_type_text==[] and people_position_text == [] and penalty_type_text == [] and penalty_result_text == '' and type_text == []:
                    st.error('请输入搜索条件')
                    return
                if people_type_text == []:
                    people_type_text = people_type_list
                if people_position_text == []:
                    people_position_text = people_position_list
                if penalty_type_text == []:
                    penalty_type_text = penalty_type_list
                if type_text == []:
                    type_text = type_list

                # search by filename, start date,end date, org,people type, people name, people position, penalty type, penalty result, type
                search_df = searchpeople(peopledf, filename_text,start_date,end_date , org_text,people_type_text, people_name_text, people_position_text, penalty_type_text, penalty_result_text, type_text)
                total = len(search_df)
                st.sidebar.write('总数:', total)
                # count by month
                df_month = count_by_month(search_df)
                # draw plotly figure
                display_dfmonth(df_month)
                st.table(search_df)
                # display download button
                st.sidebar.download_button('下载搜索结果',data=search_df.to_csv(),file_name='搜索结果.csv')
    elif choice == '案例搜索2':
        st.subheader('案例搜索2')
        # get csrc2 detail
        df = get_csrc2detail()
        # get max date
        max_date = df['发文日期'].max()
        # get five years before max date
        five_years_before = max_date - pd.Timedelta(days=365*5)
        # choose search type
        search_type = st.sidebar.radio('搜索类型', ['案情经过'])
        if search_type == '案情经过':
            with st.form('案例搜索2'):
                col1, col2 = st.columns(2)
                with col1:
                    # input filename keyword
                    filename_text = st.text_input('名称')
                    # input date range
                    start_date = st.date_input('开始日期', value=five_years_before)
                    end_date = st.date_input('结束日期', value=max_date)
                with col2:
                    # input wenhao keyword
                    wenhao_text = st.text_input('文号')
                    # input case keyword
                    case_text = st.text_input('搜索案件关键词')
                # search button
                searchbutton = st.form_submit_button('搜索')
            if searchbutton:
                if filename_text == '' and wenhao_text == '' and case_text == '':
                    st.error('请输入搜索条件')
                    return
                # search by filename, date, wenhao, case
                search_df = searchcsrc2(df, filename_text,start_date,end_date , wenhao_text, case_text)
                total = len(search_df)
                st.sidebar.write('总数:', total)
                # count by month
                df_month = count_by_month(search_df)
                # draw plotly figure
                display_dfmonth(df_month)
                st.table(search_df)
                # display download button
                st.sidebar.download_button('下载搜索结果',data=search_df.to_csv(),file_name='搜索结果.csv')

if __name__ == '__main__':
    main()