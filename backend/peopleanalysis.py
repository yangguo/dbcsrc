import openai
import os
import json
from utils import savetemp

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
    api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

# Get model name from environment or use default
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

def text2schema(text, topic):
    """Extract entities using OpenAI LLM"""
    txtls = []
    if text != "":
        try:
            # Create prompt for entity extraction
            prompt = f"""Extract all {topic} (persons, organizations, or responsible persons) from the following Chinese text.
            
Text: {text}
            
Respond with only a JSON array of extracted entities. For example:
            ["entity1", "entity2", "entity3"]
            
If no entities are found, respond with an empty array: []
            
Entity type to extract: {topic}
            - 个人: Extract person names
            - 单位: Extract organization/company names  
            - 负责人: Extract names of responsible persons/leaders"""
            
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert in Chinese named entity recognition. Always respond with valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            # Parse the response
            result_text = response.choices[0].message.content.strip()
            try:
                entities = json.loads(result_text)
                if isinstance(entities, list):
                    txtls = entities
            except json.JSONDecodeError:
                pass
                
        except Exception as e:
            pass
            
    return txtls


def df2people(df, idcol, peoplecol):
    df1 = df[[idcol, peoplecol]]

    idls = []
    peoplels = []
    orgls = []
    start = 0
    for i in range(start, len(df1)):
        id = df1.iloc[i][idcol]
        content = df1.iloc[i][peoplecol]
        people = text2schema(str(content), "个人")
        org = text2schema(str(content), "单位")
        idls.append(id)
        peoplels.append(people)
        orgls.append(org)

        if (i + 1) % 10 == 0 and i > start:
            tempdf = get_pandas().DataFrame({"id": idls, "peoplels": peoplels, "orgls": orgls})
            savename = "temppeople-" + str(i) + ".csv"
            savetemp(tempdf, savename)

    resdf = get_pandas().DataFrame({"id": idls, "peoplels": peoplels, "orgls": orgls})
    resdf.loc[:, "org"] = resdf["orgls"].apply(lambda x: x[0] if len(x) > 0 else "")
    # savename = "temppeople-" + str(i)+'.csv'
    return resdf
