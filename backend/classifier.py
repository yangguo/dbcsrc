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
