import pandas as pd
import openai
import os
import json
from utils import savetemp

# Initialize OpenAI client
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

# Get model name from environment or use default
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

def get_class(article, candidate_labels, multi_label=False):
    """Classify text using OpenAI LLM"""
    try:
        # Create prompt for classification
        labels_str = ", ".join(candidate_labels)
        prompt = f"""Please classify the following text into one of these categories: {labels_str}
        
Text to classify: {article}
        
Respond with only a JSON object in this format:
        {{
            "label": "selected_category",
            "score": confidence_score_between_0_and_1
        }}
        
Choose the most appropriate category from the provided list."""
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a text classification assistant. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=150
        )
        
        # Parse the response
        result_text = response.choices[0].message.content.strip()
        try:
            result = json.loads(result_text)
            return {
                "label": result.get("label", candidate_labels[0]),
                "score": float(result.get("score", 0.5))
            }
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "label": candidate_labels[0],
                "score": 0.5
            }
            
    except Exception as e:
        # Return default result on error
        return {
            "label": candidate_labels[0] if candidate_labels else "unknown",
            "score": 0.0
        }


def df2label(df, idcol, contentcol, candidate_labels, multi_label=False):
    artls = df[contentcol].tolist()
    urls = df[idcol].tolist()

    txtls = []
    idls = []
    labells = []
    scorels = []

    for i, item in enumerate(zip(artls, urls)):
        article, url = item
        results = get_class(article, candidate_labels, multi_label)
        label = results["label"]
        score = results["score"]
        txtls.append(str(article))
        idls.append(url)
        labells.append(label)
        scorels.append(score)
        mod = (i + 1) % 10
        if mod == 0 and i > 0:
            tempdf = pd.DataFrame({"label": labells, "score": scorels, "id": idls})
            # tempdf["labels"] = tempdf["result"].apply(lambda x: x["labels"][:3])
            # tempdf["scores"] = tempdf["result"].apply(lambda x: x["scores"][:3])
            # tempdf["label"] = tempdf["labels"].apply(lambda x: x[0])
            # tempdf["label"]=tempdf["result"].apply(lambda x: x[0]["label"])
            savename = "templabel-" + str(i + 1)
            savetemp(tempdf, savename)

    # results = get_class(txtls, candidate_labels, multi_label=False)
    # tempdf = pd.DataFrame({"result": results, "id": idls})
    # tempdf["labels"] = tempdf["result"].apply(lambda x: x["labels"][:3])
    # tempdf["scores"] = tempdf["result"].apply(lambda x: x["scores"][:3])
    # tempdf["label"] = tempdf["labels"].apply(lambda x: x[0])
    tempdf = pd.DataFrame({"label": labells, "score": scorels, "id": idls})
    # tempdf1 = tempdf[["id", "labels", "scores", "label"]]
    # savename = "csrc2label" + get_nowdate()
    # savedf2(tempdf1, savename)
    return tempdf


def extract_penalty_info(text):
    """使用LLM提取行政处罚决定书关键信息"""
    try:
        # 构建提示词
        prompt = f"""你是一个文本信息抽取模型。
请从以下文本中提取以下关键信息，并以 JSON 格式输出：
  "行政处罚决定书文号",
  "被处罚当事人",
  "主要违法违规事实",
  "行政处罚依据"（以字符串形式输出所有相关条文，多个条文用分号分隔）,
  "行政处罚决定",
  "作出处罚决定的机关名称"，
  "作出处罚决定的日期"，
  "行业",
  "罚没总金额"，（数字形式，包含罚款金额和没收金额的总和）
  "违规类型"，
  "监管地区" （相关省份）。
重要提示：将输出格式化为JSON。只返回JSON响应，不添加其他评论或文本。如果返回的文本不是JSON，将视为失败。所有字段值都必须是字符串类型，不要使用数组或列表格式。

输入文本：{text}"""
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个专业的文本信息抽取助手。请严格按照要求以JSON格式返回结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        
        # 解析响应
        result_text = response.choices[0].message.content.strip()
        try:
            # 尝试解析JSON
            result = json.loads(result_text)
            return {
                "success": True,
                "data": result
            }
        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return {
                        "success": True,
                        "data": result
                    }
                except json.JSONDecodeError:
                    pass
            
            return {
                "success": False,
                "error": "无法解析LLM返回的JSON格式",
                "raw_response": result_text
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"LLM分析失败: {str(e)}"
        }


def df2penalty_analysis(df, idcol, contentcol):
    """批量处理行政处罚决定书信息提取"""
    import logging
    logger = logging.getLogger(__name__)
    
    artls = df[contentcol].tolist()
    urls = df[idcol].tolist()
    total_records = len(artls)
    
    logger.info(f"开始批量处理 {total_records} 条行政处罚决定书记录")
    
    results = []
    
    for i, (article, url) in enumerate(zip(artls, urls)):
        current_progress = i + 1
        logger.info(f"处理第 {current_progress}/{total_records} 条记录 ({(current_progress/total_records)*100:.1f}%): {url}")
        
        try:
            # 提取信息
            analysis_result = extract_penalty_info(str(article))
            
            if analysis_result["success"]:
                # 成功提取信息
                extracted_data = analysis_result["data"]
                result_row = {
                    "id": url,
                    "行政处罚决定书文号": extracted_data.get("行政处罚决定书文号", ""),
                    "被处罚当事人": extracted_data.get("被处罚当事人", ""),
                    "主要违法违规事实": extracted_data.get("主要违法违规事实", ""),
                    "行政处罚依据": extracted_data.get("行政处罚依据", ""),
                    "行政处罚决定": extracted_data.get("行政处罚决定", ""),
                    "作出处罚决定的机关名称": extracted_data.get("作出处罚决定的机关名称", ""),
                    "作出处罚决定的日期": extracted_data.get("作出处罚决定的日期", ""),
                    "行业": extracted_data.get("行业", ""),
                    "罚没总金额": extracted_data.get("罚没总金额", ""),
                    "违规类型": extracted_data.get("违规类型", ""),
                    "监管地区": extracted_data.get("监管地区", ""),
                    "analysis_status": "success"
                }
                logger.debug(f"记录 {url} 处理成功")
            else:
                # 提取失败
                result_row = {
                    "id": url,
                    "行政处罚决定书文号": "",
                    "被处罚当事人": "",
                    "主要违法违规事实": "",
                    "行政处罚依据": "",
                    "行政处罚决定": "",
                    "作出处罚决定的机关名称": "",
                    "作出处罚决定的日期": "",
                    "行业": "",
                    "罚没总金额": "",
                    "违规类型": "",
                    "监管地区": "",
                    "analysis_status": "failed",
                    "error": analysis_result.get("error", "未知错误")
                }
                logger.warning(f"记录 {url} 处理失败: {analysis_result.get('error', '未知错误')}")
        
        except Exception as e:
            # 处理异常情况
            logger.error(f"处理记录 {url} 时发生异常: {str(e)}")
            result_row = {
                "id": url,
                "行政处罚决定书文号": "",
                "被处罚当事人": "",
                "主要违法违规事实": "",
                "行政处罚依据": "",
                "行政处罚决定": "",
                "作出处罚决定的机关名称": "",
                "作出处罚决定的日期": "",
                "行业": "",
                "罚没总金额": "",
                "违规类型": "",
                "监管地区": "",
                "analysis_status": "error",
                "error": f"处理异常: {str(e)}"
            }
        
        results.append(result_row)
        
        # 每处理10条记录保存一次临时结果并记录进度
        if current_progress % 10 == 0:
            temp_df = pd.DataFrame(results)
            savename = f"penalty_analysis_temp_{current_progress}"
            savetemp(temp_df, savename)
            logger.info(f"已保存临时结果: {savename}, 当前进度: {current_progress}/{total_records}")
        
        # 每处理50条记录强制垃圾回收，释放内存
        if current_progress % 50 == 0:
            import gc
            gc.collect()
            logger.info(f"已完成 {current_progress} 条记录处理，执行内存清理")
    
    logger.info(f"批量处理完成，共处理 {total_records} 条记录")
    
    # 统计处理结果
    final_df = pd.DataFrame(results)
    success_count = len(final_df[final_df['analysis_status'] == 'success'])
    failed_count = len(final_df[final_df['analysis_status'] == 'failed'])
    error_count = len(final_df[final_df['analysis_status'] == 'error'])
    
    logger.info(f"处理结果统计: 成功 {success_count} 条, 失败 {failed_count} 条, 异常 {error_count} 条")
    
    # 返回最终结果
    return final_df
