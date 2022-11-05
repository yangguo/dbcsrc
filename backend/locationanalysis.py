import addressparser
import jionlp as jio
import pandas as pd


def short_to_province(short):
    S_TO_P_DICT = {
        "京": "北京市",
        "津": "天津市",
        "渝": "重庆市",
        "沪": "上海市",
        "冀": "河北省",
        "晋": "山西省",
        "辽": "辽宁省",
        "吉": "吉林省",
        "黑": "黑龙江省",
        "苏": "江苏省",
        "浙": "浙江省",
        "皖": "安徽省",
        "闽": "福建省",
        "赣": "江西省",
        "鲁": "山东省",
        "豫": "河南省",
        "鄂": "湖北省",
        "湘": "湖南省",
        "粤": "广东省",
        "琼": "海南省",
        "川": "四川省",
        "蜀": "四川省",
        "黔": "贵州省",
        "贵": "贵州省",
        "云": "云南省",
        "滇": "云南省",
        "陕": "陕西省",
        "秦": "陕西省",
        "甘": "甘肃省",
        "陇": "甘肃省",
        "青": "青海省",
        "台": "台湾省",
        "蒙": "内蒙古自治区",
        "桂": "广西壮族自治区",
        "宁": "宁夏回族自治区",
        "新": "新疆维吾尔自治区",
        "藏": "西藏自治区",
        "港": "香港特别行政区",
        "澳": "澳门特别行政区",
        "承": "承德",
        "厦": "厦门",
        "连": "大连",
    }
    return S_TO_P_DICT.get(short)


def df2part1loc(df, idcol, contentcol):
    txtls = []
    idls = []
    start = 0
    end = len(df)
    for i in range(start, end):
        id = df.iloc[i][idcol]
        content = df.iloc[i][contentcol]
        res = jio.parse_location(str(content), change2new=True, town_village=True)
        txtls.append(res)
        idls.append(id)
    tempdf = pd.DataFrame({"result": txtls, "id": idls})
    tempdf["province"] = tempdf["result"].apply(lambda x: x["province"])
    tempdf["city"] = tempdf["result"].apply(lambda x: x["city"])
    tempdf["county"] = tempdf["result"].apply(lambda x: x["county"])
    # tempdf1 = tempdf[[idcol, "province", "city", "county"]].drop_duplicates()
    return tempdf


def df2part2loc(df, idcol, contentcol):
    titls = df[contentcol].tolist()
    dfloc = addressparser.transform(titls, cut=False)
    df2 = pd.concat([df, dfloc], axis=1)
    d2 = df2[[idcol, "省", "市", "区"]]
    return d2


def df2location(df, idcol, titlecol, contentcol):
    df1 = df[[idcol, titlecol, contentcol]]

    # titlecol analysis
    d1 = df2part1loc(df1, idcol, titlecol)
    d2 = df2part2loc(df1, idcol, titlecol)
    d12 = pd.merge(d2, d1, on=idcol, how="left")
    d12.loc[d12["省"] == "", ["省", "市", "区"]] = d12.loc[
        d12["省"] == "", ["province", "city", "county"]
    ].values

    part1 = d12[d12["省"].notnull()][[idcol, "省", "市", "区"]].reset_index(drop=True)
    misidls = d12[d12["省"].isnull()][idcol].tolist()
    misdf = df1[df1[idcol].isin(misidls)].reset_index()

    # contentcol analysis on misdf
    d3 = df2part1loc(misdf, idcol, contentcol)
    d4 = df2part2loc(misdf, idcol, contentcol)
    d34 = pd.merge(d4, d3, on=idcol, how="left")
    d34.loc[d34["省"] == "", ["省", "市", "区"]] = d34.loc[
        d34["省"] == "", ["province", "city", "county"]
    ].values
    part2 = d34[[idcol, "省", "市", "区"]].reset_index(drop=True)

    allpart = pd.concat([part1, part2])
    allpart.columns = [idcol, "province", "city", "county"]
    # reset index
    allpart = allpart.reset_index(drop=True)
    return allpart
