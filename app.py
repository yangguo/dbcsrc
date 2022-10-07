from ast import literal_eval

import pandas as pd
import streamlit as st

from dbcsrc import (  # count_by_month,; display_dfmonth,
    display_eventdetail,
    display_summary,
    generate_lawdf,
    generate_peopledf,
    get_csrcdetail,
    get_eventdetail,
    get_lawdetail,
    get_peopledetail,
    get_sumeventdf,
    searchcsrc,
    searchlaw,
    searchpeople,
    update_sumeventdf,
)
from dbcsrc2 import (  # get_csrc2detail,
    combine_csrc2text,
    content_length_analysis,
    display_eventdetail2,
    display_summary2,
    download_attachment,
    download_csrcsum,
    generate_lawdf2,
    get_csrc2analysis,
    get_csrc2textupdate,
    get_csrcdownload,
    get_csrclenanalysis,
    get_sumeventdf2,
    remove_tempfiles,
    searchcsrc2,
    update_csrc2analysis,
    update_csrc2text,
    update_label,
    update_sumeventdf2,
)
from doc2text import docxconvertion

# use wide layout
st.set_page_config(page_title="案例分析", layout="wide")

tempdir = "data/penalty/csrc2/temp"


def main():

    menu = ["案例总数", "案例搜索1", "案例搜索2", "案例更新1", "案例更新2", "附件处理2", "案例分类2"]
    choice = st.sidebar.selectbox("选择", menu)
    if choice == "案例总数":
        st.subheader("典型案例总数")
        display_summary()
        st.subheader("完整案例总数")
        display_summary2()

    if choice == "案例更新1":
        st.subheader("案例更新1")
        display_summary()

        with st.sidebar.form("更新案例"):
            # choose page start number and end number
            start_num = st.number_input("起始页", value=1, min_value=1)
            # convert to int
            start_num = int(start_num)
            end_num = st.number_input("结束页", value=1)
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
        # download csrcsum
        download_csrcsum()
        # get org list
        org_list = sumdf2["机构"].unique()

        with st.sidebar.form("更新案例"):
            # choose org name
            org_name_ls = st.multiselect("选择机构", org_list)
            # if org name is blank list, then choose all
            if org_name_ls == []:
                org_name_ls = org_list
            # choose page start number and end number
            start_num = st.number_input("起始页", value=1, min_value=1)
            # convert to int
            start_num = int(start_num)
            end_num = st.number_input("结束页", value=1)
            # convert to int
            end_num = int(end_num)
            # button to scrapy web
            sumeventbutton = st.form_submit_button("更新案例")

        if sumeventbutton:
            for org_name in org_name_ls:
                # display org_name
                st.markdown("### 更新" + org_name + "案例")
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

        # button to refresh page
        refreshbutton = st.sidebar.button("刷新页面")
        if refreshbutton:
            st.experimental_rerun()

        # refresh data button
        refreshbutton = st.sidebar.button("刷新数据")
        if refreshbutton:
            update_csrc2analysis()
            st.success("数据更新完成")

        # convert eventdf to lawdf
        lawdfconvert = st.sidebar.button("处罚依据分析")
        if lawdfconvert:
            # eventdf = get_csrc2detail()
            eventdf = get_csrc2analysis()
            lawdf = generate_lawdf2(eventdf)
            # savedf(lawdf,'lawdf')
            st.success("处罚依据分析完成")
            st.write(lawdf[:50])

    elif choice == "附件处理2":

        # analysis content length
        content_len = st.sidebar.number_input("输入内容长度", value=10)
        content_len_btn = st.sidebar.button("附件分析")

        if content_len_btn:
            misdf = content_length_analysis(content_len)
            mislen = len(misdf)
            st.success("附件分析完成" + str(mislen) + "条案例")
            # st.write(misdf)

        lendf = get_csrclenanalysis()
        # if lendf is empty:
        if lendf.empty:
            st.error("先进行附件分析")
        else:
            st.markdown("#### 附件分析结果")
            st.write(lendf)

        with st.sidebar.form("下载附件"):
            # choose up number and down number
            up_num = st.number_input("起始位置", value=0, min_value=0)
            # convert to int
            up_num = int(up_num)
            down_num = st.number_input("结束位置", value=1)
            # convert to int
            down_num = int(down_num)
            # download attachment button
            download_att_btn = st.form_submit_button("下载附件")

        if download_att_btn:
            downdf = download_attachment(up_num, down_num)
            downlen = len(downdf)
            st.success("下载附件完成" + str(downlen) + "条案例")
            # st.write(downdf)

        # button for convert
        convert_button = st.sidebar.button("word格式转换")
        if convert_button:
            docxconvertion(tempdir)
            st.success("word格式转换完成")

        downdf = get_csrcdownload()
        # if lendf is empty:
        if downdf.empty:
            st.error("先下载附件")
        else:
            st.markdown("#### 附件下载结果")
            st.write(downdf)

        # button for convert
        convert_button = st.sidebar.button("文本抽取")
        if convert_button:
            txtupdf = update_csrc2text()
            txtuplen = len(txtupdf)
            st.success("文本抽取完成" + str(txtuplen) + "条案例")
            # st.write(dfnew)

        txtupdf = get_csrc2textupdate()
        if txtupdf.empty:
            st.error("先进行文本抽取")
        else:
            st.markdown("#### 文本抽取结果")
            st.write(txtupdf)

        # button for update text
        update_text_button = st.sidebar.button("更新文本")
        if update_text_button:
            combine_csrc2text()
            st.success("更新文本完成")

        # remove attachment button
        remove_attachment_btn = st.sidebar.button("删除附件")
        if remove_attachment_btn:
            remove_tempfiles()
            st.success("删除附件完成")

    elif choice == "案例分类2":
        df = get_csrc2analysis()
        # get columns
        columns = df.columns
        # choose columns
        select_column = st.sidebar.selectbox("选择分类字段", columns)
        # get selected column

        # text are for text
        # article_text = st.text_area("输入文本", value="")
        # text area for input label list
        labeltext = st.text_area("输入标签列表", value="")
        # radio button for choose multi label or single label
        multi_label = st.sidebar.checkbox("是否多标签", value=False, key="multi_label")

        # button for classify
        classify_button = st.sidebar.button("标签分类")
        if classify_button:
            if labeltext == "":
                st.error("输入标签列表")
            else:
                # convert to list
                labellist = literal_eval(labeltext)
                # if not null
                if len(labellist) != 0:
                    update_label(select_column, labellist, multi_label)
                    st.success("标签分类完成")
                else:
                    st.error("请输入标签列表")

    elif choice == "案例搜索1":
        st.subheader("案例搜索1")
        # initialize search result in session state
        if "search_result_csrc" not in st.session_state:
            st.session_state["search_result_csrc"] = None
        if "keywords_csrc1" not in st.session_state:
            st.session_state["keywords_csrc1"] = []

        # get csrc detail
        df = get_csrcdetail()
        # get length of old eventdf
        oldlen1 = len(df)
        # get min and max date of old eventdf
        min_date = df["发文日期"].min()
        max_date = df["发文日期"].max()
        # use metric
        # st.sidebar.write("案例总数", oldlen1)
        # st.sidebar.write("最晚发文日期", max_date)
        # st.sidebar.write("最早发文日期", min_date)
        # calculate the date one year before max_date
        one_year_before_max_date = max_date - pd.Timedelta(days=365)
        # choose search type
        search_type = st.sidebar.radio("搜索类型", ["案情经过", "处罚依据", "处罚人员"])
        # search_type = "处罚人员"
        if search_type == "案情经过":
            # get type list
            type_list = df["文书类型"].unique()

            with st.form("案情经过"):
                col1, col2 = st.columns(2)
                with col1:
                    # input filename keyword
                    filename_text = st.text_input("发文名称")
                    # input date range
                    start_date = st.date_input(
                        "开始日期", value=one_year_before_max_date, min_value=min_date
                    )
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
                    st.warning("请输入搜索条件")
                    # st.stop()
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
                    filename_text = st.text_input("发文名称")
                    # input date range
                    start_date = st.date_input(
                        "开始日期", value=one_year_before_max_date, min_value=min_date
                    )
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
                    st.warning("请输入搜索条件")
                    # st.stop()
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

            # get csrc detail
            csrcdf = get_csrcdetail()
            # get people detail
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
                    filename_text = st.text_input("发文名称")
                    # input date range
                    start_date = st.date_input(
                        "开始日期", value=one_year_before_max_date, min_value=min_date
                    )
                    # get people name
                    people_name_text = st.text_input("当事人名称")

                    # get people type
                    people_type_text = st.multiselect("当事人类型", people_type_list)
                    # get penalty result
                    penalty_result_text = st.text_input("处罚结果")
                    # input case keyword
                    case_text = st.text_input("案情经过")
                with col2:
                    # input org keyword
                    org_text = st.text_input("发文机构")
                    end_date = st.date_input("结束日期", value=max_date)
                    # get people position
                    people_position_text = st.multiselect("当事人身份", people_position_list)
                    # get penalty type
                    penalty_type_text = st.multiselect("违规类型", penalty_type_list)
                    # get type
                    type_text = st.multiselect("文书类型", type_list)
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
                    and case_text == ""
                ):
                    st.warning("请输入搜索条件")
                    # st.stop()
                if people_type_text == []:
                    people_type_text = people_type_list
                if people_position_text == []:
                    people_position_text = people_position_list
                if penalty_type_text == []:
                    penalty_type_text = penalty_type_list
                if type_text == []:
                    type_text = type_list

                # set search parameters in session state
                st.session_state["keywords_csrc1"] = [
                    filename_text,
                    start_date,
                    end_date,
                    org_text,
                    case_text,
                    type_text,
                ]

                # search by filename, date, org, case, type
                search_df1 = searchcsrc(
                    csrcdf,
                    filename_text,
                    start_date,
                    end_date,
                    org_text,
                    case_text,
                    type_text,
                )

                # search by filename, start date,end date, org,people type, people name, people position, penalty type, penalty result, type
                search_df2 = searchpeople(
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
                # get idls of search_df1
                idls1 = search_df1["id"].unique()
                # get idls of search_df2
                idls2 = search_df2["id"].unique()
                # get intersection of idls1 and idls2
                idls = list(set(idls1) & set(idls2))
                # get search result from search_df1
                search_df = search_df1[search_df1["id"].isin(idls)]

                # set search result in session state
                st.session_state["search_result_csrc"] = search_df
            else:
                # get search result from session state
                search_df = st.session_state["search_result_csrc"]

        if search_df is None:
            st.error("请先搜索")
            st.stop()

        if len(search_df) > 0:
            # display eventdetail
            display_eventdetail(search_df)
        else:
            st.warning("没有搜索结果")

    elif choice == "案例搜索2":
        st.subheader("案例搜索2")
        # initialize search result in session state
        if "search_result_csrc2" not in st.session_state:
            st.session_state["search_result_csrc2"] = None
        if "keywords_csrc2" not in st.session_state:  # 生成word的session初始化
            st.session_state["keywords_csrc2"] = []

        # get csrc2 detail
        # df = get_csrc2detail()
        df = get_csrc2analysis()
        # get org list
        org_list = df["机构"].unique()
        # get length of old eventdf
        oldlen2 = len(df)
        # get min and max date of old eventdf
        min_date2 = df["发文日期"].min()
        max_date2 = df["发文日期"].max()
        # use metric
        # st.sidebar.write("案例总数", oldlen2)
        # st.sidebar.write("最晚发文日期", max_date2)
        # st.sidebar.write("最早发文日期", min_date2)

        # get one year before max date
        one_year_before = max_date2 - pd.Timedelta(days=365)
        # choose search type
        # search_type = st.sidebar.radio("搜索类型", ["案情经过",'案情分类'])
        search_type = "案情经过"
        if search_type == "案情经过":
            with st.form("案例搜索2"):
                col1, col2 = st.columns(2)
                with col1:
                    # input date range
                    start_date = st.date_input(
                        "开始日期", value=one_year_before, min_value=min_date2
                    )
                    # input filename keyword
                    filename_text = st.text_input("发文名称")
                    # input case keyword
                    case_text = st.text_input("案件关键词")
                with col2:
                    end_date = st.date_input("结束日期", value=max_date2)
                    # input wenhao keyword
                    wenhao_text = st.text_input("文号")
                    # input org keyword from org list
                    org_text = st.multiselect("发文机构", org_list)
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
                    st.warning("请输入搜索条件")
                    # st.stop()
                # search by filename, date, wenhao, case, org
                st.session_state["keywords_csrc2"] = [
                    filename_text,
                    start_date,
                    end_date,
                    wenhao_text,
                    case_text,
                    org_text,
                ]
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

        # st.write("案例总数", len(search_df))
        if len(search_df) > 0:
            # display eventdetail
            display_eventdetail2(search_df)
        else:
            st.warning("没有搜索结果")


if __name__ == "__main__":
    main()
