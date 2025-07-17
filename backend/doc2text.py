import base64
import fnmatch
import glob
import os
import re
import subprocess
import zipfile
from pathlib import Path

import docx
import pdfplumber
import base64
import openai

# import streamlit as st
from pdf2image import convert_from_path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# uploadpath = "uploads/"




def docxurl2txt(url):
    text = ""
    try:
        doc = docx.Document(url)
        fullText = []
        for para in doc.paragraphs:
            fullText.append(para.text)
            text = "\n".join(fullText)
    except Exception as e:
        # Error in docx processing
        pass

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
        # Error in PDF processing
        pass
    return result


# Initialize OpenAI client
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

# Get model name from environment or use default
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4-vision-preview")

def encode_image(image_path):
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def llm_ocr_text(image_file):
    """Extract text from image using OpenAI Vision model"""
    try:
        # Get the base64 string
        base64_image = encode_image(image_file)
        
        response = client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please extract all text from this image. Return only the extracted text without any additional commentary or formatting. If the text is in Chinese, preserve the Chinese characters."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        # Error in OCR processing
        pass
    return ""


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
        text += llm_ocr_text(image_file)
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
        text += llm_ocr_text(image_file)
        # delete image file
        os.remove(image_file)

    return text


def picurl2ocr(url):
    text = ""
    text += llm_ocr_text(url)
    return text


def find_files(path: str, glob_pat: str, ignore_case: bool = False):
    rule = (
        re.compile(fnmatch.translate(glob_pat), re.IGNORECASE)
        if ignore_case
        else re.compile(fnmatch.translate(glob_pat))
    )
    return [
        n for n in glob.glob(os.path.join(path, "*.*"), recursive=False) if rule.match(n)
    ]


def save_uploadedfile(uploadedfile, uploadpath):
    with open(os.path.join(uploadpath, uploadedfile.name), "wb") as f:
        f.write(uploadedfile.getbuffer())
    # File upload successful
    pass


def find_libreoffice_executable():
    """Find LibreOffice executable on Windows"""
    possible_paths = [
        r"D:\LibreOffice\program\soffice.exe",  # Your custom installation path
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        r"C:\Program Files\LibreOffice 7\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice 7\program\soffice.exe",
        "soffice"  # fallback for Linux/macOS or if in PATH
    ]
    
    for path in possible_paths:
        if os.path.exists(path) or path == "soffice":
            return path
    
    return None

def convert_with_libreoffice(input_file, output_dir, soffice_path):
    """Convert document using LibreOffice with proper error handling"""
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert paths to absolute paths to avoid issues
        input_file = os.path.abspath(input_file)
        output_dir = os.path.abspath(output_dir)
        
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"Input file does not exist: {input_file}")
            return False
        
        # Check if LibreOffice executable exists
        if not os.path.exists(soffice_path):
            print(f"LibreOffice executable not found: {soffice_path}")
            return False
        
        print(f"Converting: {input_file}")
        print(f"Output dir: {output_dir}")
        print(f"Using LibreOffice: {soffice_path}")
        
        cmd = [
            soffice_path,
            "--headless",
            "--convert-to",
            "docx",
            input_file,
            "--outdir",
            output_dir,
        ]
        
        # Use shell=True on Windows to handle paths with spaces and special characters
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
            shell=True,
            cwd=output_dir  # Set working directory
        )
        
        print(f"LibreOffice return code: {result.returncode}")
        if result.stdout:
            print(f"LibreOffice stdout: {result.stdout}")
        if result.stderr:
            print(f"LibreOffice stderr: {result.stderr}")
        
        if result.returncode != 0:
            print(f"LibreOffice conversion failed for {input_file}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print(f"LibreOffice conversion timed out for {input_file}")
        return False
    except Exception as e:
        print(f"Error converting {input_file}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def docxconvertion(uploadpath):
    docdest = os.path.join(uploadpath, "doc")
    wpsdest = os.path.join(uploadpath, "wps")
    docxdest = os.path.join(uploadpath, "docx")

    # Find LibreOffice executable
    soffice_path = find_libreoffice_executable()
    if not soffice_path:
        print("LibreOffice not found. Please install LibreOffice or add it to PATH.")
        return False

    docfiles = find_files(uploadpath, "*.doc", True)
    wpsfiles = find_files(uploadpath, "*.wps", True)
    docxfiles = find_files(uploadpath, "*.docx", True)

    success = True

    for filepath in docfiles:
        if not convert_with_libreoffice(filepath, docdest, soffice_path):
            success = False

    for filepath in wpsfiles:
        if not convert_with_libreoffice(filepath, wpsdest, soffice_path):
            success = False

    for filepath in docxfiles:
        if not convert_with_libreoffice(filepath, docxdest, soffice_path):
            success = False
    
    return success


def get_uploadfiles(uploadpath):
    fileslist = glob.glob(uploadpath + "/*.*", recursive=False)
    basenamels = []
    for file in fileslist:
        basenamels.append(os.path.basename(file))
    return basenamels


def remove_uploadfiles(uploadpath):
    files = glob.glob(uploadpath + "/*.*", recursive=False)

    for f in files:
        try:
            os.remove(f)
        except OSError as e:
            # Error processing file
            pass


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
                # Processing data path
                text = docxurl2txt(datapath)
                text1 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                if text1 == "":
                    text = docxurl2ocr(datapath, uploadpath)

            elif ext.lower() == ".wps":
                # datapath = uploadpath + "wps/" + base + ".docx"
                datapath = os.path.join(uploadpath, "wps", base + ".docx")
                # Processing data path
                text = docxurl2txt(datapath)
                text1 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                if text1 == "":
                    text = docxurl2ocr(datapath, uploadpath)

            #         elif ext.lower()=='doc.docx':
            #             datapath=os.path.join(filepath,'docc',file)
            #             # Processing data path
            #             text=docxurl2txt(datapath)
            elif ext.lower() == ".docx":
                # Processing data path
                text = docxurl2txt(datapath)
                text1 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                if text1 == "":
                    datapath = os.path.join(uploadpath, "docx", file)
                    print(datapath)
                    text = docxurl2txt(datapath)
                    text2 = text.translate(str.maketrans("", "", r" \n\t\r\s"))
                    if text2 == "":
                        text = docxurl2ocr(datapath, uploadpath)

            elif ext.lower() == ".pdf":
                print(datapath)
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
                text = ""
        except Exception as e:
            # Error in file processing
            pass
            text = ""
        resls.append(text)
    return resls


# extract text from files
def extract_text(df, uploadpath):
    txtls = df["文件"].tolist()
    resls = convert_uploadfiles(txtls, uploadpath)
    df["文本"] = resls
    return df
