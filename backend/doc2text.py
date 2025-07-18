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


def pdfurl2txt(url, uploadpath=None):
    """Extract text from PDF using pdfplumber with automatic OCR fallback"""
    result = ""
    
    try:
        # Primary method: pdfplumber
        with pdfplumber.open(url) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    result += txt + "\n"
        
        # Check if we got meaningful text (not just whitespace/special chars)
        clean_result = result.strip().translate(str.maketrans("", "", r" \n\t\r\s"))
        
        if clean_result:
            print(f"Successfully extracted {len(result)} characters using pdfplumber")
            return result.strip()
        else:
            print("pdfplumber extracted no meaningful text, trying PyMuPDF...")
            
    except Exception as e:
        print(f"pdfplumber failed for {url}: {str(e)}")
    
    # Fallback method 1: PyMuPDF
    try:
        import fitz
        doc = fitz.open(url)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text:
                result += text + "\n"
        doc.close()
        
        # Check if PyMuPDF got meaningful text
        clean_result = result.strip().translate(str.maketrans("", "", r" \n\t\r\s"))
        
        if clean_result:
            print(f"Successfully extracted {len(result)} characters using PyMuPDF")
            return result.strip()
        else:
            print("PyMuPDF also extracted no meaningful text, falling back to OCR...")
            
    except Exception as fallback_error:
        print(f"PyMuPDF fallback failed: {str(fallback_error)}")
    
    # Fallback method 2: OCR using LLM
    if uploadpath is None:
        # Create temporary directory for OCR processing
        import tempfile
        uploadpath = tempfile.mkdtemp()
        cleanup_temp = True
    else:
        cleanup_temp = False
    
    try:
        print("Attempting OCR extraction...")
        ocr_result = pdfurl2ocr(url, uploadpath)
        
        if ocr_result and ocr_result.strip():
            print(f"Successfully extracted {len(ocr_result)} characters using OCR")
            return ocr_result.strip()
        else:
            print("OCR extraction also failed or returned no text")
            
    except Exception as ocr_error:
        print(f"OCR fallback failed: {str(ocr_error)}")
    finally:
        # Clean up temporary directory if we created it
        if cleanup_temp:
            try:
                import shutil
                shutil.rmtree(uploadpath, ignore_errors=True)
            except:
                pass
    
    print(f"All PDF text extraction methods failed for {url}")
    return ""


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
    """Extract text from image using Doubao Vision API - simplified and focused"""
    try:
        if not os.path.exists(image_file):
            print(f"Image file not found: {image_file}")
            return ""
        
        # Get the base64 string
        base64_image = encode_image(image_file)
        if not base64_image:
            print(f"Failed to encode image: {image_file}")
            return ""
        
        print(f"Attempting OCR for: {os.path.basename(image_file)}")
        
        # Use the configured vision model directly
        try:
            response = client.chat.completions.create(
                model=OPENAI_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请提取图片中的所有文字内容，包括中文和英文。只返回提取的文字，不要添加任何解释。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0
            )
            
            if response and response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content and content.strip():
                    print(f"✓ OCR successful, extracted {len(content)} characters")
                    return content.strip()
            
            print("❌ Empty response from vision model")
            return ""
            
        except Exception as api_error:
            error_msg = str(api_error)
            print(f"❌ Vision API error: {error_msg}")
            
            # Log specific error details for debugging
            if "400" in error_msg:
                print("💡 HTTP 400 - Check model name and message format")
            elif "401" in error_msg:
                print("💡 HTTP 401 - Check API key")
            elif "404" in error_msg:
                print("💡 HTTP 404 - Model not found")
            
            return ""
        
    except Exception as e:
        print(f"❌ OCR processing error: {str(e)}")
        return ""


def pdfurl2ocr(url, uploadpath):
    """Convert PDF to images and extract text using OCR - PyMuPDF preferred"""
    image_file_list = []
    text = ""
    
    try:
        # Try PyMuPDF first (no external dependencies)
        try:
            import fitz
            print(f"Using PyMuPDF for PDF to image conversion")
            
            doc = fitz.open(url)
            page_count = len(doc)
            print(f"PDF has {page_count} pages")
            
            # Convert each page to image
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                # Get pixmap with higher resolution for better OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                filename = os.path.join(uploadpath, f"page_{page_num + 1}.png")
                pix.save(filename)
                image_file_list.append(filename)
                print(f"Converted page {page_num + 1} to {filename}")
            
            doc.close()
            
        except ImportError:
            print("PyMuPDF not available, trying pdf2image...")
            # Fallback to pdf2image (requires poppler)
            try:
                from pdf2image import convert_from_path
                PDF_file = Path(url)
                pdf_pages = convert_from_path(PDF_file, 300)  # 300 DPI for good quality
                
                for page_enumeration, page in enumerate(pdf_pages, start=1):
                    filename = os.path.join(uploadpath, f"page_{page_enumeration}.jpg")
                    page.save(filename, "JPEG")
                    image_file_list.append(filename)
                    print(f"Converted page {page_enumeration} to {filename}")
                    
            except Exception as pdf2image_error:
                print(f"pdf2image failed: {str(pdf2image_error)}")
                return ""

        # Extract text from images using LLM OCR
        print(f"Starting OCR for {len(image_file_list)} images...")
        for i, image_file in enumerate(image_file_list, 1):
            try:
                print(f"Processing image {i}/{len(image_file_list)}: {os.path.basename(image_file)}")
                extracted_text = llm_ocr_text(image_file)
                if extracted_text and extracted_text.strip():
                    text += extracted_text + "\n"
                    print(f"✓ Extracted {len(extracted_text)} characters from page {i}")
                else:
                    print(f"❌ No text extracted from page {i}")
            except Exception as e:
                print(f"Error extracting text from {image_file}: {str(e)}")
            finally:
                # Clean up image file
                try:
                    os.remove(image_file)
                except OSError:
                    pass

        if text.strip():
            print(f"✅ Total OCR extraction: {len(text)} characters")
        else:
            print("❌ No text extracted from any pages")

    except Exception as e:
        print(f"Error in PDF OCR processing for {url}: {str(e)}")
        import traceback
        traceback.print_exc()
        text = ""
    
    return text.strip()


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
                # Pass uploadpath to enable automatic OCR fallback
                text = pdfurl2txt(datapath, uploadpath)

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
