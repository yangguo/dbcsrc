import openai
import os
import json

# Lazy import pandas to reduce memory usage during startup
pd = None

def get_pandas():
    """Lazy import pandas to reduce startup memory usage"""
    global pd
    if pd is None:
        try:
            import pandas as pandas_module
            pd = pandas_module
        except ImportError as e:
            print(f"Failed to import pandas: {e}")
            raise
    return pd

# Initialize OpenAI client
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

# Get model name from environment or use default
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


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


def llm_parse_location(text):
    """Use LLM to parse location information from text"""
    try:
        prompt = f"""
        Extract location information from the following Chinese text and return a JSON object with province, city, and county fields.
        If any field cannot be determined, set it to null.
        
        Text: {text}
        
        Return format:
        {{
            "province": "province name or null",
            "city": "city name or null", 
            "county": "county/district name or null"
        }}
        
        Only return the JSON object, no other text.
        """
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a location extraction expert for Chinese addresses. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        # Error in LLM location parsing
        return {"province": None, "city": None, "county": None}

def df2part1loc(df, idcol, contentcol):
    txtls = []
    idls = []
    start = 0
    end = len(df)
    for i in range(start, end):
        id = df.iloc[i][idcol]
        content = df.iloc[i][contentcol]
        res = llm_parse_location(str(content))
        txtls.append(res)
        idls.append(id)
    tempdf = get_pandas().DataFrame({"result": txtls, "id": idls})
    tempdf["province"] = tempdf["result"].apply(lambda x: x["province"])
    tempdf["city"] = tempdf["result"].apply(lambda x: x["city"])
    tempdf["county"] = tempdf["result"].apply(lambda x: x["county"])
    # tempdf1 = tempdf[[idcol, "province", "city", "county"]].drop_duplicates()
    return tempdf


def llm_transform_addresses(address_list):
    """Use LLM to transform a list of addresses into structured location data"""
    try:
        addresses_text = "\n".join([f"{i+1}. {addr}" for i, addr in enumerate(address_list)])
        
        prompt = f"""
        Parse the following Chinese addresses and extract province (省), city (市), and district/county (区) information.
        Return a JSON array where each object corresponds to the address at the same index.
        If any field cannot be determined, set it to empty string "".
        
        Addresses:
        {addresses_text}
        
        Return format (JSON array):
        [
            {{"省": "province name or empty", "市": "city name or empty", "区": "district name or empty"}},
            {{"省": "province name or empty", "市": "city name or empty", "区": "district name or empty"}}
        ]
        
        Only return the JSON array, no other text.
        """
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an address parsing expert for Chinese addresses. Return only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        result = json.loads(response.choices[0].message.content)
        return get_pandas().DataFrame(result)
    except Exception as e:
        # Error in LLM address transformation
        # Return empty dataframe with expected columns
        return get_pandas().DataFrame([{"省": "", "市": "", "区": ""} for _ in address_list])

def df2part2loc(df, idcol, contentcol):
    titls = df[contentcol].tolist()
    dfloc = llm_transform_addresses(titls)
    df2 = get_pandas().concat([df, dfloc], axis=1)
    d2 = df2[[idcol, "省", "市", "区"]]
    return d2


def df2location(df, idcol, titlecol, contentcol):
    df1 = df[[idcol, titlecol, contentcol]]

    # titlecol analysis
    d1 = df2part1loc(df1, idcol, titlecol)
    d2 = df2part2loc(df1, idcol, titlecol)
    d12 = get_pandas().merge(d2, d1, on=idcol, how="left")
    d12.loc[d12["省"] == "", ["省", "市", "区"]] = d12.loc[
        d12["省"] == "", ["province", "city", "county"]
    ].values

    part1 = d12[d12["省"].notnull()][[idcol, "省", "市", "区"]].reset_index(drop=True)
    misidls = d12[d12["省"].isnull()][idcol].tolist()
    misdf = df1[df1[idcol].isin(misidls)].reset_index()

    # contentcol analysis on misdf
    d3 = df2part1loc(misdf, idcol, contentcol)
    d4 = df2part2loc(misdf, idcol, contentcol)
    d34 = get_pandas().merge(d4, d3, on=idcol, how="left")
    d34.loc[d34["省"] == "", ["省", "市", "区"]] = d34.loc[
        d34["省"] == "", ["province", "city", "county"]
    ].values
    part2 = d34[[idcol, "省", "市", "区"]].reset_index(drop=True)

    allpart = get_pandas().concat([part1, part2])
    allpart.columns = [idcol, "province", "city", "county"]
    # reset index
    allpart = allpart.reset_index(drop=True)
    return allpart
