# backend/Dockerfile

FROM python:3.9

#RUN apt-get update -y

# install protobuf-compiler
RUN apt-get update && apt-get install -y protobuf-compiler

# install libreoffice
RUN apt-get install -y libreoffice

# install poppler-utils
RUN apt-get install -y poppler-utils

# install chinese fonts
RUN apt-get install -y ttf-wqy-zenhei ttf-wqy-microhei 

RUN pip install --no-cache-dir -U pip setuptools wheel


COPY requirements.txt app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" ,"--workers","4", "--reload"]
