import math
import pickle
import re
from itertools import groupby
from operator import itemgetter

import chinese2digits as c2d
import pandas as pd
from paddlenlp import Taskflow
from utils import savetemp


def judge_end(S):
    count = 1

    for i in range(1, len(S)):
        if S[-i - 1] == '"' and S[-i - 2] == '"':
            count += 1
        else:
            break
    if count % 2 == 0:
        return False
    else:
        return True


def excel_clipboard(S):  # 直接从Excel复制并粘贴
    S = S.strip("\n") + "\n"
    count1 = 0
    count2 = 0
    result = []
    while count1 < len(S) - 1:
        # count2=count1
        # print(count1)
        if S[count1] != '"':
            # print(1)
            while count2 < len(S):
                count2 += 1
                if S[count2] == "\n":
                    # print(S[count1:count2])
                    result.append(S[count1 : count2 + 1])
                    count2 += 1
                    break

        elif S[count1] == '"':
            # print(1)
            while count2 < len(S):
                count2 += 1
                # print(S[count1:count1+count2])
                if (
                    S[count2] == "\n"
                    and S[count2 - 1] == '"'
                    and judge_end(S[count1 : count2 + 1])
                ):
                    # print(S[count1:count1+count2])
                    result.append(S[count1 : count2 + 1])
                    count2 += 1
                    break

        # print(S[count2])

        count1 = count2
    return result


def insert_str(str1, index, str2):  # str2插入str1的index位置
    str1_list = list(str1)
    str1_list.insert(index, str2)
    return "".join(str1_list)


def delete_str(str1, start, end):  # 删除str1的start到end位置
    str1_list = list(str1)
    del str1_list[start:end]
    return "".join(str1_list)


def count_list(list1, str1):  # 计算list1中str1出现的次数
    count = 0
    for i in list1:
        if i == str1:
            count += 1
    return count


def nlp_input(str, string):  # str为字符串目标list，string为字符串总量
    schema = str  # Define the schema for entity extraction
    ie = Taskflow("information_extraction", schema=schema, batch_size=14)
    return ie(string)


def wash_data(data):
    def get_Chinese_number(
        str1, str2, num
    ):  # str1为要搜的东西，str2为要搜的地方，num为想保留中文数字的最小个数；[0]为返回的中文数字，[1]为返回的数字
        def out_put_continuous(data, num):  # 获取list中连续的数字
            result = []
            for k, g in groupby(enumerate(data), lambda i_x: i_x[0] - i_x[1]):
                result.append(list(map(itemgetter(1), g)))
            # 删除长度为1的结果
            result_new = []
            for i in result:
                if len(i) >= num:
                    result_new.append(i)
                    # print(len(i))
            return result_new

        def get_keyword_position1(str1, str2):  # 抓取每个中文数字的位置
            somestr = str2
            substr = str1
            return [substr.start() for substr in re.finditer(substr, somestr)]

        # str2='十二万元'
        temp = get_keyword_position1(str1, str2)

        temp1 = out_put_continuous(temp, num)
        # data = [ 1, 4,5,6, 10, 15,16,17,18, 22, 25,26,27,28]
        # print(out_put_continuous(data))
        # print(temp1)
        results = []
        for i in temp1:
            result = ""
            for j in i:
                result = result + str2[j]
            results.append(result)

        results_num = []
        results_new = []
        for result in results:
            try:
                # print(c2d.takeNumberFromString(results[i])['digitsStringList'][0])
                results_num.append(
                    c2d.takeNumberFromString(result)["digitsStringList"][0]
                )
                results_new.append(result)
            except Exception as e:
                print(e)
                pass
                # results.remove(results[i])

        return results_new, results_num  # [0]为返回的中文数字，[1]为返回的数字

    # new_df_str = str(data).replace(' ', '').replace(',', '').replace('，', '')
    # 先对数字进行去千分符处理

    rexp = re.compile(r"(\d{1,3}([,，]\d{3})*(\.\d+)?)")
    temp = rexp.findall(data)
    # 找r中tuple最长的string组成新list
    temp = [max(i, key=len) for i in temp]
    # 按list中string的长度进行重新排序
    temp = sorted(temp, key=len, reverse=True)
    # 去除千位符
    for i in temp:
        data = data.replace(i, i.replace(",", "").replace("，", ""))
    new_df_str = data
    # 去除句首加顿号的情况用&代替
    rexp = re.compile(r"[一二三四五六七八九十\d+](?<!元)[、]")
    temp = rexp.findall(new_df_str)
    for i in temp:
        new_df_str = new_df_str.replace(i, i.replace("、", "&"))
    new_df_str = new_df_str.replace("人民币", "").replace("美元", "").replace("罚金", "罚款")
    # 下面开始微调以增强paddle的识别性,在数字后面加0
    num = get_position_and_str(r"[1-9]\d*\.?\d*", new_df_str)
    # 根据num每个元素第1个元素,对num元素进行倒序排序
    num.sort(key=lambda x: x[1], reverse=True)
    for i in range(len(num)):
        # 将num的剩余元素的第三位组成新list
        temp = []
        for j in range(i, len(num)):
            temp.append(num[j][2])
        count = count_list(temp, num[i][2])
        # string后插入指定个数的0
        if "." in num[i][2]:
            replace_num = num[i][2] + "0" * (count - 1)
        else:
            replace_num = num[i][2] + "." + "0" * (count - 1)
        new_df_str = delete_str(new_df_str, num[i][0], num[i][1])
        new_df_str = insert_str(new_df_str, num[i][0], replace_num)

    result = get_Chinese_number(
        r"[零,壹,贰,叁,肆,伍,陆,柒,捌,玖,拾,陌,阡,一,二,两,三,四,五,六,七,八,九,十,百,千,万,亿]",
        new_df_str,
        2,
    )
    try:
        temp = pd.DataFrame(columns=["数字", "中文", "长度"])
        temp["数字"] = result[1]
        temp["中文"] = result[0]
        # print(temp['中文'])
        temp["长度"] = temp["中文"].str.len()

        # 按照长度降序排序
        temp = temp.sort_values(by="长度", ascending=False)
        temp.reset_index(drop=True, inplace=True)

        for i in range(len(temp)):
            new_df_str = new_df_str.replace(temp.iloc[i, 1], temp.iloc[i, 0])
        new_df_str = new_df_str.strip("。") + "。"  # 末尾加句号
        new_df_str = re.sub(
            r"[一二三四五六七八九十\d]、",
            lambda x: x.group(0).replace("、", ")"),
            new_df_str,
        )  # 洗去数字加顿号的形式
        new_df_str = re.sub(
            r"决定[^:：]", lambda x: x.group(0).replace("决定", "决定："), new_df_str
        )
        # new_df_str=re.sub(r'决定[^:：]', '决定：',new_df_str)#把不规则的决定调试好
        new_df_str = new_df_str.strip("。") + "。"
        new_df_str = new_df_str.replace(".万元", "万元")
        new_df_str = new_df_str.replace(".元", "元")
        return new_df_str
    except Exception as e:
        print(e)
        new_df_str = new_df_str.strip("。") + "。"
        new_df_str = new_df_str.replace(".万元", "万元")
        new_df_str = new_df_str.replace(".元", "元")
        return new_df_str


def get_position_and_str(str1, str2, expander=0):  # str1为要搜的东西，str2为要搜的地方，expander为扩展值
    result = []
    f = re.finditer(str1, str2)
    for i in f:
        result.append(list([i.span()[0] - expander, i.span()[1] + expander, i.group()]))
        # print(i.span()[0])
    # add=re.findall(str1,str2)
    # for i in range(len(result)):
    #     result[i].append(str2[result[i][0]:result[i][1]])
    #     # result[i].append(add[i])
    # # print(add)
    # print(result)
    return result


def compare(
    list1, list2, strict=1
):  # list需要是[[1,2,str]]这样的综合list，计算各元素的最小距离,默认出的结果list1不重复且保留带文字的distance
    all = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
    if list1 == []:
        # print(temp)
        # all1 = all
        # all2 = all
        return all
    elif list2 == []:
        all["list1"] = list1
        all["list2"] = ["na"] * len(list1)
        all["list2-list1"] = ["na"] * len(list1)
        return all
    else:
        for i in list1:
            temp = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
            for j in list2:
                if (j[0] <= i[1] - 1 and j[1] - 1 > i[1] - 1 and i[0] < j[0]) or (
                    j[1] - 1 >= i[0] and j[0] < i[0] and i[1] - 1 > j[1] - 1
                ):
                    distance = "相交"
                elif j[0] <= i[0] and j[1] - 1 >= i[1] - 1:
                    distance = "list2包含list1"
                elif j[1] - 1 <= i[1] - 1 and j[0] >= i[0]:
                    distance = "list1包含list2"
                elif j[1] - 1 == i[1] - 1 and j[0] == i[0]:
                    distance = "相等"
                elif j[0] > i[1] - 1:
                    distance = j[0] - (i[1] - 1)
                elif j[1] - 1 < i[0]:
                    distance = (j[1] - 1) - i[0]
                # print(i)
                # print(j)
                temp = pd.concat(
                    [
                        temp,
                        pd.DataFrame(
                            {
                                "list1": [[i[0], i[1], i[2]]],
                                "list2": [[j[0], j[1], j[2]]],
                                "list2-list1": distance,
                            }
                        ),
                    ],
                    axis=0,
                    join="outer",
                )

            temp1 = temp[
                temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            # print(temp1)
            temp2 = temp[
                ~temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            # print(temp1)
            temp2 = temp2[
                temp2["list2-list1"].abs() == temp2["list2-list1"].abs().min()
            ]  # 求最小的距离
            all = pd.concat([all, temp1, temp2], axis=0, join="outer")

            # 去除重复项
        if strict == 1:
            all["key"] = all["list1"].apply(lambda x: "".join(str(x)))
            all = all.drop_duplicates(subset=["key"], keep="first")
        all = all.drop(["key"], axis=1)
        all.reset_index(drop=True, inplace=True)
        # all1=all[all['list2-list1'].astype(str).str.contains(r'相交|list1包含list2|list2包含list1|相等', regex= True)]
        # all2=all[~all['list2-list1'].astype(str).str.contains(r'相交|list1包含list2|list2包含list1|相等', regex= True)]
        # print(all)
        return all


def jieya1(dataframe):
    result = pd.DataFrame(
        columns=[
            "list1首",
            "list1尾",
            "list1",
            "list2首",
            "list2尾",
            "list2",
            "list2-list1",
        ]
    )
    for i in range(len(dataframe)):
        result = pd.concat(
            [
                result,
                pd.DataFrame(
                    {
                        "list1首": [dataframe["list1"][i][0]],
                        "list1尾": [dataframe["list1"][i][1]],
                        "list1": [dataframe["list1"][i][2]],
                        "list2首": [dataframe["list2"][i][0]],
                        "list2尾": [dataframe["list2"][i][1]],
                        "list2": [dataframe["list2"][i][2]],
                        "list2-list1": [dataframe["list2-list1"][i]],
                    }
                ),
            ],
            axis=0,
            join="outer",
        )
    result1 = result[
        result["list2-list1"]
        .astype(str)
        .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
    ]
    result2 = result[
        ~result["list2-list1"]
        .astype(str)
        .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
    ]
    return result, result1, result2


def jieya(list):
    result = pd.DataFrame(columns=["list1首", "list1尾", "list1"])
    for i in range(len(list)):
        result = pd.concat(
            [
                result,
                pd.DataFrame(
                    {
                        "list1首": [list[i][0]],
                        "list1尾": [list[i][1]],
                        "list1": [list[i][2]],
                    }
                ),
            ],
            axis=0,
            join="outer",
        )
    return result


def yasuo(dataframe):
    # dataframe合并成list
    list1 = []
    for i in range(len(dataframe)):
        # print(dataframe['list尾'][i])
        list1.append(
            [dataframe["list1首"][i], dataframe["list1尾"][i], dataframe["list1"][i]]
        )
    return list1


def get_number(moneys):
    sum = 0
    if len(moneys) != 0:
        for money in moneys:
            money[2] = money[2].replace("人民币", "").replace("的", "")
            try:
                if "亿元" in money[2]:
                    money[2] = money[2].replace("亿元", "")
                    money[2] = float(money[2]) * 100000000

                elif "千万元" in money[2]:
                    money[2] = money[2].replace("千万元", "")
                    money[2] = float(money[2]) * 10000000

                elif "万元" in money[2]:
                    money[2] = money[2].replace("万元", "")
                    money[2] = float(money[2]) * 10000

                elif "元" in money[2]:
                    money[2] = money[2].replace("元", "")
                    money[2] = float(money[2])
                elif "万" in money[2]:
                    money[2] = money[2].replace("万", "")
                    money[2] = float(money[2]) * 10000
            except Exception as e:
                print(e)
                money[2] = float(money[2])
            sum = sum + round(money[2], 2)
    else:
        moneys = moneys
        sum = 0
        # print(sum)
    return moneys, sum


def cut_string(
    strings, divs, o=0, keep=0
):  # strings为要分割的字符list矩阵(包含位置与字符),div为分割的querys,list,o=0代表割掉该字段之前的部分,o=1代表割掉该字段之后的部分,kepp=0表示如果没有切割词,则保留原来的字符数组,keep=1表示如果没有切割词,则不返回
    results = []
    for ss in strings:
        s = ss[2]
        result = []

        for div in divs:
            if len(s.split(div)) >= 2:
                # s=wash_data(s)
                # get_position_and_str('罚款',s)
                a = s.split(div)
                # print(a)
                if o == 0:
                    del a[0]
                elif o == 1:
                    del a[-1]
                a = ",".join(a)
                leng = len(a)
                # print(l)
                if o == 0:
                    result.append([ss[1] - leng, ss[1], a])
                    # result=result+[[ss[1] - l, ss[1], a]]
                elif o == 1:
                    result.append([ss[0], ss[0] + leng, a])
                    # result=result+[[ss[0], ss[0] + l, a]]
                # result.append([ss[0],ss[1],a])
                results = results + result
                break
                # return a

        if keep == 0 and len(result) == 0:
            results.append(ss)

    return results
    # return ''


def get_relation(a, b):  # 这是判断两个点关系的函数
    if a[0] <= b[0] and a[1] >= b[1]:
        return "包含"
    if a[0] >= b[0] and a[1] <= b[1]:
        return "被包含"
    if a[0] <= b[0] and a[1] > b[0] and a[1] <= b[1]:
        return "相交"
    if a[0] >= b[0] and a[0] < b[1] and a[1] >= b[1]:
        return "相交"
    if a[1] <= b[0]:
        return "左"
    if a[0] >= b[1]:
        return "右"
    # return '无关系'


def multi_relation(
    list1, list2
):  # 这是判断一堆点关系的函数list1为主list2为被比较list,list1为行坐标,list2为列坐标
    list1 = [str(i) for i in list1]
    list2 = [str(i) for i in list2]
    df = pd.DataFrame(index=list1, columns=list2)
    for i in list1:
        for j in list2:
            df.loc[i, j] = get_relation(eval(i), eval(j))
            # print(eval(i))
    return df


# 以下是专为自定义式子所做的函数
def list_small(list1, list2, strict=1):
    # print('list1:',list1)
    # print('list2:',list2)
    all = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
    if list1 == []:
        return list1
    elif list2 == []:
        return []
    else:
        for i in list1:
            temp = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
            for j in list2:
                if (j[0] <= i[1] - 1 and j[1] - 1 > i[1] - 1 and i[0] < j[0]) or (
                    j[1] - 1 >= i[0] and j[0] < i[0] and i[1] - 1 > j[1] - 1
                ):
                    distance = "相交"
                elif j[0] <= i[0] and j[1] - 1 >= i[1] - 1:
                    distance = "list2包含list1"
                elif j[1] - 1 <= i[1] - 1 and j[0] >= i[0]:
                    distance = "list1包含list2"
                elif j[1] - 1 == i[1] - 1 and j[0] == i[0]:
                    distance = "相等"
                elif j[0] > i[1] - 1:
                    distance = j[0] - (i[1] - 1)
                elif j[1] - 1 < i[0]:
                    distance = (j[1] - 1) - i[0]
                temp = pd.concat(
                    [
                        temp,
                        pd.DataFrame(
                            {
                                "list1": [[i[0], i[1], i[2]]],
                                "list2": [[j[0], j[1], j[2]]],
                                "list2-list1": distance,
                            }
                        ),
                    ],
                    axis=0,
                    join="outer",
                )
            temp1 = temp[
                temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp[
                ~temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp2[
                temp2["list2-list1"].abs() == temp2["list2-list1"].abs().min()
            ]  # 求最小的距离
            all = pd.concat([all, temp1, temp2], axis=0, join="outer")
        if strict == 1:
            all["key"] = all["list1"].apply(lambda x: "".join(str(x)))
            all = all.drop_duplicates(subset=["key"], keep="first")
        all = all[
            all["list2-list1"].astype(str).str.contains(r"list2包含list1", regex=True)
        ]
        all = all["list1"].tolist()
        # all2=all[~all['list2-list1'].astype(str).str.contains(r'相交|list1包含list2|list2包含list1|相等', regex= True)]
        # print(all)
        return all


def list_split(list1, list2, strict=1):
    # print(list1)
    all = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
    if list1 == []:
        return list1
    elif list2 == []:
        # print(list1)
        return list1
    else:
        for i in list1:
            temp = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
            for j in list2:
                if (j[0] <= i[1] - 1 and j[1] - 1 > i[1] - 1 and i[0] < j[0]) or (
                    j[1] - 1 >= i[0] and j[0] < i[0] and i[1] - 1 > j[1] - 1
                ):
                    distance = "相交"
                elif j[0] <= i[0] and j[1] - 1 >= i[1] - 1:
                    distance = "list2包含list1"
                elif j[1] - 1 <= i[1] - 1 and j[0] >= i[0]:
                    distance = "list1包含list2"
                elif j[1] - 1 == i[1] - 1 and j[0] == i[0]:
                    distance = "相等"
                elif j[0] > i[1] - 1:
                    distance = j[0] - (i[1] - 1)
                elif j[1] - 1 < i[0]:
                    distance = (j[1] - 1) - i[0]
                temp = pd.concat(
                    [
                        temp,
                        pd.DataFrame(
                            {
                                "list1": [[i[0], i[1], i[2]]],
                                "list2": [[j[0], j[1], j[2]]],
                                "list2-list1": distance,
                            }
                        ),
                    ],
                    axis=0,
                    join="outer",
                )
            temp1 = temp[
                temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp[
                ~temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp2[
                temp2["list2-list1"].abs() == temp2["list2-list1"].abs().min()
            ]  # 求最小的距离
            all = pd.concat([all, temp1, temp2], axis=0, join="outer")
        if strict == 1:
            all["key"] = all["list1"].apply(lambda x: "".join(str(x)))
            all = all.drop_duplicates(subset=["key"], keep="first")
        # all=all[all['list2-list1'].astype(str).str.contains(r'list2包含list1', regex= True)]
        if len(
            all[
                ~all["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
        ) != len(
            all[
                ~all["list2-list1"]
                .astype(str)
                .str.contains(r"list2包含list1", regex=True)
            ]
        ):
            print("存在相交")
        all = all[
            ~all["list2-list1"]
            .astype(str)
            .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
        ]
        # print(all)
        all = all["list1"].tolist()
        # print(all)
        return all


def list_big(list1, list2, strict=1):
    all = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
    if list1 == []:
        return list1
    elif list2 == []:
        return []
    else:
        for i in list1:
            temp = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
            for j in list2:
                if (j[0] <= i[1] - 1 and j[1] - 1 > i[1] - 1 and i[0] < j[0]) or (
                    j[1] - 1 >= i[0] and j[0] < i[0] and i[1] - 1 > j[1] - 1
                ):
                    distance = "相交"
                elif j[0] <= i[0] and j[1] - 1 >= i[1] - 1:
                    distance = "list2包含list1"
                elif j[1] - 1 <= i[1] - 1 and j[0] >= i[0]:
                    distance = "list1包含list2"
                elif j[1] - 1 == i[1] - 1 and j[0] == i[0]:
                    distance = "相等"
                elif j[0] > i[1] - 1:
                    distance = j[0] - (i[1] - 1)
                elif j[1] - 1 < i[0]:
                    distance = (j[1] - 1) - i[0]
                temp = pd.concat(
                    [
                        temp,
                        pd.DataFrame(
                            {
                                "list1": [[i[0], i[1], i[2]]],
                                "list2": [[j[0], j[1], j[2]]],
                                "list2-list1": distance,
                            }
                        ),
                    ],
                    axis=0,
                    join="outer",
                )
            temp1 = temp[
                temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp[
                ~temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp2[
                temp2["list2-list1"].abs() == temp2["list2-list1"].abs().min()
            ]  # 求最小的距离
            all = pd.concat([all, temp1, temp2], axis=0, join="outer")
        if strict == 1:
            all["key"] = all["list1"].apply(lambda x: "".join(str(x)))
            all = all.drop_duplicates(subset=["key"], keep="first")
        all = all[
            all["list2-list1"].astype(str).str.contains(r"list1包含list2", regex=True)
        ]
        all = all["list1"].tolist()
        # all2=all[~all['list2-list1'].astype(str).str.contains(r'相交|list1包含list2|list2包含list1|相等', regex= True)]
        # print(all)
        return all


def list_abs(list1, list2, n, strict=1):
    all = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
    if list1 == []:
        return list1
    elif list2 == []:
        return []
    else:
        for i in list1:
            temp = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
            for j in list2:
                if (j[0] <= i[1] - 1 and j[1] - 1 > i[1] - 1 and i[0] < j[0]) or (
                    j[1] - 1 >= i[0] and j[0] < i[0] and i[1] - 1 > j[1] - 1
                ):
                    distance = "相交"
                elif j[0] <= i[0] and j[1] - 1 >= i[1] - 1:
                    distance = "list2包含list1"
                elif j[1] - 1 <= i[1] - 1 and j[0] >= i[0]:
                    distance = "list1包含list2"
                elif j[1] - 1 == i[1] - 1 and j[0] == i[0]:
                    distance = "相等"
                elif j[0] > i[1] - 1:
                    distance = j[0] - (i[1] - 1)
                elif j[1] - 1 < i[0]:
                    distance = (j[1] - 1) - i[0]
                temp = pd.concat(
                    [
                        temp,
                        pd.DataFrame(
                            {
                                "list1": [[i[0], i[1], i[2]]],
                                "list2": [[j[0], j[1], j[2]]],
                                "list2-list1": distance,
                            }
                        ),
                    ],
                    axis=0,
                    join="outer",
                )
            temp1 = temp[
                temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp[
                ~temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp2[
                temp2["list2-list1"].abs() == temp2["list2-list1"].abs().min()
            ]  # 求最小的距离
            all = pd.concat([all, temp1, temp2], axis=0, join="outer")
        if strict == 1:
            all["key"] = all["list1"].apply(lambda x: "".join(str(x)))
            all = all.drop_duplicates(subset=["key"], keep="first")
        # all=all[all['list2-list1'].astype(str).str.contains(r'list1包含list2', regex= True)]
        all = all[
            ~all["list2-list1"]
            .astype(str)
            .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
        ]
        all = all[all["list2-list1"].abs() <= n]
        all = all["list1"].tolist()
        # all2=all[~all['list2-list1'].astype(str).str.contains(r'相交|list1包含list2|list2包含list1|相等', regex= True)]
        # print(all)
        return all


def list_distance(list1, list2, n, strict=1):
    all = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
    if list1 == []:
        return list1
    elif list2 == []:
        return []
    else:
        for i in list1:
            temp = pd.DataFrame(columns=["list1", "list2", "list2-list1"])
            for j in list2:
                if (j[0] <= i[1] - 1 and j[1] - 1 > i[1] - 1 and i[0] < j[0]) or (
                    j[1] - 1 >= i[0] and j[0] < i[0] and i[1] - 1 > j[1] - 1
                ):
                    distance = "相交"
                elif j[0] <= i[0] and j[1] - 1 >= i[1] - 1:
                    distance = "list2包含list1"
                elif j[1] - 1 <= i[1] - 1 and j[0] >= i[0]:
                    distance = "list1包含list2"
                elif j[1] - 1 == i[1] - 1 and j[0] == i[0]:
                    distance = "相等"
                elif j[0] > i[1] - 1:
                    distance = j[0] - (i[1] - 1)
                elif j[1] - 1 < i[0]:
                    distance = (j[1] - 1) - i[0]
                temp = pd.concat(
                    [
                        temp,
                        pd.DataFrame(
                            {
                                "list1": [[i[0], i[1], i[2]]],
                                "list2": [[j[0], j[1], j[2]]],
                                "list2-list1": distance,
                            }
                        ),
                    ],
                    axis=0,
                    join="outer",
                )
            temp1 = temp[
                temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp[
                ~temp["list2-list1"]
                .astype(str)
                .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
            ]
            temp2 = temp2[
                temp2["list2-list1"].abs() == temp2["list2-list1"].abs().min()
            ]  # 求最小的距离
            all = pd.concat([all, temp1, temp2], axis=0, join="outer")
        if strict == 1:
            all["key"] = all["list1"].apply(lambda x: "".join(str(x)))
            all = all.drop_duplicates(subset=["key"], keep="first")
        all = all[
            ~all["list2-list1"]
            .astype(str)
            .str.contains(r"相交|list1包含list2|list2包含list1|相等", regex=True)
        ]
        all = all[all["list2-list1"] * n > 0]
        all = all["list1"].tolist()
        # all2=all[~all['list2-list1'].astype(str).str.contains(r'相交|list1包含list2|list2包含list1|相等', regex= True)]
        # print(all)
        return all


def save_variable(v, filename):  # 用于存储变量
    f = open(filename, "wb")  # 打开或创建名叫filename的文档。
    pickle.dump(v, f)  # 在文件filename中写入v
    #     pickle.dump(a, handle)
    f.close()  # 关闭文件，释放内存。
    return filename


# 用此class自定义运算符
class Infix(object):
    def __init__(self, func):
        self.func = func

    class RBind:
        def __init__(self, func, binded):
            self.func = func
            self.binded = binded

        def __call__(self, other):
            return self.func(other, self.binded)

        __ror__ = __call__

    class LBind:
        def __init__(self, func, binded):
            self.func = func
            self.binded = binded

        def __call__(self, other):
            return self.func(self.binded, other)

        __or__ = __call__

    def __or__(self, other):
        return self.RBind(self.func, other)

    def __ror__(self, other):
        return self.LBind(self.func, other)

    def __call__(self, value1, value2):
        return self.func(value1, value2)


# 运算符定义：（以下式子的结果均是保留list1）
# |small|代表求list1包含于list2的部分
# |split|代表求list1与list2分离的部分；
# |big|代表求list1包含list2的部分；
# |dabs50|代表list1与list2的绝对值距离小于50；
# |dabs10|代表list1于list2绝对值距离小于10；
# |dsmall|代表list1出现在list2左边；
# |dbig|代表list1出现在list2右边
# |dcut|
small = Infix(lambda list1, list2: list_small(list1, list2))
split = Infix(lambda list1, list2: list_split(list1, list2))
big = Infix(lambda list1, list2: list_big(list1, list2))
dabs50 = Infix(lambda list1, list2: list_abs(list1, list2, 50))
dabs10 = Infix(lambda list1, list2: list_abs(list1, list2, 10))
dsmall = Infix(lambda list1, list2: list_distance(list1, list2, 1))
dbig = Infix(lambda list1, list2: list_distance(list1, list2, -1))


def accurate_compare(
    list1, list2, list3, method1, method2
):  # 通过list3的每一项锁定list1与list2的每一项，并拿list1，list2每一项做比较，method1是list1、2与list3的关系，method2是比较list1与list2的关系，用1-7分别代表上述公式方法
    result = []
    for i in list3:
        if method1 == 1:
            # print(list1)
            temp1 = list1 | small | [i]
            temp2 = list2 | small | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 2:
            temp1 = list1 | split | [i]
            temp2 = list2 | split | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 3:
            temp1 = list1 | big | [i]
            temp2 = list2 | big | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 4:
            temp1 = list1 | dabs50 | [i]
            temp2 = list2 | dabs50 | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 5:
            temp1 = list1 | dabs10 | [i]
            temp2 = list2 | dabs10 | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 6:
            temp1 = list1 | dsmall | [i]
            temp2 = list2 | dsmall | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 7:
            temp1 = list1 | dbig | [i]
            temp2 = list2 | dbig | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        result = result + temp3
    return result


def calculate_顿号(list1, list2, list3, method1, method2):  # 专门用来求顿号的函数
    result = []
    # temp_copy = copy.deepcopy(list2)
    # print(len(list3))
    for i in list3:
        if method1 == 1:
            # print(list1)
            temp1 = list1 | small | [i]
            temp2 = list2 | small | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 2:
            temp1 = list1 | split | [i]
            temp2 = list2 | split | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 3:
            temp1 = list1 | big | [i]
            temp2 = list2 | big | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 4:
            temp1 = list1 | dabs50 | [i]
            temp2 = list2 | dabs50 | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 5:
            temp1 = list1 | dabs10 | [i]
            temp2 = list2 | dabs10 | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 6:
            temp1 = list1 | dsmall | [i]
            temp2 = list2 | dsmall | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        elif method1 == 7:
            temp1 = list1 | dbig | [i]
            temp2 = list2 | dbig | [i]
            if method2 == 1:
                temp3 = temp1 | small | temp2
            elif method2 == 2:
                temp3 = temp1 | split | temp2
            elif method2 == 3:
                temp3 = temp1 | big | temp2
            elif method2 == 4:
                temp3 = temp1 | dabs50 | temp2
            elif method2 == 5:
                temp3 = temp1 | dabs10 | temp2
            elif method2 == 6:
                temp3 = temp1 | dsmall | temp2
            elif method2 == 7:
                temp3 = temp1 | dbig | temp2
        if len(temp3) == 0 or len(temp2) > 1:
            temp2 = temp2
        elif len(temp3) > 0:
            temp2[0][2] = temp2[0][2] * (1 + len(temp3))
        result = result + temp2
    return result


def calculate_similar(key, string, keep=0):  # key为关键词，string为要输入的字符串,keep为要保留的位数
    import math
    import re

    import pandas as pd
    from paddlenlp import Taskflow

    def split_santence(string, s=128):  # string是要分的句子，s为阈值
        n = math.ceil(len(string) / s)
        num = math.floor(len(string) / n)
        return re.findall(r"[\s\S]{1," + str(num) + "}", string)

    def get_position_and_str(
        str1, str2, expander=0
    ):  # str1为要搜的东西，str2为要搜的地方，expander为扩展值
        result = []
        f = re.finditer(str1, str2)
        for i in f:
            result.append(
                list([i.span()[0] - expander, i.span()[1] + expander, i.group()])
            )
            # print(i.span()[0])
        # add=re.findall(str1,str2)
        # for i in range(len(result)):
        #     result[i].append(str2[result[i][0]:result[i][1]])
        #     # result[i].append(add[i])
        # # print(add)
        # print(result)
        return result

    db_outcome = pd.DataFrame(columns=["文字", "相似度"])
    result_句子 = get_position_and_str(r"[\s\S]*?[：:；;。\n]", string)
    # print(result_句子)
    temp = []
    for j in result_句子:
        temp = temp + split_santence(j[2])
        # print(split_santence(j[2]))
    # print(temp)
    result = []
    for i in key:
        for j in temp:
            result.append([i] + [j])
    # print(result)
    similarity = Taskflow("text_similarity", batch_size=30)
    result = similarity(result)
    for j in result:
        db_outcome = pd.concat(
            [
                db_outcome,
                pd.DataFrame(
                    columns=["文字", "相似度"], data=[[j["text2"], j["similarity"]]]
                ),
            ]
        )

    # 删除重复项保留第一个
    db_outcome = db_outcome.drop_duplicates(subset=["文字"], keep="first")
    if keep != 0:
        db_outcome = db_outcome.sort_values(by=["相似度"], ascending=False).head(keep)
    else:
        db_outcome = db_outcome.sort_values(by=["相似度"], ascending=False)
    db_outcome.index = range(1, len(db_outcome) + 1)

    return db_outcome


def calculate_similar_batch(key, string_list):  # key为关键词，string_list为要输入的字符串数组
    import math
    import re

    import pandas as pd
    from paddlenlp import Taskflow

    def split_santence(string, s=128):  # string是要分的句子，s为阈值
        n = math.ceil(len(string) / s)
        num = math.floor(len(string) / n)
        return re.findall(r"[\s\S]{1," + str(num) + "}", string)

    db_outcome = pd.DataFrame(columns=["query", "文字", "相似度"])
    result = []
    result_query = []
    for i in key:
        for j in string_list:
            result.append([i] + [j])
            result_query.append(i)
    # print(result)
    similarity = Taskflow("text_similarity", batch_size=30)
    result = similarity(result)
    for j in result:
        db_outcome = pd.concat(
            [
                db_outcome,
                pd.DataFrame(
                    columns=["文字", "相似度"], data=[[j["text2"], j["similarity"]]]
                ),
            ]
        )
    db_outcome["query"] = result_query
    return db_outcome


def check_contain_valid_str(check_str):
    """判断字符串是否包含有效字符：中文 or 英文 or 数字"""

    def check_contain_chinese(check_str):
        """判断字符串中是否含有中文字符"""
        for ch in check_str:
            if "\u4e00" <= ch <= "\u9fff":
                return True
        return False

    def check_contain_englist(check_str):
        """判断字符串中是否含有英文字符"""
        contain_en = bool(re.search("[a-z]", check_str))
        return contain_en

    def check_contain_digits(check_str):
        """判断字符串中是否含有数字字符"""
        contain_di = bool(re.search("[0-9]", check_str))
        return contain_di

    valid_res = (
        check_contain_englist(check_str)
        or check_contain_chinese(check_str)
        or check_contain_digits(check_str)
    )
    return valid_res


def split_santence(string, s=128):  # string是要分的句子，s为阈值
    n = math.ceil(len(string) / s)
    num = math.floor(len(string) / n)
    result = re.findall(r"[\s\S]{1," + str(num) + "}", string)
    result1 = []
    for i in result:
        if check_contain_valid_str(i):  # 判断是否包含有效字符
            result1.append(i)
    return result1


def extract_money(
    stringall, flag=1
):  # string_all 为一个list,里面写证监局的文，flag=1代表罚款，flag=2代表没收
    # 2先对文字进行简单裁剪(关键词['局决定','会决定','现对','鉴于',',决定：','，决定：','的规定','的要求']),我只要这些词之后的东西
    # region
    content = stringall
    querys = [
        "局决定",
        "会决定",
        "现对",
        "鉴于",
        ",决定：",
        "，决定：",
        "的规定",
        "的要求",
    ]
    temp = []
    for i in range(len(content)):
        temp.append([0, 0, content[i]])
    temps = cut_string(temp, querys)
    temp1 = [i[2] for i in temps]
    cutted_contents = [wash_data(i) for i in temp1]
    # endregion

    # 3用paddle提取金额
    # region
    if flag == 1:
        choose = "罚款"
    if flag == 2:
        choose = "没收金额"
    temps = nlp_input([choose], cutted_contents)
    result_罚款_df = pd.DataFrame(columns=["编号", "罚款详情"])
    for i in range(len(temps)):
        temp1s = []
        if len(temps[i]) == 0:
            temp1s.append(["", "", ""])
        else:
            for temp1 in temps[i][choose]:
                temp1s.append([temp1["start"], temp1["end"], temp1["text"]])
        result_罚款_df = pd.concat(
            [result_罚款_df, pd.DataFrame({"编号": [str(i)], "罚款详情": [temp1s]})]
        )
    # 调整result_罚款_df,使[['','' ,'' ]]为空值
    for i in range(len(result_罚款_df)):
        if result_罚款_df.iloc[i, 1] == [["", "", ""]]:
            result_罚款_df.iloc[i, 1] = ""
    # endregion
    # 4对剩下的内容进行进一步处理
    # region
    sum_list = []
    for iall in range(len(cutted_contents)):  # len(cutted_contents)
        try:
            result_金额 = result_罚款_df.iloc[iall, 1]
            # print(result_金额)
            if result_金额 == "":  # [['', '', '']]
                sum_list.append(0)

            else:
                string1 = cutted_contents[iall]
                result_综上 = get_position_and_str(r"综上|综合上述", string1)
                result_句子 = get_position_and_str(r"[\s\S]*?[：:；;。]", string1)
                result_其中 = get_position_and_str(r"其中", string1)
                result_合计 = get_position_and_str(r"合计", string1)
                # print(result_金额)
                # 2对剩余的表述进行金额的提取
                # 2.1根据符号提取出段落的句子,这些句子需满足包含金额的条件
                # 先找到含罚款信息的句子,
                result_带金额句子 = result_句子 | big | result_金额
                # 我先要判断'综上'后面有没有金额，如果有，就把'综上'前面的内容删掉
                result_带金额句子_包含综上 = []
                for i in result_带金额句子:
                    # 先提取出金额
                    temp_金额 = result_金额 | small | [i]
                    temp_综上 = result_综上 | small | [i]
                    if len(temp_综上) > 0:
                        # 开始判断与综上的关系
                        matrix = multi_relation(temp_金额, temp_综上)
                        # print(matrix)
                        # 计算出现在第一个综上右边的金额的个数
                        count = matrix.iloc[:, 0].str.contains("右").sum()
                        # print(count)
                        # 如果左边的金额个数大于0,则删除综上
                        if count > 0:
                            temp = cut_string([i], ["综上", "综合上述"], o=0)[0]
                            result_带金额句子_包含综上 = []
                            result_带金额句子_包含综上.append(temp)
                            break
                        else:
                            result_带金额句子_包含综上.append(i)
                    else:
                        result_带金额句子_包含综上.append(i)

                # print(result_带金额句子_包含综上)
                # 先找包含合计的句子
                result_带金额句子_包含综上_包含合计 = []
                for temp in result_带金额句子_包含综上:
                    temp_金额 = result_金额 | small | [temp]
                    temp_合计 = result_合计 | small | [temp]
                    if len(temp_合计) > 0:
                        # 开始判断与综上的关系
                        matrix = multi_relation(temp_金额, temp_合计)
                        # print(matrix)
                        # 计算出现在第一个综上右边的金额的个数
                        count = matrix.iloc[:, 0].str.contains("右").sum()
                        # print(count)
                        # 如果左边的金额个数大于0,则删除综上
                        if count > 0:
                            temp = cut_string([temp], ["合计"], o=0)[0]
                            result_带金额句子_包含综上_包含合计.append(temp)
                        else:
                            result_带金额句子_包含综上_包含合计.append(temp)
                    else:
                        result_带金额句子_包含综上_包含合计.append(temp)
                # print(result_带金额句子_包含综上_包含合计)
                # 再剔除"其中",这里采用遍历的方法
                result_带金额句子_包含综上_包含合计_剔除其中 = []
                for temp in result_带金额句子_包含综上_包含合计:
                    temp_金额 = result_金额 | small | [temp]
                    temp_其中 = result_其中 | small | [temp]
                    if len(temp_其中) > 0:
                        # 开始判断与其中的关系
                        matrix = multi_relation(temp_金额, temp_其中)
                        # print(matrix)
                        # 计算出现在第一个其中右边的金额的个数
                        count = matrix.iloc[:, 0].str.contains("左").sum()
                        # print(count)
                        # 如果左边的金额个数大于0,则删除其中
                        if count > 0:
                            temp = cut_string([temp], ["其中", "(作为", "（作为"], o=1)[0]
                            result_带金额句子_包含综上_包含合计_剔除其中.append(temp)
                        else:
                            result_带金额句子_包含综上_包含合计_剔除其中.append(temp)
                    else:
                        result_带金额句子_包含综上_包含合计_剔除其中.append(temp)

                # print(result_带金额句子_包含综上_包含合计_剔除其中)
                # 最后开始处理分别
                # 1先进一步分句
                # result_句子 = get_position_and_str(r'[\s\S]*?[：:；;。，,]', string1)
                # print(result_句子)
                result_带金额句子_包含综上_包含合计_剔除其中_分句 = result_带金额句子_包含综上_包含合计_剔除其中
                sums = 0
                for temp in result_带金额句子_包含综上_包含合计_剔除其中_分句:
                    # 先提取出金额
                    temp_金额 = result_金额 | small | [temp]
                    # print(temp)
                    # 如果在一个小句子中,出现了两个金额,则不考虑分别的情况
                    # print(temp_金额)
                    if len(temp_金额) > 1 or (
                        temp[2].count("分别") == 0 and temp[2].count("各") == 0
                    ):
                        # 提取temp_金额每个元素的第三位组成新的数组
                        # temp_金额_第三位=[i[2] for i in temp_金额]
                        # print(temp_金额)
                        sum = get_number(temp_金额)[1]
                    else:
                        c = temp[2].count("、") + 1
                        # print(temp_金额)
                        sum = get_number(temp_金额)[1] * c
                    sums = sums + sum
                sum_list.append(sums)
        except Exception as e:
            print(e)
            print(cutted_contents[iall])
            print(iall)
            sum_list.append(0)
    # endregion
    return sum_list


def df2amount(df, idcol, contentcol):
    df1 = df[[idcol, contentcol]]

    idls = []
    finels = []
    confisls = []
    start = 0
    end = len(df1)
    for i in range(start, end):
        id = df1.iloc[i][idcol]
        content = df1.iloc[i][contentcol]
        print(i)
        print(content)
        fine = extract_money([str(content)], 1)
        confiscate = extract_money([str(content)], 2)
        print("fine:", fine)
        print("confiscate:", confiscate)
        idls.append(id)
        finels.append(fine)
        confisls.append(confiscate)

        if (i + 1) % 100 == 0 and i > start:
            tempdf = pd.DataFrame({"id": idls, "finels": finels, "confisls": confisls})
            tempdf["fine"] = tempdf["finels"].apply(lambda x: x[0])
            tempdf["confiscate"] = tempdf["confisls"].apply(lambda x: x[0])
            tempdf["amount"] = tempdf["fine"] + tempdf["confiscate"]
            savename = "tempamt-" + str(i)
            savetemp(tempdf, savename)

    resdf = pd.DataFrame({"id": idls, "finels": finels, "confisls": confisls})
    resdf["fine"] = resdf["finels"].apply(lambda x: x[0])
    resdf["confiscate"] = resdf["confisls"].apply(lambda x: x[0])
    resdf["amount"] = resdf["fine"] + resdf["confiscate"]
    # savename = "csrc2amt" + get_nowdate()+".csv"
    # savedf2(resdf, savename)
    return resdf
