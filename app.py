import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import streamlit as st

from dbcsrc import (  # count_by_month,; display_dfmonth,
    display_eventdetail,
    generate_lawdf,
    generate_peopledf,
    get_csrcdetail,
    get_csrcsum,
    get_eventdetail,
    get_lawdetail,
    get_peopledetail,
    get_sumeventdf,
    searchcsrc,
    searchlaw,
    searchpeople,
    update_sumeventdf,
)
from dbcsrc2 import (
    display_eventdetail2,
    display_summary2,
    get_csrc2detail,
    get_sumeventdf2,
    searchcsrc2,
    update_sumeventdf2,
)

# use wide layout
st.set_page_config(page_title="案例分析", layout="wide")


def main():

    menu = [
        # '案例分析',
        "案例搜索1",
        "案例搜索2",
        "案例更新1",
        "案例更新2",
    ]
    choice = st.sidebar.selectbox("选择", menu)

    if choice == "案例更新1":
        st.subheader("案例更新1")
        oldsum = get_csrcsum()
        # get length of old eventdf
        oldlen = len(oldsum)
        # get min and max date of old eventdf
        min_date = oldsum["date1"].min()
        max_date = oldsum["date1"].max()
        # use metric
        st.metric("原案例总数", oldlen)
        st.metric("原案例日期范围", f"{min_date} - {max_date}")

        with st.sidebar.form("更新案例"):
            # choose page start number and end number
            start_num = st.number_input("起始页", value=1, min_value=1, max_value=5)
            # convert to int
            start_num = int(start_num)
            end_num = st.number_input(
                "结束页", value=start_num, min_value=start_num, max_value=10
            )
            # convert to int
            end_num = int(end_num)
            # button to scrapy web
            sumeventbutton = st.form_submit_button("更新案例")

        if sumeventbutton:
            # get sumeventdf
            sumeventdf = get_sumeventdf(start_num, end_num)
            # update sumeventdf
            newsum = update_sumeventdf(sumeventdf)
            # get length of newsum
            sumevent_len = len(newsum)
            # display sumeventdf
            st.success(f"更新完成，共{sumevent_len}条案例列表")
            # get event detail
            eventdetail = get_eventdetail(newsum)
            # get length of eventdetail
            eventdetail_len = len(eventdetail)
            # display eventdetail
            st.success(f"更新完成，共{eventdetail_len}条案例详情")

        # convert eventdf to lawdf
        lawdfconvert = st.sidebar.button("处罚依据分析")
        if lawdfconvert:
            eventdf = get_csrcdetail()
            lawdf = generate_lawdf(eventdf)
            # savedf(lawdf,'lawdf')
            st.success("处罚依据分析完成")
            st.write(lawdf[:50])

        # convert eventdf to peopledf
        peopledfconvert = st.sidebar.button("处罚人员分析")
        if peopledfconvert:
            eventdf = get_csrcdetail()
            peopledf = generate_peopledf(eventdf)
            # savedf(peopledf,'peopledf')
            st.success("处罚人员分析完成")
            st.write(peopledf[:50])

    elif choice == "案例更新2":
        st.subheader("案例更新2")
        # display summary2
        sumdf2 = display_summary2()
        # get org list
        org_list = sumdf2["机构"].unique()

        with st.sidebar.form("更新案例"):
            # choose org name
            org_name = st.selectbox("选择机构", org_list)
            # choose page start number and end number
            start_num = st.number_input("起始页", value=1, min_value=1, max_value=20)
            # convert to int
            start_num = int(start_num)
            end_num = st.number_input(
                "结束页", value=start_num, min_value=start_num, max_value=20
            )
            # convert to int
            end_num = int(end_num)
            # button to scrapy web
            sumeventbutton = st.form_submit_button("更新案例")

        if sumeventbutton:
            # get sumeventdf
            sumeventdf2 = get_sumeventdf2(org_name, start_num, end_num)
            # display sumeventdf
            st.write(sumeventdf2[:50])
            # update sumeventdf
            newsum2 = update_sumeventdf2(sumeventdf2)
            # get length of newsum
            sumevent_len2 = len(newsum2)
            # display sumeventdf
            st.success(f"更新完成，共{sumevent_len2}条案例列表")

    elif choice == "案例搜索1":
        st.subheader("案例搜索1")
        # initialize search result in session state
        if "search_result_csrc" not in st.session_state:
            st.session_state["search_result_csrc"] = None

        # get csrc detail
        df = get_csrcdetail()
        # get max date
        max_date = df["发文日期"].max()
        # calculate the date five years before max_date
        five_years_before_max_date = max_date - pd.Timedelta(days=365 * 5)
        # choose search type
        search_type = st.sidebar.radio("搜索类型", ["案情经过", "处罚依据", "处罚人员"])
        if search_type == "案情经过":
            # get type list
            type_list = df["文书类型"].unique()

            with st.form("案情经过"):
                col1, col2 = st.columns(2)
                with col1:
                    # input filename keyword
                    filename_text = st.text_input("文件名")
                    # input date range
                    start_date = st.date_input("开始日期", value=five_years_before_max_date)
                    # input case keyword
                    case_text = st.text_input("案情经过")

                with col2:
                    # input org keyword
                    org_text = st.text_input("发文单位")
                    end_date = st.date_input("结束日期", value=max_date)
                    # get type
                    type_text = st.multiselect("文书类型", type_list)
                # search button
                searchbutton = st.form_submit_button("搜索")

            if searchbutton:
                if (
                    filename_text == ""
                    and org_text == ""
                    and case_text == ""
                    and type_text == []
                ):
                    st.error("请输入搜索条件")
                    st.stop()
                if type_text == []:
                    type_text = type_list
                # search by filename, date, org, case, type
                search_df = searchcsrc(
                    df,
                    filename_text,
                    start_date,
                    end_date,
                    org_text,
                    case_text,
                    type_text,
                )
                # set search result in session state
                st.session_state["search_result_csrc"] = search_df
            else:
                # get search result from session state
                search_df = st.session_state["search_result_csrc"]

        elif search_type == "处罚依据":
            lawdf = get_lawdetail()
            # get law list
            law_list = lawdf["法律法规"].unique()
            # get type list
            type_list = lawdf["文书类型"].unique()

            with st.form("处罚依据"):
                col1, col2 = st.columns(2)
                with col1:
                    # input filename keyword
                    filename_text = st.text_input("文件名")
                    # input date range
                    start_date = st.date_input("开始日期", value=five_years_before_max_date)
                    # get law
                    law_text = st.multiselect("法律法规", law_list)
                    # get type
                    type_text = st.multiselect("文书类型", type_list)
                with col2:
                    # input org keyword
                    org_text = st.text_input("发文单位")
                    end_date = st.date_input("结束日期", value=max_date)
                    # input article keyword
                    article_text = st.text_input("条文号")
                # search button
                searchbutton = st.form_submit_button("搜索")

            if searchbutton:
                if (
                    filename_text == ""
                    and org_text == ""
                    and article_text == ""
                    and law_text == []
                    and type_text == []
                ):
                    st.error("请输入搜索条件")
                    st.stop()
                if law_text == []:
                    law_text = law_list
                if type_text == []:
                    type_text = type_list
                # search by filename, start date,end date, org,law, article, type
                search_df = searchlaw(
                    lawdf,
                    filename_text,
                    start_date,
                    end_date,
                    org_text,
                    law_text,
                    article_text,
                    type_text,
                )
                # set search result in session state
                st.session_state["search_result_csrc"] = search_df
            else:
                # get search result from session state
                search_df = st.session_state["search_result_csrc"]

        elif search_type == "处罚人员":
            peopledf = get_peopledetail()
            # get people type list
            people_type_list = peopledf["当事人类型"].unique()
            # get people position list
            people_position_list = peopledf["当事人身份"].unique()
            # get penalty type list
            penalty_type_list = peopledf["违规类型"].unique()
            # get type list
            type_list = peopledf["文书类型"].unique()

            with st.form("处罚人员"):
                col1, col2 = st.columns(2)
                with col1:
                    # input filename keyword
                    filename_text = st.text_input("文件名")
                    # input date range
                    start_date = st.date_input("开始日期", value=five_years_before_max_date)
                    # get people name
                    people_name_text = st.text_input("当事人名称")

                    # get people type
                    people_type_text = st.multiselect("当事人类型", people_type_list)
                    # get penalty result
                    penalty_result_text = st.text_input("处罚结果")
                with col2:
                    # input org keyword
                    org_text = st.text_input("发文单位")
                    end_date = st.date_input("结束日期", value=max_date)
                    # get people position
                    people_position_text = st.multiselect("当事人身份", people_position_list)
                    # get penalty type
                    penalty_type_text = st.multiselect("违规类型", penalty_type_list)
                    # get type
                    type_text = st.multiselect("处罚类型", type_list)
                # search button
                searchbutton = st.form_submit_button("搜索")

            if searchbutton:
                if (
                    filename_text == ""
                    and org_text == ""
                    and people_name_text == ""
                    and people_type_text == []
                    and people_position_text == []
                    and penalty_type_text == []
                    and penalty_result_text == ""
                    and type_text == []
                ):
                    st.error("请输入搜索条件")
                    st.stop()
                if people_type_text == []:
                    people_type_text = people_type_list
                if people_position_text == []:
                    people_position_text = people_position_list
                if penalty_type_text == []:
                    penalty_type_text = penalty_type_list
                if type_text == []:
                    type_text = type_list

                # search by filename, start date,end date, org,people type, people name, people position, penalty type, penalty result, type
                search_df = searchpeople(
                    peopledf,
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
                )
                # set search result in session state
                st.session_state["search_result_csrc"] = search_df
            else:
                # get search result from session state
                search_df = st.session_state["search_result_csrc"]

        if search_df is None:
            st.error("请先搜索")
            st.stop()

        # display eventdetail
        display_eventdetail(search_df)

    elif choice == "案例搜索2":
        st.subheader("案例搜索2")
        # initialize search result in session state
        if "search_result_csrc2" not in st.session_state:
            st.session_state["search_result_csrc2"] = None

        # get csrc2 detail
        df = get_csrc2detail()
        # get org list
        org_list = df["机构"].unique()
        # get max date
        max_date = df["发文日期"].max()
        # get five years before max date
        five_years_before = max_date - pd.Timedelta(days=365 * 5)
        # choose search type
        search_type = st.sidebar.radio("搜索类型", ["案情经过"])
        if search_type == "案情经过":
            with st.form("案例搜索2"):
                col1, col2 = st.columns(2)
                with col1:
                    # input date range
                    start_date = st.date_input("开始日期", value=five_years_before)
                    # input filename keyword
                    filename_text = st.text_input("名称")
                    # input case keyword
                    case_text = st.text_input("案件关键词")
                with col2:
                    end_date = st.date_input("结束日期", value=max_date)
                    # input wenhao keyword
                    wenhao_text = st.text_input("文号")
                    # input org keyword from org list
                    org_text = st.multiselect("发文单位", org_list)
                    if org_text == []:
                        org_text = org_list
                # search button
                searchbutton = st.form_submit_button("搜索")
            if searchbutton:
                if (
                    filename_text == ""
                    and wenhao_text == ""
                    and case_text == ""
                    # and org_text == []
                ):
                    st.error("请输入搜索条件")
                    st.stop()
                # search by filename, date, wenhao, case, org
                search_df = searchcsrc2(
                    df,
                    filename_text,
                    start_date,
                    end_date,
                    wenhao_text,
                    case_text,
                    org_text,
                )
                # set search result in session state
                st.session_state["search_result_csrc2"] = search_df
            else:
                # get search result from session state
                search_df = st.session_state["search_result_csrc2"]

        if search_df is None:
            st.error("请先搜索")
            st.stop()

        # display eventdetail
        display_eventdetail2(search_df)


if __name__ == "__main__":
    main()
