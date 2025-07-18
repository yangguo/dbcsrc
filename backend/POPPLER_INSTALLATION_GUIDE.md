# Poppler Installation Guide for Windows

The PDF processing functionality requires `poppler` to be installed on your system. Here are several ways to install it on Windows:

## Method 1: Using Conda (Recommended)

If you have Anaconda or Miniconda installed:

```bash
conda install -c conda-forge poppler
```

## Method 2: Manual Installation

1. **Download Poppler for Windows:**
   - Go to: https://github.com/oschwartz10612/poppler-windows/releases/
   - Download the latest release (e.g., `Release-23.11.0-0.zip`)

2. **Extract and Install:**
   - Extract the ZIP file to a folder like `C:\poppler`
   - The folder structure should look like:
     ```
     C:\poppler\
     ├── Library\
     │   ├── bin\      <- This contains the executables
     │   ├── include\
     │   └── lib\
     └── ...
     ```

3. **Add to System PATH:**
   - Open System Properties → Advanced → Environment Variables
   - Add `C:\poppler\Library\bin` to your system PATH
   - Restart your command prompt/IDE

## Method 3: Using Chocolatey

If you have Chocolatey package manager:

```bash
choco install poppler
```

## Method 4: Using Scoop

If you have Scoop package manager:

```bash
scoop install poppler
```

## Verification

After installation, verify that poppler is working:

```bash
# Check if poppler tools are available
pdftoppm -h
pdfinfo -h
```

## Alternative: PyMuPDF Fallback

If you can't install poppler, the code now includes a PyMuPDF fallback. Install it with:

```bash
pip install PyMuPDF==1.23.8
```

This provides basic PDF processing without requiring poppler, though OCR functionality will still need poppler for pdf2image.

## Testing Your Installation

Run the test script to verify everything is working:

```bash
cd backend
python test_pdf_processing.py
```

## Troubleshooting

### Common Issues:

1. **"poppler not found" error:**
   - Make sure poppler/bin is in your PATH
   - Restart your terminal/IDE after adding to PATH
   - Try the full path to poppler executables

2. **Permission errors:**
   - Run command prompt as administrator
   - Check folder permissions

3. **DLL errors:**
   - Make sure you downloaded the correct architecture (x64/x86)
   - Try reinstalling Visual C++ Redistributables

### Environment Variables

You can also set the poppler path directly in your code or environment:

```bash
# Set poppler path (if not in system PATH)
set POPPLER_PATH=C:\poppler\Library\bin
```

## Docker Alternative

If you're using Docker, poppler is already included in most Linux-based images:

```dockerfile
# In your Dockerfile
RUN apt-get update && apt-get install -y poppler-utils
```

## Contact

If you continue to have issues, check the project documentation or create an issue with:
- Your Windows version
- Python version
- Error messages
- Installation method attempted