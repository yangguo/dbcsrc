"""Web crawling module for CSRC case data extraction."""

import json
import os
import glob
import random
import time
import requests
from datetime import datetime

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
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Directory paths
pencsrc2 = "../data/penalty/csrc2"

# Organization ID mapping - each organization can have multiple IDs with names
# Structure: {"org_name": [{"id": "id_string", "name": "id_display_name"}, ...]}
org2id = {
    "山西": [{"id": "94bf3c5d8e5b4265a7916f19fb8b65ef", "name": "行政执法"},
    {"id": "085ed9d1e1dc437cb9945e961fb2f5a0", "name": "行政处罚决定"},
    {"id": "df89d13c12024339b008cb48dd820882", "name": "市场禁入决定"},
    {"id": "7de444553c114e0f9dd0b5de7733cf5f", "name": "行政监管措施"}
    ],
    "四川": [{"id": "88a03b16f60e4d16a62bd494d6530495", "name": "行政执法"},
    {"id": "6cd6f0ccbd2f49c6af32878d34c54ae6", "name": "行政处罚决定"},
    {"id": "901f0f0751dc4cfb83bc035a332fdc47", "name": "市场禁入决定"},
    {"id": "c8ec4969173148c19b6d52afc6500b49", "name": "行政监管措施"}
    ],
    "新疆": [{"id": "baa8f6e40657486bb0d7cc8525c857e6", "name": "行政执法"},
    {"id": "085ed9d1e1dc437cb9945e961fb2f5a0", "name": "行政处罚决定"},
    {"id": "95e320eada3b4b2a8a0b319f991d392c", "name": "行政监管措施"}
    ],
    "山东": [{"id": "4bd2094f91c14fcc84ffc4df0cd29d2b", "name": "行政执法"},
    {"id": "3a1acab4996548faa7532b957ebf4f8e", "name": "行政处罚决定"},
    {"id": "c73b329b9d114b8b850b789b7dd682b2", "name": "市场禁入决定"},
    {"id": "f8979e6c0b544e1992fea51d3c8739e3", "name": "行政监管措施"}
    ],
    "大连": [{"id": "d5247fa1384f4a46b17f2d33f025bdca", "name": "行政执法"},
    {"id": "fd0d6ccfc90640ec8af49b99d4af14f2", "name": "行政处罚决定"},
    {"id": "e69e418d713644018609ebea0ca891b3", "name": "市场禁入决定"},
    {"id": "fdf5c88757e04212a6dd66f396b21168", "name": "行政监管措施"}
    ],
    "湖北": [{"id": "a4478a6efb074823959f782bf7ad23c2", "name": "行政执法"},
    {"id": "f0a7388893fa4c15a2d6482510e2fb31", "name": "行政处罚决定"},
    {"id": "ef65fb100c394c049a776d9f55f91540", "name": "市场禁入决定"},
    {"id": "5a4e3e893a5f45d3a3f450cb8f96c635", "name": "行政监管措施"}
    ],
    "湖南": [{"id": "53d1eac8c4c145db8ca62c99bda5c058", "name": "行政执法"},
    {"id": "9182876b7fe841d3a2990998f5b756f3", "name": "行政处罚决定"},
    {"id": "2f087f7010fb43788a9015f21448447a", "name": "行政监管措施"}
    ],
    "陕西": [{"id": "00d7790e259b4d3dbaefe2935b1ec05f", "name": "行政执法"},
    {"id": "f0dad1ecc157416ea412e4a0608e04bd", "name": "行政处罚决定"},
    {"id": "f6c680055f9e43e7addf9493680a6112", "name": "行政监管措施"}
    ],
    "天津": [{"id": "882ff9eb82b346999ab45e9a597bc461", "name": "行政执法"},
    {"id": "8dce98784326429e9c97515b634723fe", "name": "行政处罚决定"},
    {"id": "f374ea9e12af484691ef888847fb6615", "name": "行政监管措施"}],
    "宁夏": [{"id": "9e622bf25828428996182a74dea32057", "name": "行政执法"},
    {"id": "45da89683b9d4a4c9657ebc12da2a73c", "name": "行政处罚决定"},
    {"id": "90ada2ec65a44e3797cbb858e62ba748", "name": "行政监管措施"}],
    "安徽": [{"id": "1d14687d160f4fe09642c86fc33501bd", "name": "行政执法"},
    {"id": "83fb5344bde849ea8973f3715a680a15", "name": "行政处罚决定"},
    {"id": "fe3b67dca3a14f908960d6d3a9bcea2b", "name": "市场禁入决定"},
    {"id": "5efe954d7f8049128e04a5141fc23da6", "name": "行政监管措施"}],
    "总部": [{"id": "29ae08ca97d44d6ea365874aa02d44f6", "name": "行政执法"},
    {"id": "e5a95ae5aea54c1f9dde255f21f67799", "name": "市场禁入"},
    {"id": "28de6b87eda140cb93de4dd10d11867d", "name": "行政处罚"},
    {"id": "0d9699d43e754cca958057f019998a5c", "name": "行政监管措施"},
    {"id": "17d5ff2fe43e488dba825807ae40d63f", "name": "行政处罚决定"},
    {"id": "3795869930ca4b70bf55469270a6e641", "name": "市场禁入决定"},
    {"id": "3ff8b60a78ab4c749387d99b9164ec6e", "name": "行政监管措施"}
    ],
    "北京": [{"id": "313639c4d05a43e5b86b1f356066f22d", "name": "行政执法"},
    {"id": "53be9cf2273744cda5c5780e0dded972","name":"行政处罚决定"},
    {"id": "8fae491ec565487491e08a1469476df5","name":"市场禁入决定"},
    {"id": "ea82afe8502d46aebea7346f0729dd85", "name":"行政监管措施"}
    ],
    "江苏": [{"id": "47d5896f8fc1486c89208dbdf00e937b", "name": "行政执法"},
    {"id": "b335834574a34e43874ef3dba68d5be5","name":"行政处罚决定"},
    {"id": "920da2d21d444b99829711457b624ab8","name":"市场禁入决定"},
    {"id": "9d6dfc15aa6144c8aea00f9878bdb1ce","name":"行政监管措施"}
    ],
    "黑龙江": [{"id": "19044145cb714a7cbd9cad1b2a810809", "name": "行政执法"},
    {"id": "370916bda2524acdb187191fbba13f44","name": "行政处罚决定"},
    {"id": "5ebef8919c8a409fb888701b1887034b","name": "市场禁入决定"},
    {"id": "e41f4e2fc9b34f5bab55489864313654","name": "行政监管措施"}
    ],
    "甘肃": [{"id": "7a78277d94df4057a9ad6cb9db7fca2a", "name": "行政执法"},
    {"id": "8e13b6a296324a60bc247a4a8a1df6a6","name": "行政处罚决定"},
    {"id": "ab8c66c4e8b24a169ad3b8f93d6d7fab","name": "行政监管措施"}
    ],
    "宁波": [{"id": "da83ebb77019448c912dbcdec571d3d7", "name": "行政执法"},
    {"id": "8e2d5a7bf989489fb9caa99a39bfaa70","name": "行政处罚决定"},
    {"id": "bf62ab47f6d24bfeadfd38847970904e","name": "市场禁入决定"},
    {"id": "fd693136e4cd4936a2ddb2255e5c1257","name": "行政监管措施"}
    ],
    "深圳": [{"id": "51840ec0710b4221b27cf3f7d52c0781", "name": "行政执法"},
    {"id": "a3d847e5be4d40a5baaf387be4a56e9b","name": "行政处罚决定"},
    {"id": "e20fe3b27d88473fbfced87a436a577e","name": "市场禁入决定"},
    {"id": "58959eb1bd68458088cac63f46a5fa40","name": "行政监管措施"}
    ],
    "河北": [
        {"id": "9b55d0917b8c45239e04815ad7d684dd", "name": "行政执法"},
        {"id": "e838879760e84c668062433e2cdbc389", "name": "行政处罚决定"},
        {"id": "03efc68cb7cf4e65a5ee1e4e96d19a69", "name": "市场禁入决定"},
        {"id": "4091867fdc664e169267aefc763c6d1d", "name": "行政监管措施"}
    ],
    "广东": [{"id": "a281797dea33433e93c30bcc4fa2e907", "name": "行政执法"},
    {"id": "02a93424320e46dea2631da827f96174", "name": "行政处罚决定"},
    {"id": "45c4bd0b8818479a9a55f7d68ddf1d64", "name": "市场禁入决定"},
    {"id": "29a1328dc824498b89eae8e63c38837f", "name": "行政监管措施"}
    ],

    "厦门": [{"id": "b5eabe7e6d0847ebae3ea9b1abd2a230", "name": "行政执法"},
    {"id": "0c1b68108fca4de0b240caaa32f901ed", "name": "行政处罚决定"},
    {"id": "e2498cacabda4ce19405bbf42de0c973", "name": "市场禁入决定"},
    {"id": "e3feac23205440e5b10ed81efa9dd94b", "name": "行政监管措施"}],
    "福建": [{"id": "ca335b3bbc51408da8a64f89bce67c95", "name": "行政执法"},
    {"id": "3df69151384a46cf8c8d11584cff5e94", "name": "行政处罚决定"},
    {"id": "4c9fdc7debfd49218f6fbdfaa804061f", "name": "市场禁入决定"},
    {"id": "e0d6aa56b3564735930b1cc078646d49", "name": "行政监管措施"}],
    "西藏": [{"id": "da2deae04a2a412e896d05d31b603804", "name": "行政执法"},
    {"id": "10f9fd2824c444ffafeaed5192682d55", "name": "行政处罚决定"},
    {"id": "5860856427aa48a98445caad530c723d", "name": "行政监管措施"}],
    "青岛": [{"id": "47f0814210b64db681be188da7f21b22", "name": "行政执法"},
    {"id": "e3e00f2b72414f1c9ea951eeb010a6cf", "name": "行政处罚决定"},
    {"id": "c0cb4dce3ac64e7fa57e20a86ba6c598", "name": "市场禁入决定"},
    {"id": "453f88a0ab9642f88908e41ceb78003d", "name": "行政监管措施"}],
    "贵州": [{"id": "1d15ee7b6389461eb45b7de8fc742615", "name": "行政执法"},
    {"id": "8bcfadbce6b74f178c37e6eafa9438b0", "name": "行政处罚决定"},
    {"id": "bcae0b7fe2e6473aa1d0b4b67f35b808", "name": "市场禁入决定"},
    {"id": "7f610f00f3b6435f9e7b730f125db5e6", "name": "行政监管措施"}],
    "河南": [{"id": "fa3997ef7b7549049b59451451e03623", "name": "行政执法"},
 {"id": "9724ed53f22a4333b91c65c349edaf48", "name": "行政处罚决定"},
    {"id": "b84c5f0139f346c2a4174f229074dcf3", "name": "市场禁入决定"},
    {"id": "92dfd6c412c2470bb93ed753c3404bc4", "name": "行政监管措施"}],
       "广西": [{"id": "cad5c39b4cae415fb576ceffc5d197ec", "name": "行政执法"},
 {"id": "f12807ebb0f948afaf7070627fadad7e", "name": "行政处罚决定"},
    {"id": "d5c5271fed23434094bf6ba3b5d4709b", "name": "市场禁入决定"},
    {"id": "9b57abde8c1541239b97224e26ba1da3", "name": "行政监管措施"}],
    "内蒙古": [{"id": "afc4ff6ea7644244ba66b79b296aaa36", "name": "行政执法"},
    {"id": "e4f2dbcdd85c4bac9a9e9a6f2d093d19", "name": "行政处罚决定"},
    {"id": "4c96602a020c4398adfc7123a48f2ee1", "name": "行政监管措施"}],
    "海南": [{"id": "aa24b402e1df434bbb68baa256fef9d4", "name": "行政执法"},
   {"id": "6d27bb42929c46ae8487a14f41fab43b", "name": "行政处罚决定"},
    {"id": "8bbdb3cb7e7c4c729fc28e2420073790", "name": "市场禁入决定"},
    {"id": "c42cd21f50b84d16a8614fdf1cc3e478", "name": "行政监管措施"}],
     "浙江": [{"id": "ac4e1875e53f4cb185195265376c8550", "name": "行政执法"},
   {"id": "441d2ae10ef240cbbcfca758a73356f2", "name": "行政处罚决定"},
    {"id": "183083760abf4395b964a8a8e3038716", "name": "市场禁入决定"},
    {"id": "83e130eb74f74d458c81027715955391", "name": "行政监管措施"}],
    "云南": [{"id": "0ce80bd1aaae430c8511b1a282e582f8", "name": "行政执法"},
  {"id": "99481e931fc94d13b8592449acb386a4", "name": "行政处罚决定"},
    {"id": "be1b3f4ddb264702b12f2e6795082ef9", "name": "市场禁入决定"},
    {"id": "ebb6ce034bb84594a0f0c06fccecde9b", "name": "行政监管措施"}],
     "辽宁": [{"id": "25ae72513b9a4e96a18823d4b1844f22", "name": "行政执法"},
  {"id": "94cc260b27d2430b8c39c21e4627cf2e", "name": "行政处罚决定"},
    {"id": "d1e464deb9ce4cdab2c1b40bede29c40", "name": "市场禁入决定"},
    {"id": "58df751f822a42a0acb1abd7471c71f8", "name": "行政监管措施"}],
    "吉林": [{"id": "ee414472c92443479e16c250e69840e1", "name": "行政执法"},
  {"id": "9a3520fd5ea644c2ad6e05acd0a05401", "name": "行政处罚决定"},
    {"id": "366f3072cbe143bebd533ef37f04eff5", "name": "行政监管措施"}],
    "江西": [{"id": "d7cae17b8d824e768ec1f7e86fd7f36a", "name": "行政执法"},
 {"id": "97691c60bc9a4b96af8b79df53b13b74", "name": "行政处罚决定"},
    {"id": "9520f36bb312424bbeffb08c4542d83c", "name": "行政监管措施"}],
     "重庆": [{"id": "c28e1398b3054af694b769291a1c8952", "name": "行政执法"},
{"id": "febe5cf9074b4ce6a52fd3d34d7a5cba", "name": "行政处罚决定"},
    {"id": "55dbc14f9bea476bb09743d5f1c8c842", "name": "行政监管措施"}],
     "上海": [{"id": "0dd09598f7f2470fb269732ec5b8ddc8", "name": "行政执法"},
  {"id": "c8318fc200764e38b30116c2d5f72b4b", "name": "行政处罚决定"},
    {"id": "df44b3a122c6406db6e6f1dcd02c90c9", "name": "市场禁入决定"},
    {"id": "9ebc4198232e496e8bebf1b1bb1778ef", "name": "行政监管措施"}],
    "青海": [{"id": "1747a405d9a6437e8688f25c48c6205a", "name": "行政执法"},
 {"id": "439a663f89484376be17d4dcae953254", "name": "行政处罚决定"},
    {"id": "dcd6e6dc74d94b0fbc46812b9721fc13", "name": "市场禁入决定"},
    {"id": "989b26dfc95a4188b64b3f9d4895ddd9", "name": "行政监管措施"}],
 
}


# Platform detection utilities removed - no longer needed with webdriver-manager
# ChromeDriverManager automatically handles platform-specific driver management


def get_now():
    """Get current timestamp string."""
    now = datetime.now()
    now_str = now.strftime("%Y%m%d%H%M%S")
    return now_str


def get_csvdf(penfolder, beginwith, include_filename=False):
    """Get concatenated dataframe from CSV files."""
    import os
    pattern = os.path.join(penfolder, beginwith + "*.csv")
    files2 = glob.glob(pattern, recursive=False)
    dflist = []
    for filepath in files2:
        try:
            pendf = get_pandas().read_csv(filepath, encoding='utf-8-sig')
            
            # Add filename column if requested
            if include_filename and not pendf.empty:
                filename = os.path.basename(filepath)
                pendf['source_filename'] = filename
            
            dflist.append(pendf)
        except Exception as e:
            # Error reading file
            pass
    
    if len(dflist) > 0:
        df = get_pandas().concat(dflist)
        df.reset_index(drop=True, inplace=True)
    else:
        df = get_pandas().DataFrame()
    return df


def get_csrc2detail():
    """Get CSRC detail data."""
    pendf = get_csvdf(pencsrc2, "csrcdtlall")
    if not pendf.empty:
        # Format date - handle both timestamp and date formats
        if "发文日期" in pendf.columns:
            # First try to convert timestamps (numeric values) to datetime
            def convert_date(date_val):
                if get_pandas().isna(date_val) or date_val == "":
                    return ""
                
                # If it's a numeric timestamp, convert it
                try:
                    # Check if it's a numeric timestamp (seconds or milliseconds)
                    if str(date_val).replace('.', '').isdigit():
                        timestamp = float(date_val)
                        # If timestamp is in milliseconds (> 1e10), convert to seconds
                        if timestamp > 1e10:
                            timestamp = timestamp / 1000
                        return get_pandas().to_datetime(timestamp, unit='s').date()
                    else:
                        # Try to parse as regular date string
                        return get_pandas().to_datetime(date_val, errors='coerce').date()
                except (ValueError, TypeError, OverflowError):
                    # If conversion fails, return empty string
                    return ""
            
            pendf["发文日期"] = pendf["发文日期"].apply(convert_date)
        # Fill na
        pendf = pendf.fillna("")
    return pendf


def get_url_backend(orgname, selected_ids=None):
    """Get URLs for organization (returns list of URLs for multiple IDs).
    
    Args:
        orgname (str): Organization name
        selected_ids (list, optional): List of specific IDs to use. If None, uses all IDs for the organization.
    
    Returns:
        list: List of URLs for the specified IDs
    """
    if orgname not in org2id:
        raise ValueError(f"Organization '{orgname}' not found in org2id mapping")
    
    id_list = org2id[orgname]
    
    # Filter by selected IDs if provided
    if selected_ids:
        id_list = [item for item in id_list if item["id"] in selected_ids]
    
    urls = []
    for item in id_list:
        url = (
            "http://www.csrc.gov.cn/searchList/"
            + item["id"]
            + "?_isAgg=true&_isJson=true&_pageSize=10&_template=index&_rangeTimeGte=&_channelName=&page="
        )
        urls.append(url)
    return urls


def savedf_backend(df, basename):
    """Save dataframe to CSV."""
    savename = basename + ".csv"
    savepath = os.path.join(pencsrc2, savename)
    os.makedirs(os.path.dirname(savepath), exist_ok=True)
    df.to_csv(savepath, index=False, escapechar="\\", encoding='utf-8-sig')


def get_sumeventdf_backend(orgname, start, end, selected_ids=None):
    """Backend implementation of get_sumeventdf2.
    
    Args:
        orgname (str): Organization name
        start (int): Start page number
        end (int): End page number
        selected_ids (list, optional): List of specific IDs to use. If None, uses all IDs for the organization.
        
    Returns:
        pd.DataFrame: Scraped case data
    """
    if not isinstance(start, int) or not isinstance(end, int):
        raise ValueError("Start and end must be integers")
    
    if start > end:
        raise ValueError("Start page must be less than or equal to end page")
    
    if start < 1:
        raise ValueError("Start page must be greater than 0")
    
    # Calculate estimated time
    total_pages = end - start + 1
    estimated_time = total_pages * 3  # Rough estimate: 3 seconds per page
    # Starting to scrape pages for organization
    
    resultls = []
    errorls = []
    count = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for pageno in range(start, end + 1):
        progress = ((pageno - start) / total_pages) * 100
        # Processing page
        url_list = get_url_backend(orgname, selected_ids)
        
        # Process each URL (one for each ID) for this page
        for base_url in url_list:
            url = base_url + str(pageno)
            
            # Retry logic for network requests
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Increase timeout and add retry logic
                    dd = requests.get(url, headers=headers, verify=False, timeout=60)
                    dd.raise_for_status()
                    break  # Success, exit retry loop
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        # Max retries reached for page
                        errorls.append(url)
                        break
                    else:
                        # Retry for page
                        time.sleep(2)  # Wait before retry
                        continue
                except Exception as e:
                    # Non-retryable error for page
                    errorls.append(url)
                    break
            
            if retry_count >= max_retries:
                continue  # Skip this URL and move to next
                
            try:
                sd = BeautifulSoup(dd.content, "html.parser")
                json_text = str(sd.text).strip()
                json_data = json.loads(json_text, strict=False)
                
                if "data" not in json_data or "results" not in json_data["data"]:
                    # No data found for page
                    continue
                    
                itemls = json_data["data"]["results"]

                titlels = []
                wenhaols = []
                datels = []
                snls = []
                urlls = []
                docls = []

                for idx, item in enumerate(itemls):
                    try:
                        if "domainMetaList" not in item or not item["domainMetaList"]:
                            # Missing domainMetaList for item
                            continue
                            
                        headerls = item["domainMetaList"][0]["resultList"]
                        headerdf = get_pandas().DataFrame(headerls)
                        
                        # Extract fields with error handling
                        wenhao_rows = headerdf[headerdf["key"] == "wh"]
                        wenhao = wenhao_rows["value"].iloc[0] if not wenhao_rows.empty else ""
                        
                        sn_rows = headerdf[headerdf["key"] == "syh"]
                        sn = sn_rows["value"].iloc[0] if not sn_rows.empty else ""
                        
                        title = item.get("subTitle", "")
                        url_item = item.get("url", "")
                        date = item.get("publishedTimeStr", "")
                        
                        try:
                            doc = (
                                item.get("contentHtml", "")
                                .replace("\r", "")
                                .replace("\n", "")
                                .replace("\u2002", "")
                                .replace("\u3000", "")
                            )
                        except Exception as e:
                            # Error processing contentHtml for item
                            doc = (
                                item.get("content", "")
                                .replace("\r", "")
                                .replace("\n", "")
                                .replace("\u2002", "")
                                .replace("\u3000", "")
                            )

                        titlels.append(title)
                        wenhaols.append(wenhao)
                        datels.append(date)
                        snls.append(sn)
                        urlls.append(url_item)
                        docls.append(doc)
                    except Exception as e:
                        # Error processing item
                        continue

                if titlels:  # Only create DataFrame if we have data
                    csrceventdf = get_pandas().DataFrame({
                        "名称": titlels,
                        "文号": wenhaols,
                        "发文日期": datels,
                        "序列号": snls,
                        "链接": urlls,
                        "内容": docls,
                    })
                    csrceventdf["机构"] = orgname
                    resultls.append(csrceventdf)

            except requests.exceptions.HTTPError as e:
                if hasattr(dd, 'status_code') and dd.status_code == 403:
                    # 403 Forbidden error - authentication or IP blocking issue
                    pass
                errorls.append(url)
            except json.JSONDecodeError as e:
                # JSON decode error
                errorls.append(url)
            except Exception as e:
                # General error occurred
                errorls.append(url)

        # Save temporary results every 5 pages (moved outside the URL loop)
        mod = (count + 1) % 5
        if mod == 0 and count > 0 and resultls:
            tempdf = get_pandas().concat(resultls)
            savename = "temp-" + orgname + "-0-" + str(count + 1)
            savedf_backend(tempdf, savename)

        # Reduced wait time to improve performance (moved outside the URL loop)
        wait = random.randint(1, 5)
        time.sleep(wait)
        count += 1

    if resultls:
        resultsum = get_pandas().concat(resultls).reset_index(drop=True)
        savedf_backend(resultsum, "tempall-" + orgname)
        # Scraping completed
        return resultsum
    else:
        # Scraping completed
        return get_pandas().DataFrame()


def get_csrc2analysis():
    """Get CSRC analysis data including source filename"""
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    pencsrc2_abs = os.path.join(project_root, "data", "penalty", "csrc2")
    
    pendf = get_csvdf(pencsrc2_abs, "csrc2analysis", include_filename=True)
    if not pendf.empty:
        # Format date with error handling
        try:
            pendf["发文日期"] = get_pandas().to_datetime(pendf["发文日期"], format='mixed', errors='coerce').dt.date
        except Exception as e:
            # Date formatting warning
            # Try alternative format
            pendf["发文日期"] = get_pandas().to_datetime(pendf["发文日期"], errors='coerce').dt.date
        # Fill na
        pendf = pendf.fillna("")
    return pendf

def savetemp(df, basename):
    """Save dataframe to temp directory
    
    For files like csrcmiscontent, it will look for existing timestamped files
    and update them instead of creating new ones.
    """
    # Use absolute path to ensure it works from any working directory
    import os
    import glob
    
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
    
    os.makedirs(tempdir, exist_ok=True)
    
    # For csrcmiscontent, look for existing timestamped files
    if basename == "csrcmiscontent":
        # Look for existing csrcmiscontent*.csv files
        existing_files = glob.glob(os.path.join(tempdir, "csrcmiscontent*.csv"))
        if existing_files:
            # Update the most recent file (last in sorted order)
            existing_files.sort()
            savepath = existing_files[-1]
            df.to_csv(savepath, index=False, encoding='utf-8-sig')
            return
    
    # Default behavior: use basename.csv
    savename = basename + ".csv"
    savepath = os.path.join(tempdir, savename)
    df.to_csv(savepath, index=False, encoding='utf-8-sig')

def content_length_analysis(length, download_filter):
    """Analyze content length and filter data
    
    Args:
        length (int): Maximum content length (filters for content <= length)
        download_filter (str): Filter for document names containing this text
    
    Returns:
        list: Records with content length <= specified length
    """
    try:
        eventdf = get_csrc2analysis()
        
        if eventdf.empty:
            return []
        
        # Ensure required columns exist
        if "内容" not in eventdf.columns:
            eventdf["内容"] = ""
        if "名称" not in eventdf.columns:
            eventdf["名称"] = ""
        if "filename" not in eventdf.columns:
            eventdf["filename"] = ""
        
        eventdf["内容"] = eventdf["内容"].str.replace(
            r"\r|\n|\t|\xa0|\u3000|\s|\xa0", "", regex=True
        )
        eventdf.loc[:, "len"] = eventdf["内容"].astype(str).apply(len)
        
        # Filter for content length <= specified length (short content)
        misdf = eventdf[eventdf["len"] <= length]

        # filter by download_filter - include records that contain the filter
        # Treat 'none' as no filter (same as None or empty string)
        if download_filter and download_filter.lower() != 'none' and "名称" in misdf.columns:
            misdf = misdf[misdf["名称"].str.contains(download_filter, case=False, na=False)]

        # get df by column name - only include columns that exist
        available_cols = ["发文日期", "名称", "链接", "内容", "len", "filename", "source_filename"]
        select_cols = [col for col in available_cols if col in misdf.columns]
        misdf1 = misdf[select_cols]
        
        # sort by 发文日期 if column exists
        if "发文日期" in misdf1.columns:
            misdf1 = misdf1.sort_values(by="发文日期", ascending=False)
        
        # reset index
        misdf1.reset_index(drop=True, inplace=True)
        
        # Convert numpy data types to native Python types for JSON serialization
        # Use .loc to avoid SettingWithCopyWarning
        for col in misdf1.columns:
            if misdf1[col].dtype == 'int64':
                misdf1.loc[:, col] = misdf1[col].astype(int)
            elif misdf1[col].dtype == 'float64':
                misdf1.loc[:, col] = misdf1[col].astype(float)
            elif misdf1[col].dtype == 'object':
                misdf1.loc[:, col] = misdf1[col].astype(str)
        
        # Convert DataFrame to dict for JSON serialization
        result = misdf1.to_dict('records')
        
        # savename
        savename = "csrclenanalysis"
        # save misdf
        try:
            savetemp(misdf1, savename)
        except Exception as save_error:
            pass
        
        return result
        
    except Exception as e:
        return []


def update_sumeventdf_backend(currentsum):
    """Backend implementation of update_sumeventdf2.
    
    Args:
        currentsum (pd.DataFrame): Current scraped data
        
    Returns:
        pd.DataFrame: New records not in existing data
    """
    if currentsum.empty:
        # No current data to update
        return get_pandas().DataFrame()
        
    oldsum2 = get_csrc2detail()
    if oldsum2.empty:
        oldidls = []
    else:
        oldidls = oldsum2["链接"].tolist()
    
    currentidls = currentsum["链接"].tolist()
    newidls = [x for x in currentidls if x not in oldidls]
    newdf = currentsum[currentsum["链接"].isin(newidls)]
    
    if not newdf.empty:
        newdf.reset_index(drop=True, inplace=True)
        nowstr = get_now()
        savename = "csrcdtlall" + nowstr
        savedf_backend(newdf, savename)
        # Saved new records to csrcdtlall
        
        # Also update csrc2analysis files
        update_csrc2analysis_backend()
        
    else:
        # No new records to save
        pass
    
    # Convert DataFrame to dict for JSON serialization
    if not newdf.empty:
        # Convert numpy data types to native Python types
        # Use .loc to avoid SettingWithCopyWarning
        for col in newdf.columns:
            if newdf[col].dtype == 'int64':
                newdf.loc[:, col] = newdf[col].astype(int)
            elif newdf[col].dtype == 'float64':
                newdf.loc[:, col] = newdf[col].astype(float)
            elif newdf[col].dtype == 'object':
                newdf.loc[:, col] = newdf[col].astype(str)
        return newdf.to_dict('records')
    else:
        return []


def update_csrc2analysis_backend():
    """Backend implementation to create/update csrc2analysis files.
    
    This function reads from csrcdtlall files and creates csrc2analysis files
    by combining new data with existing analysis data. New records are saved
    as a timestamped file (csrc2analysis+timedate).
    """
    try:
        # Get new detailed data from csrcdtlall files
        newdf = get_csrc2detail()
        if newdf.empty:
            # No detail data found for analysis update
            return
            
        newurlls = newdf["链接"].tolist()
        
        # Get existing analysis data
        olddf = get_csrc2analysis()
        if olddf.empty:
            oldurlls = []
        else:
            oldurlls = olddf["链接"].tolist()
        
        # Find new URLs not in existing analysis data (based on URL deduplication)
        newidls = [x for x in newurlls if x not in oldurlls]
        upddf = newdf[newdf["链接"].isin(newidls)]
        
        # If there are new records, save them as a new timestamped file
        if not upddf.empty:
            # Only save new records (not combining with old data)
            upddf.reset_index(drop=True, inplace=True)
            
            # Generate timestamped filename
            nowstr = get_now()
            savename = f"csrc2analysis{nowstr}"
            savedf_backend(upddf, savename)
            # Saved new csrc2analysis records with timestamp
        else:
            # No new records to add to csrc2analysis
            pass
            
    except Exception as e:
        # Error updating csrc2analysis
        pass


# Chrome and ChromeDriver discovery functions removed - no longer needed
# webdriver-manager automatically handles driver discovery and installation

def get_chrome_driver():
    """Get Chrome WebDriver with automatic ChromeDriver management."""
    print("Initializing Chrome driver...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-javascript")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    
    try:
        # Use ChromeDriverManager for automatic ChromeDriver management
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✓ Chrome driver initialized successfully")
        return driver
    except Exception as e:
        # Fallback to system chromedriver if automatic management fails
        try:
            driver = webdriver.Chrome(options=options)
            print("✓ Chrome driver initialized using system chromedriver")
            return driver
        except Exception as fallback_error:
            error_msg = (
                f"Failed to initialize Chrome driver. ChromeDriverManager error: {e}\n"
                f"System chromedriver fallback error: {fallback_error}\n\n"
                "Please ensure Chrome is installed and you have internet connectivity for automatic ChromeDriver setup.\n"
                "Alternatively, install ChromeDriver manually and add it to your system PATH."
            )
            raise Exception(error_msg)


def get_csrclenanalysis():
    """Get CSRC length analysis dataframe including source filename."""
    # Define tempdir using absolute path
    import os
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
    
    pendf = get_csvdf(tempdir, "csrclenanalysis", include_filename=True)
    if not pendf.empty:
        pendf = pendf.fillna("")
    return pendf


def download_attachment(down_list=None, progress_callback=None):
    """Download attachments from CSRC URLs with progress tracking.
    
    Args:
        down_list: List of indices to download. If None, downloads all.
        progress_callback: Optional callback function to report progress (current, total, message)
    """
    if down_list is None:
        down_list = []
    
    # Define tempdir using absolute path
    import os
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
    
    # get csrclenanalysis df
    lendf = get_csrclenanalysis()
    # get misls from url
    misls = lendf["链接"].tolist()
    # get submisls by index list
    if down_list:
        submisls = [misls[i] for i in down_list if i < len(misls)]
    else:
        submisls = misls

    total_downloads = len(submisls)
    if total_downloads == 0:
        print("No URLs to download")
        return get_pandas().DataFrame()

    print(f"Starting download of {total_downloads} attachments...")
    if progress_callback:
        progress_callback(0, total_downloads, "Initializing download...")

    resultls = []
    errorls = []
    successful_downloads = 0
    failed_downloads = 0

    driver = get_chrome_driver()

    for i, url in enumerate(submisls):
        current_progress = i + 1
        progress_percent = (current_progress / total_downloads) * 100
        
        # Progress bar display
        bar_length = 30
        filled_length = int(bar_length * current_progress // total_downloads)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        print(f"\rProgress: |{bar}| {progress_percent:.1f}% ({current_progress}/{total_downloads}) - Processing attachment {current_progress}", end='', flush=True)
        
        if progress_callback:
            progress_callback(current_progress, total_downloads, f"Downloading attachment {current_progress}/{total_downloads}")

        try:
            driver.get(url)
            # Wait for the page to load and the specific element to be present
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "detail-news"))
            )

            page_source = driver.page_source
            sd = BeautifulSoup(page_source, "html.parser")

            dirpath = url.rsplit("/", 1)[0]
            savename = ""
            text = ""
            
            try:
                filepath = sd.find_all("div", class_="detail-news")[0].a["href"]
                datapath = dirpath + "/" + filepath
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Referer": url,
                }
                
                # Ensure tempdir exists
                os.makedirs(tempdir, exist_ok=True)
                
                # Add timeout and retry logic for file download
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        file_response = requests.get(datapath, headers=headers, stream=True, timeout=30)
                        file_response.raise_for_status()
                        
                        # Get file size for progress tracking
                        file_size = int(file_response.headers.get('content-length', 0))
                        
                        savename = get_now() + os.path.basename(datapath)
                        filename = os.path.join(tempdir, savename)
                        
                        downloaded_size = 0
                        with open(filename, "wb") as f:
                            for chunk in file_response.iter_content(1024 * 1024 * 2):
                                if chunk:
                                    f.write(chunk)
                                    downloaded_size += len(chunk)
                                    
                                    # Update progress for large files
                                    if file_size > 0:
                                        file_progress = (downloaded_size / file_size) * 100
                                        if file_progress % 25 == 0:  # Update every 25%
                                            print(f" - File progress: {file_progress:.0f}%", end='', flush=True)
                        
                        # Verify file was downloaded successfully
                        if os.path.exists(filename) and os.path.getsize(filename) > 0:
                            successful_downloads += 1
                            break
                        else:
                            raise Exception("Downloaded file is empty or doesn't exist")
                            
                    except Exception as download_error:
                        retry_count += 1
                        if retry_count >= max_retries:
                            failed_downloads += 1
                            break
                        else:
                            time.sleep(2)  # Wait before retry
                            
            except Exception as e:
                # Try to extract text content if file download fails
                failed_downloads += 1
                try:
                    text = sd.find_all("div", class_="detail-news")[0].text
                except Exception:
                    text = "Failed to extract text content"
                    
            datals = {"url": url, "filename": savename, "text": text}
            df = get_pandas().DataFrame(datals, index=[0])
            resultls.append(df)
            
        except Exception as e:
            # Error processing URL
            errorls.append(url)
            failed_downloads += 1

        # Save temporary results every 10 downloads
        if (current_progress) % 10 == 0 and resultls:
            tempdf = get_pandas().concat(resultls)
            temp_savename = "temp-" + str(current_progress)
            savetemp(tempdf, temp_savename)

        # Reduced wait time for better user experience
        wait = random.randint(1, 3)
        time.sleep(wait)

    # Final progress update
    print(f"\n✓ Download completed: {successful_downloads} successful, {failed_downloads} failed, {len(errorls)} errors")
    
    if progress_callback:
        progress_callback(total_downloads, total_downloads, f"Completed: {successful_downloads} successful, {failed_downloads} failed")

    driver.quit()

    if resultls:
        misdf = get_pandas().concat(resultls)
        savecsv = "csrcmiscontent" + get_now()
        # reset index
        misdf.reset_index(drop=True, inplace=True)
        savetemp(misdf, savecsv)
        
        print(f"Results saved to: {savecsv}.csv")
        print(f"Total records processed: {len(misdf)}")
        
        return misdf
    else:
        print("No results to save")
        return get_pandas().DataFrame()

# Helper functions for managing organization IDs
def add_org_id(orgname, new_id, name=None):
    """Add a new ID to an existing organization or create a new organization entry.
    
    Args:
        orgname (str): Organization name
        new_id (str): New ID to add
        name (str, optional): Display name for the ID. If None, defaults to orgname + "局"
    """
    if name is None:
        name = f"{orgname}局"
    
    new_entry = {"id": new_id, "name": name}
    
    if orgname in org2id:
        # Check if ID already exists
        existing_ids = [item["id"] for item in org2id[orgname]]
        if new_id not in existing_ids:
            org2id[orgname].append(new_entry)
    else:
        org2id[orgname] = [new_entry]


def remove_org_id(orgname, id_to_remove):
    """Remove an ID from an organization.
    
    Args:
        orgname (str): Organization name
        id_to_remove (str): ID to remove
    """
    if orgname in org2id:
        org2id[orgname] = [item for item in org2id[orgname] if item["id"] != id_to_remove]
        # Remove the organization entry if no IDs left
        if not org2id[orgname]:
            del org2id[orgname]


def get_org_ids(orgname):
    """Get all IDs for an organization.
    
    Args:
        orgname (str): Organization name
        
    Returns:
        list: List of ID dictionaries with 'id' and 'name' keys
    """
    return org2id.get(orgname, [])


def get_org_id_strings(orgname):
    """Get all ID strings for an organization.
    
    Args:
        orgname (str): Organization name
        
    Returns:
        list: List of ID strings only
    """
    return [item["id"] for item in org2id.get(orgname, [])]


def list_all_orgs():
    """List all organizations and their ID counts.
    
    Returns:
        dict: Dictionary with organization names as keys and ID counts as values
    """
    return {org: len(ids) for org, ids in org2id.items()}


def get_all_org_data():
    """Get complete organization data structure for frontend.
    
    Returns:
        dict: Complete org2id structure
    """
    return org2id

# Example usage of the updated org2id structure:
# 
# # Add multiple IDs for an organization
# add_org_id("北京", "new_id_123456")
# add_org_id("北京", "another_id_789012")
# 
# # Get all IDs for an organization
# beijing_ids = get_org_ids("北京")
# print(f"Beijing IDs: {beijing_ids}")
# 
# # List all organizations and their ID counts
# org_counts = list_all_orgs()
# print(f"Organization ID counts: {org_counts}")
# 
# # The get_url_backend function now returns a list of URLs
# beijing_urls = get_url_backend("北京")
# print(f"Beijing URLs: {beijing_urls}")

def get_sumeventdf_backend_selective(orgname, start, end, selected_ids=None):
    """Backend implementation with selective ID support.
    
    Args:
        orgname (str): Organization name
        start (int): Start page number
        end (int): End page number
        selected_ids (list, optional): List of specific IDs to scrape. If None, scrapes all IDs.
        
    Returns:
        pd.DataFrame: Scraped case data
    """
    if not isinstance(start, int) or not isinstance(end, int):
        raise ValueError("Start and end must be integers")
    
    if start > end:
        raise ValueError("Start page must be less than or equal to end page")
    
    if start < 1:
        raise ValueError("Start page must be greater than 0")
    
    # Calculate estimated time
    total_pages = end - start + 1
    estimated_time = total_pages * 3  # Rough estimate: 3 seconds per page
    
    resultls = []
    errorls = []
    count = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for pageno in range(start, end + 1):
        progress = ((pageno - start) / total_pages) * 100
        # Processing page
        url_list = get_url_backend(orgname, selected_ids)
        
        # Process each URL (one for each selected ID) for this page
        for base_url in url_list:
            url = base_url + str(pageno)
            
            # Retry logic for network requests
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Increase timeout and add retry logic
                    dd = requests.get(url, headers=headers, verify=False, timeout=60)
                    dd.raise_for_status()
                    break  # Success, exit retry loop
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        # Max retries reached for page
                        errorls.append(url)
                        break
                    else:
                        # Retry for page
                        time.sleep(2)  # Wait before retry
                        continue
                except Exception as e:
                    # Non-retryable error for page
                    errorls.append(url)
                    break
            
            if retry_count >= max_retries:
                continue  # Skip this URL and move to next
                
            try:
                sd = BeautifulSoup(dd.content, "html.parser")
                json_text = str(sd.text).strip()
                json_data = json.loads(json_text, strict=False)
                
                if "data" not in json_data or "results" not in json_data["data"]:
                    # No data found for page
                    continue
                    
                itemls = json_data["data"]["results"]

                titlels = []
                wenhaols = []
                datels = []
                snls = []
                urlls = []
                docls = []

                for idx, item in enumerate(itemls):
                    try:
                        if "domainMetaList" not in item or not item["domainMetaList"]:
                            # Missing domainMetaList for item
                            continue
                            
                        headerls = item["domainMetaList"][0]["resultList"]
                        headerdf = get_pandas().DataFrame(headerls)
                        
                        # Extract fields with error handling
                        wenhao_rows = headerdf[headerdf["key"] == "wh"]
                        wenhao = wenhao_rows["value"].iloc[0] if not wenhao_rows.empty else ""
                        
                        sn_rows = headerdf[headerdf["key"] == "syh"]
                        sn = sn_rows["value"].iloc[0] if not sn_rows.empty else ""
                        
                        title = item.get("subTitle", "")
                        url_item = item.get("url", "")
                        date = item.get("publishedTimeStr", "")
                        
                        try:
                            doc = (
                                item.get("contentHtml", "")
                                .replace("\r", "")
                                .replace("\n", "")
                                .replace("\u2002", "")
                                .replace("\u3000", "")
                            )
                        except Exception as e:
                            # Error processing contentHtml for item
                            doc = (
                                item.get("content", "")
                                .replace("\r", "")
                                .replace("\n", "")
                                .replace("\u2002", "")
                                .replace("\u3000", "")
                            )

                        titlels.append(title)
                        wenhaols.append(wenhao)
                        datels.append(date)
                        snls.append(sn)
                        urlls.append(url_item)
                        docls.append(doc)
                    except Exception as e:
                        # Error processing item
                        continue

                if titlels:  # Only create DataFrame if we have data
                    csrceventdf = get_pandas().DataFrame({
                        "名称": titlels,
                        "文号": wenhaols,
                        "发文日期": datels,
                        "序列号": snls,
                        "链接": urlls,
                        "内容": docls,
                    })
                    csrceventdf["机构"] = orgname
                    resultls.append(csrceventdf)

            except requests.exceptions.HTTPError as e:
                if hasattr(dd, 'status_code') and dd.status_code == 403:
                    # 403 Forbidden error - authentication or IP blocking issue
                    pass
                errorls.append(url)
            except json.JSONDecodeError as e:
                # JSON decode error
                errorls.append(url)
            except Exception as e:
                # General error occurred
                errorls.append(url)

        # Save temporary results every 5 pages (moved outside the URL loop)
        mod = (count + 1) % 5
        if mod == 0 and count > 0 and resultls:
            tempdf = get_pandas().concat(resultls)
            savename = "temp-" + orgname + "-0-" + str(count + 1)
            savedf_backend(tempdf, savename)

        # Reduced wait time to improve performance (moved outside the URL loop)
        wait = random.randint(1, 5)
        time.sleep(wait)
        count += 1

    if resultls:
        resultsum = get_pandas().concat(resultls).reset_index(drop=True)
        savedf_backend(resultsum, "tempall-" + orgname)
        # Scraping completed
        return resultsum
    else:
        # Scraping completed
        return get_pandas().DataFrame()