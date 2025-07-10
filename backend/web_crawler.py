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

# Organization ID mapping
org2id = {
    "山西": "94bf3c5d8e5b4265a7916f19fb8b65ef",
    "四川": "88a03b16f60e4d16a62bd494d6530495",
    "新疆": "baa8f6e40657486bb0d7cc8525c857e6",
    "山东": "4bd2094f91c14fcc84ffc4df0cd29d2b",
    "大连": "d5247fa1384f4a46b17f2d33f025bdca",
    "湖北": "a4478a6efb074823959f782bf7ad23c2",
    "湖南": "53d1eac8c4c145db8ca62c99bda5c058",
    "陕西": "00d7790e259b4d3dbaefe2935b1ec05f",
    "天津": "882ff9eb82b346999ab45e9a597bc461",
    "宁夏": "9e622bf25828428996182a74dea32057",
    "安徽": "1d14687d160f4fe09642c86fc33501bd",
    "总部": "29ae08ca97d44d6ea365874aa02d44f6",
    "北京": "313639c4d05a43e5b86b1f356066f22d",
    "江苏": "47d5896f8fc1486c89208dbdf00e937b",
    "黑龙江": "19044145cb714a7cbd9cad1b2a810809",
    "甘肃": "7a78277d94df4057a9ad6cb9db7fca2a",
    "宁波": "da83ebb77019448c912dbcdec571d3d7",
    "深圳": "51840ec0710b4221b27cf3f7d52c0781",
    "河北": "9b55d0917b8c45239e04815ad7d684dd",
    "广东": "a281797dea33433e93c30bcc4fa2e907",
    "厦门": "b5eabe7e6d0847ebae3ea9b1abd2a230",
    "福建": "ca335b3bbc51408da8a64f89bce67c95",
    "西藏": "da2deae04a2a412e896d05d31b603804",
    "青岛": "47f0814210b64db681be188da7f21b22",
    "贵州": "1d15ee7b6389461eb45b7de8fc742615",
    "河南": "fa3997ef7b7549049b59451451e03623",
    "广西": "cad5c39b4cae415fb576ceffc5d197ec",
    "内蒙古": "afc4ff6ea7644244ba66b79b296aaa36",
    "海南": "aa24b402e1df434bbb68baa256fef9d4",
    "浙江": "ac4e1875e53f4cb185195265376c8550",
    "云南": "0ce80bd1aaae430c8511b1a282e582f8",
    "辽宁": "25ae72513b9a4e96a18823d4b1844f22",
    "吉林": "ee414472c92443479e16c250e69840e1",
    "江西": "d7cae17b8d824e768ec1f7e86fd7f36a",
    "重庆": "c28e1398b3054af694b769291a1c8952",
    "上海": "0dd09598f7f2470fb269732ec5b8ddc8",
    "青海": "1747a405d9a6437e8688f25c48c6205a",
}


# Platform detection utilities removed - no longer needed with webdriver-manager
# ChromeDriverManager automatically handles platform-specific driver management


def get_now():
    """Get current timestamp string."""
    now = datetime.now()
    now_str = now.strftime("%Y%m%d%H%M%S")
    return now_str


def get_csvdf(penfolder, beginwith):
    """Get concatenated dataframe from CSV files."""
    import os
    pattern = os.path.join(penfolder, beginwith + "*.csv")
    files2 = glob.glob(pattern, recursive=False)
    dflist = []
    for filepath in files2:
        try:
            pendf = get_pandas().read_csv(filepath, encoding='utf-8-sig')
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


def get_url_backend(orgname):
    """Get URL for organization."""
    if orgname not in org2id:
        raise ValueError(f"Organization '{orgname}' not found in org2id mapping")
    
    id = org2id[orgname]
    url = (
        "http://www.csrc.gov.cn/searchList/"
        + id
        + "?_isAgg=true&_isJson=true&_pageSize=10&_template=index&_rangeTimeGte=&_channelName=&page="
    )
    return url


def savedf_backend(df, basename):
    """Save dataframe to CSV."""
    savename = basename + ".csv"
    savepath = os.path.join(pencsrc2, savename)
    os.makedirs(os.path.dirname(savepath), exist_ok=True)
    df.to_csv(savepath, index=False, escapechar="\\", encoding='utf-8-sig')


def get_sumeventdf_backend(orgname, start, end):
    """Backend implementation of get_sumeventdf2.
    
    Args:
        orgname (str): Organization name
        start (int): Start page number
        end (int): End page number
        
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
        url = get_url_backend(orgname) + str(pageno)
        
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
            continue  # Skip this page and move to next
            
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

        # Save temporary results every 5 pages
        mod = (count + 1) % 5
        if mod == 0 and count > 0 and resultls:
            tempdf = get_pandas().concat(resultls)
            savename = "temp-" + orgname + "-0-" + str(count + 1)
            savedf_backend(tempdf, savename)

        # Reduced wait time to improve performance
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
    """Get CSRC analysis data"""
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    pencsrc2_abs = os.path.join(project_root, "data", "penalty", "csrc2")
    
    pendf = get_csvdf(pencsrc2_abs, "csrc2analysis")
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
    """Save dataframe to temp directory"""
    # Use absolute path to ensure it works from any working directory
    import os
    # Get the project root directory (dbcsrc)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
    
    savename = basename + ".csv"
    savepath = os.path.join(tempdir, savename)
    os.makedirs(os.path.dirname(savepath), exist_ok=True)
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
        eventdf["len"] = eventdf["内容"].astype(str).apply(len)
        
        # Filter for content length <= specified length (short content)
        misdf = eventdf[eventdf["len"] <= length]

        # filter by download_filter - include records that contain the filter
        # Treat 'none' as no filter (same as None or empty string)
        if download_filter and download_filter.lower() != 'none' and "名称" in misdf.columns:
            misdf = misdf[misdf["名称"].str.contains(download_filter, case=False, na=False)]

        # get df by column name - only include columns that exist
        available_cols = ["发文日期", "名称", "链接", "内容", "len", "filename"]
        select_cols = [col for col in available_cols if col in misdf.columns]
        misdf1 = misdf[select_cols]
        
        # sort by 发文日期 if column exists
        if "发文日期" in misdf1.columns:
            misdf1 = misdf1.sort_values(by="发文日期", ascending=False)
        
        # reset index
        misdf1.reset_index(drop=True, inplace=True)
        
        # Convert numpy data types to native Python types for JSON serialization
        for col in misdf1.columns:
            if misdf1[col].dtype == 'int64':
                misdf1[col] = misdf1[col].astype(int)
            elif misdf1[col].dtype == 'float64':
                misdf1[col] = misdf1[col].astype(float)
            elif misdf1[col].dtype == 'object':
                misdf1[col] = misdf1[col].astype(str)
        
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
        for col in newdf.columns:
            if newdf[col].dtype == 'int64':
                newdf[col] = newdf[col].astype(int)
            elif newdf[col].dtype == 'float64':
                newdf[col] = newdf[col].astype(float)
            elif newdf[col].dtype == 'object':
                newdf[col] = newdf[col].astype(str)
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
    print("Starting Chrome driver initialization...")
    
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
        print("Using ChromeDriverManager for automatic ChromeDriver setup...")
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("Successfully initialized Chrome driver with automatic management")
        return driver
    except Exception as e:
        # Fallback to system chromedriver if automatic management fails
        print(f"ChromeDriverManager failed: {e}")
        try:
            print("Attempting to use system chromedriver as fallback...")
            driver = webdriver.Chrome(options=options)
            print("Successfully initialized Chrome driver using system chromedriver")
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
    """Get CSRC length analysis dataframe."""
    # Define tempdir using absolute path
    import os
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(backend_dir)
    tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
    
    pendf = get_csvdf(tempdir, "csrclenanalysis")
    if not pendf.empty:
        pendf = pendf.fillna("")
    return pendf


def download_attachment(down_list=None):
    """Download attachments from CSRC URLs.
    
    Args:
        down_list: List of indices to download. If None, downloads all.
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
        submisls = [misls[i] for i in down_list]
    else:
        submisls = misls

    resultls = []
    errorls = []
    count = 0

    driver = get_chrome_driver()

    for i, url in enumerate(submisls):
        # Processing download
        try:
            driver.get(url)
            # Wait for the page to load and the specific element to be present
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "detail-news"))
            )

            page_source = driver.page_source
            sd = BeautifulSoup(page_source, "html.parser")

            dirpath = url.rsplit("/", 1)[0]
            try:
                filepath = sd.find_all("div", class_="detail-news")[0].a["href"]
                datapath = dirpath + "/" + filepath
                # Downloading file
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
                        
                        savename = get_now() + os.path.basename(datapath)
                        filename = os.path.join(tempdir, savename)
                        
                        with open(filename, "wb") as f:
                            for chunk in file_response.iter_content(1024 * 1024 * 2):
                                if chunk:
                                    f.write(chunk)
                        
                        # Verify file was downloaded successfully
                        if os.path.exists(filename) and os.path.getsize(filename) > 0:
                            text = ""
                            break
                        else:
                            raise Exception("Downloaded file is empty or doesn't exist")
                            
                    except Exception as download_error:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"Failed to download {datapath} after {max_retries} attempts: {str(download_error)}")
                            raise download_error
                        else:
                            print(f"Download attempt {retry_count} failed for {datapath}, retrying...")
                            time.sleep(2)  # Wait before retry
                            
            except Exception as e:
                # Error downloading file - log the specific error
                print(f"Error downloading attachment from {url}: {str(e)}")
                savename = ""
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

        mod = (count + 1) % 10
        if mod == 0 and count > 0:
            tempdf = pd.concat(resultls)
            savename = "temp-" + str(count + 1)
            savetemp(tempdf, savename)

        wait = random.randint(2, 20)
        time.sleep(wait)
        # Download completed
        count += 1

    driver.quit()

    if resultls:
        misdf = pd.concat(resultls)
        savecsv = "csrcmiscontent" + get_now()
        # reset index
        misdf.reset_index(drop=True, inplace=True)
        savetemp(misdf, savecsv)
        return misdf
    else:
        return get_pandas().DataFrame()