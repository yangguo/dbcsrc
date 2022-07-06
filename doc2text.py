import fnmatch
import glob
import os
import re
import subprocess
import zipfile
from pathlib import Path

import docx
import numpy as np
import pdfplumber
import streamlit as st
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# uploadpath = "uploads/"

ocr = PaddleOCR(use_angle_cls=True, lang="ch")


def docxurl2txt(url):

    text = ""
    try:
        doc = docx.Document(url)
        fullText = []
        for para in doc.paragraphs:
            fullText.append(para.text)
            text = "\n".join(fullText)
    except Exception as e:
        st.error(str(e))

    return text


def pdfurl2txt(url):
    #     response = requests.get(url)
    #     source_stream = BytesIO(response.content)
    result = ""
    try:
        #         with pdfplumber.open(source_stream) as pdf:
        with pdfplumber.open(url) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt != "":
                    result += txt
    except Exception as e:
        st.error(str(e))
    return result


def paddleocr2text(image_file):
    result = ocr.ocr(image_file, cls=True)
    # print(result)
    txtls = [line[1][0] for line in result]
    #     print(txtls)
    txt = "\n".join(txtls)
    return txt


def pdfurl2ocr(url, uploadpath):
    PDF_file = Path(url)
    # Store all the pages of the PDF in a variable
    image_file_list = []
    text = ""
    # with TemporaryDirectory() as tempdir:
    pdf_pages = convert_from_path(PDF_file, 500)
    # Iterate through all the pages stored above
    for page_enumeration, page in enumerate(pdf_pages, start=1):
        # enumerate() "counts" the pages for us.

        # Create a file name to store the image
        filename = os.path.join(uploadpath, "page_" + str(page_enumeration) + ".jpg")

        # Save the image of the page in system
        page.save(filename, "JPEG")
        image_file_list.append(filename)

    # Iterate from 1 to total number of pages
    for image_file in image_file_list:
        text += paddleocr2text(image_file)
        # delete image file
        os.remove(image_file)

    return text


def docxurl2ocr(url, uploadpath):
    z = zipfile.ZipFile(url)
    all_files = z.namelist()
    images = sorted(filter(lambda x: x.startswith("word/media/"), all_files))

    # Store all the pages of the PDF in a variable
    image_file_list = []
    text = ""
    # with TemporaryDirectory() as tempdir:
    # Iterate through all the pages stored above
    for page_enumeration, image in enumerate(images):
        # enumerate() "counts" the pages for us.
        img = z.open(image).read()
        # Create a file name to store the image
        filename = os.path.basename(image)
        filepath = os.path.join(uploadpath, filename)
        #             print(filename)
        # Save the image of the page in system
        f = open(filepath, "wb")
        f.write(img)
        image_file_list.append(filepath)

    # Iterate from 1 to total number of pages
    for image_file in image_file_list:
        text += paddleocr2text(image_file)
        # delete image file
        os.remove(image_file)

    return text


def picurl2ocr(url):
    text = ""
    text += paddleocr2text(url)
    return text


def find_files(path: str, glob_pat: str, ignore_case: bool = False):
    rule = (
        re.compile(fnmatch.translate(glob_pat), re.IGNORECASE)
        if ignore_case
        else re.compile(fnmatch.translate(glob_pat))
    )
    return [
        n for n in glob.glob(os.path.join(path, "*.*"), recursive=True) if rule.match(n)
    ]


def save_uploadedfile(uploadedfile, uploadpath):
    with open(os.path.join(uploadpath, uploadedfile.name), "wb") as f:
        f.write(uploadedfile.getbuffer())
    return st.success("上传文件:{} 成功。".format(uploadedfile.name))


def docxconvertion(uploadpath):

    docdest = os.path.join(uploadpath, "doc")
    wpsdest = os.path.join(uploadpath, "wps")
    # doccdest = os.path.join(basepath,'docc')
    docxdest = os.path.join(uploadpath, "docx")

    docfiles = find_files(uploadpath, "*.doc", True)
    wpsfiles = find_files(uploadpath, "*.wps", True)
    docxfiles = find_files(uploadpath, "*.docx", True)

    for filepath in docfiles:
        st.info(filepath)
        # filename = os.path.basename(filepath)
        #     print(filename)
        #         output = subprocess.check_output(["soffice","--headless","--convert-to","docx",file,"--outdir",dest])
        subprocess.call(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "docx",
                filepath,
                "--outdir",
                docdest,
            ]
        )

    for filepath in wpsfiles:
        st.info(filepath)
        # filename = os.path.basename(filepath)
        #     print(filename)
        #         output = subprocess.check_output(["soffice","--headless","--convert-to","docx",file,"--outdir",dest])
        subprocess.call(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "docx",
                filepath,
                "--outdir",
                wpsdest,
            ]
        )

    # for filepath in doccfiles:
    #     print (filepath)
    #     filename=os.path.basename(filepath)
    # #     print(filename)
    # #         output = subprocess.check_output(["soffice","--headless","--convert-to","docx",file,"--outdir",dest])
    #     subprocess.call(['soffice', '--headless', '--convert-to', 'docx', filepath,"--outdir",doccdest])

    for filepath in docxfiles:
        st.info(filepath)
        # filename = os.path.basename(filepath)
        #     print(filename)
        #         output = subprocess.check_output(["soffice","--headless","--convert-to","docx",file,"--outdir",dest])
        subprocess.call(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "docx",
                filepath,
                "--outdir",
                docxdest,
            ]
        )


def get_uploadfiles(uploadpath):
    fileslist = glob.glob(uploadpath + "/*.*", recursive=True)
    basenamels = []
    for file in fileslist:
        basenamels.append(os.path.basename(file))
    return basenamels


def remove_uploadfiles(uploadpath):
    files = glob.glob(uploadpath + "**/*.*", recursive=True)

    for f in files:
        try:
            os.remove(f)
        except OSError as e:
            st.error("Error: %s : %s" % (f, e.strerror))


# convert all files in uploadfolder to text
def convert_uploadfiles(txtls, uploadpath):

    resls = []
    for file in txtls:
        # st.info(file)
        try:
            # datapath=file
            datapath = os.path.join(uploadpath, file)
            #     get file ext
            base, ext = os.path.splitext(file)

            if ext.lower() == ".doc":
                # datapath = uploadpath + "doc/" + base + ".docx"
                datapath = os.path.join(uploadpath, "doc", base + ".docx")
                st.info(datapath)
                text = docxurl2txt(datapath)
                text1 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                if text1 == "":
                    text = docxurl2ocr(datapath, uploadpath)

            elif ext.lower() == ".wps":
                # datapath = uploadpath + "wps/" + base + ".docx"
                datapath = os.path.join(uploadpath, "wps", base + ".docx")
                st.info(datapath)
                text = docxurl2txt(datapath)
                text1 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                if text1 == "":
                    text = docxurl2ocr(datapath, uploadpath)

            #         elif ext.lower()=='doc.docx':
            #             datapath=os.path.join(filepath,'docc',file)
            #             print(datapath)
            #             text=docxurl2txt(datapath)
            elif ext.lower() == ".docx":
                st.info(datapath)
                text = docxurl2txt(datapath)
                text1 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                if text1 == "":
                    datapath = os.path.join(uploadpath, "docx", file)
                    st.info(datapath)
                    text = docxurl2txt(datapath)
                    text2 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                    if text2 == "":
                        text = docxurl2ocr(datapath, uploadpath)

            elif ext.lower() == ".pdf":
                text = pdfurl2txt(datapath)
                text1 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                if text1 == "":
                    text = pdfurl2ocr(datapath, uploadpath)

            elif (
                ext.lower() == ".png"
                or ext.lower() == ".jpg"
                or ext.lower() == ".jpeg"
                or ext.lower() == ".bmp"
                or ext.lower() == ".tiff"
            ):
                text = picurl2ocr(datapath)
            else:
                text = np.nan
        except Exception as e:
            st.error(str(e))
            text = ""
        resls.append(text)
    return resls


# extract text from files
def extract_text(df, uploadpath):
    txtls = df["文件"].tolist()
    resls = convert_uploadfiles(txtls, uploadpath)
    df["文本"] = resls
    return df
