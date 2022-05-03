from utils import get_csvdf, get_rulefolder

rulefolder = 'data/rules'


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
