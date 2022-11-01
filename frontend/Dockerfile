FROM python:3.9

# install chromedriver_linux64
# RUN apt-get update && \
#     apt-get install -y gnupg wget curl unzip --no-install-recommends && \
#     wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
#     echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
#     apt-get update -y && \
#     apt-get install -y google-chrome-stable 
    #&& \
#     CHROMEVER=$(google-chrome --product-version | grep -o "[^\.]*\.[^\.]*\.[^\.]*") && \
#     DRIVERVER=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROMEVER") && \
#     wget -q --continue -P /chromedriver "http://chromedriver.storage.googleapis.com/$DRIVERVER/chromedriver_linux64.zip" && \
#     unzip /chromedriver/chromedriver* -d /chromedriver

# put chromedriver in the path
# ENV PATH /chromedriver:$PATH

# RUN apt-get update
# install libreoffice
# RUN apt-get install -y libreoffice

# install poppler-utils
# RUN apt-get install -y poppler-utils

# install chinese fonts
# RUN apt-get install -y ttf-wqy-zenhei ttf-wqy-microhei 

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -U pip setuptools wheel

# install paddlepaddle
# RUN pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple

RUN pip install --no-cache-dir -r requirements.txt 

# download the spacy model
# RUN python -m spacy download zh_core_web_lg

EXPOSE 8501

COPY . /app

ENTRYPOINT ["streamlit", "run"]

CMD ["app.py"]
