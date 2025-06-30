# DBCSRC - Document Analysis and Web Crawling System

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.2.0-red.svg)](https://streamlit.io/)

## 📋 Overview

DBCSRC is a comprehensive document analysis and web crawling system designed for processing regulatory documents, extracting financial information, and performing entity analysis. The system combines web scraping capabilities with advanced document processing and machine learning-based analysis.

## ✨ Features

- **Document Processing**: Support for multiple document formats (PDF, DOCX, DOC, OFD)
- **Web Crawling**: Automated data collection from regulatory websites
- **Financial Analysis**: Extract monetary amounts and financial penalties
- **Entity Recognition**: Identify people, organizations, and locations
- **Classification**: Categorize documents using machine learning
- **Database Integration**: MongoDB support for data storage
- **Web Interface**: User-friendly Streamlit frontend
- **API Backend**: FastAPI-based REST API

## 🏗️ Architecture

The project consists of three main components:

```
├── backend/          # FastAPI backend services
├── frontend/         # Streamlit web application
└── nextjs-frontend/  # Next.js modern web interface
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- MongoDB (for database functionality)
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/dbcsrc.git
   cd dbcsrc
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

4. **Next.js Frontend Setup** (Optional)
   ```bash
   cd nextjs-frontend
   npm install
   ```

### Running the Application

1. **Start the Backend API**
   ```bash
   cd backend
   python main.py
   ```

2. **Start the Streamlit Frontend**
   ```bash
   cd frontend
   streamlit run app.py
   ```

3. **Start the Next.js Frontend** (Optional)
   ```bash
   cd nextjs-frontend
   npm run dev
   ```

### Docker Deployment

```bash
docker-compose up -d
```

## 📖 Usage

### Document Processing

1. Upload documents through the web interface
2. Select processing options (OCR, entity extraction, etc.)
3. View extracted information and analysis results

### Web Crawling

1. Configure crawling parameters
2. Start automated data collection
3. Monitor progress and review collected data

### API Usage

The backend provides REST API endpoints for:

- Document upload and processing
- Entity extraction
- Financial analysis
- Database operations

Example API call:
```python
import requests

response = requests.post(
    "http://localhost:8000/extract-amount",
    json={"content": "罚款金额为10万元"}
)
print(response.json())
```

## 🛠️ Development

### Project Structure

```
dbcsrc/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── classifier.py        # Document classification
│   ├── doc2text.py         # Document text extraction
│   ├── extractamount.py    # Financial amount extraction
│   ├── locationanalysis.py # Location entity analysis
│   ├── peopleanalysis.py   # People entity analysis
│   ├── web_crawler.py      # Web scraping functionality
│   └── utils.py            # Utility functions
├── frontend/
│   ├── app.py              # Main Streamlit app
│   ├── dbcsrc.py           # Core frontend logic
│   ├── dbcsrc2.py          # Additional frontend features
│   ├── database.py         # Database operations
│   └── utils.py            # Frontend utilities
└── nextjs-frontend/        # Modern React-based interface
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for functions and classes
- Write unit tests for new features

## 📝 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=dbcsrc

# API Keys (if needed)
OPENAI_API_KEY=your_openai_key

# Application Settings
DEBUG=False
LOG_LEVEL=INFO
```

## 🧪 Testing

Run tests using pytest:

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
pytest
```

## 📊 Performance

- Document processing: ~2-5 seconds per document
- Web crawling: Configurable rate limiting
- Database operations: Optimized with indexing
- Memory usage: ~500MB typical operation

## 🔒 Security

- Input validation on all endpoints
- Rate limiting for API calls
- Secure file upload handling
- Environment-based configuration

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- Create an [issue](https://github.com/your-username/dbcsrc/issues) for bug reports
- Start a [discussion](https://github.com/your-username/dbcsrc/discussions) for questions
- Check the [wiki](https://github.com/your-username/dbcsrc/wiki) for documentation

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the web interface
- Powered by [FastAPI](https://fastapi.tiangolo.com/) for the backend
- Document processing using [pdfplumber](https://github.com/jsvine/pdfplumber) and [python-docx](https://python-docx.readthedocs.io/)
- Machine learning capabilities with various NLP libraries

---

**Made with ❤️ for document analysis and regulatory compliance**
