import os

import pandas as pd
import pymongo
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

mongo_connection_string = os.getenv("MONGO_DB_URL")


# Connect to the MongoDB Docker container
@st.cache_resource
def get_mongo_client():
    return pymongo.MongoClient("mongodb://localhost:27017/")


@st.cache_resource
def get_mongo_remote():
    client = pymongo.MongoClient(
        mongo_connection_string,
    )
    # db = client.test
    # Send a ping to confirm a successful connection
    try:
        client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
    return client


def get_collection(dbname, collectionname):
    # client = get_mongo_client()
    client = get_mongo_remote()
    db = client[dbname]
    collection = db[collectionname]
    return collection


# get collection by name
# def get_collection_by_name(name):
#     client = get_mongo_client()
#     db = client["test_database"]
#     collection = db[name]
#     return collection


# insert dataframes into MongoDB
def insert_data(df, collection):
    records = df.to_dict("records")
    batch_size = 10000
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        collection.insert_many(batch)


# get dataframes from MongoDB
def get_data(collection):
    # get data from MongoDB
    df = pd.DataFrame(list(collection.find()))
    return df


# delete dataframes from MongoDB
def delete_data(collection):
    collection.delete_many({})
