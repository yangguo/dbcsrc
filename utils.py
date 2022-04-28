from textrank4zh import TextRank4Keyword, TextRank4Sentence
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode

# get summary of text
def get_summary(text):
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=text, lower=True, source='all_filters')

    sumls = []
    for item in tr4s.get_key_sentences(num=3):
        sumls.append(item.sentence)
    summary = ''.join(sumls)
    return summary

def df2aggrid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination()
    gb.configure_side_bar()
    gb.configure_default_column(groupable=True,
                                value=True,
                                enableRowGroup=True,
                                aggFunc="sum",
                                editable=True)
    # gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    gridOptions = gb.build()
    ag_grid = AgGrid(df,
                    theme='dark',
                     gridOptions=gridOptions,
                     update_mode=GridUpdateMode.SELECTION_CHANGED,
                     enable_enterprise_modules=True)
    return ag_grid