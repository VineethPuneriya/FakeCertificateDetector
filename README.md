# 🛡️ CertShield - Fake Certificate Detector

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Backend-black)
![License](https://img.shields.io/badge/License-Not%20Specified-lightgrey)

An **enterprise-grade Flask web application** designed to verify the authenticity of digital e-learning certificates.
This system detects **tampered, forged, or photoshopped certificates** using a combination of **forensic analysis, OCR, cryptographic validation, and intelligent matching algorithms**.

---

## 🚀 Overview

Fake Certificate Detector is built to address the growing issue of **fraudulent educational credentials**. It leverages advanced techniques such as:

* 📄 PDF forensic inspection
* 🔍 Hybrid text extraction (native + OCR)
* 🔐 Encrypted local data caching
* 🤖 Intelligent platform detection
* 🔗 Automated certificate verification

The system is optimized for **accuracy, performance, and security**, making it suitable for **academic institutions, recruiters, and enterprise validation systems**.

---

## 🧠 Core Architecture

The application follows a modular pipeline:

1. Upload Certificate
2. Metadata Forensic Analysis
3. QR Code Extraction & Decoding
4. Text Extraction (Native + OCR Fallback)
5. Platform Auto-Detection
6. Verification via Scraping
7. Fuzzy Matching & Validation
8. Secure Caching & Result Output

---

## ⚙️ Tech Stack

### 🔹 Backend

* Python 3.9+
* Flask
* SQLAlchemy (SQLite)

### 🔹 Computer Vision & OCR

* OpenCV
* pyzbar (QR decoding)
* EasyOCR (PyTorch-based)
* PyMuPDF (`fitz`)

### 🔹 Web Scraping & Automation

* Playwright (Chromium engine)
* BeautifulSoup4
* Requests

### 🔹 Data Processing

* thefuzz (fuzzy string matching)

### 🔹 Security

* cryptography (Fernet AES-128-CBC encryption)

### 🔹 Frontend

* Vanilla HTML, CSS, JavaScript
* Custom responsive CSS grid
* Drag-and-drop file upload
* Light/Dark mode toggle (LocalStorage)
* CSS animations

---

## ✨ Key Features

### 🕵️‍♂️ Forensic Metadata Analysis

* Inspects PDF headers and metadata
* Detects modifications from tools like Photoshop, Canva, Illustrator, iLovePDF

---

### 🔍 Hybrid Text Extraction Engine

* Combines native PDF parsing with OCR fallback
* Uses a **250-character threshold** to detect flattened PDFs

---

### 🔐 Encrypted Master Cache

* Stores certificate data securely using **Fernet AES-128 encryption**
* Protects PII (names, course titles, certificate IDs)
* Reduces redundant scraping

---

### 🧠 Fuzzy String Matching

* Handles OCR inaccuracies intelligently
* Thresholds:

  * 80% (default)
  * 65% (edge cases)

---

### 🤖 Auto-Detection Engine

* Automatically detects issuing platform
* No manual input required

---

### 🔗 Direct Verification Links

* Generates official verification URLs dynamically
* Provides instant validation access

---

## 🌐 Supported Platforms

* Coursera
* Cisco Networking Academy
* AWS Academy (via Credly)
* Udemy
* Saylor Academy
* Mindluster
* Infosys Springboard
* Alison

---

## 📁 Project Structure

```
Fake-Certificate-Detector/
│
├── app.py
├── requirements.txt
├── masterCache.db
│
├── uploads/
│
├── templates/
│   └── index.html
│
├── scrapers/
│   ├── coursera.py
│   ├── udemy.py
│   ├── aws.py
│   └── ...
│
└── static/
    ├── css/
    ├── js/
    └── assets/
```

---

## 🛠️ Installation & Setup

### 🔧 System Prerequisites

#### Install ZBar (Required for QR Scanning)

* Linux:

```bash
sudo apt-get install libzbar0
```

* Mac:

```bash
brew install zbar
```

* Windows:
  Install ZBar and add it to PATH

---

#### EasyOCR Requirements

* Requires PyTorch
* GPU acceleration recommended (CUDA-enabled setup)

---

### 📥 Setup Steps

#### Clone Repository

```bash
git clone https://github.com/your-username/fake-certificate-detector.git
cd fake-certificate-detector
```

---

#### Create Virtual Environment

```bash
python -m venv venv
```

Activate:

* Windows:

```bash
venv\Scripts\activate
```

* Linux/Mac:

```bash
source venv/bin/activate
```

---

#### Install Dependencies

```bash
pip install -r requirements.txt
```

---

#### Install Playwright Browsers

```bash
playwright install chromium
```

---

#### Set Environment Variable (Encryption Key)

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Set it:

* Windows:

```bash
set CACHE_ENCRYPTION_KEY=your_generated_key
```

* Linux/Mac:

```bash
export CACHE_ENCRYPTION_KEY=your_generated_key
```

---

#### Run Application

```bash
python app.py
```

---

## 🔒 Security Considerations

* All PII is encrypted at rest
* No sensitive data stored in plaintext
* Secure caching prevents repeated scraping
* Privacy-focused design

---

## 📊 Performance Notes

* Hybrid extraction reduces OCR overhead
* Encrypted cache improves speed
* Playwright ensures reliable scraping

---

## 🧪 Future Enhancements

* ML-based forgery detection
* Blockchain certificate validation
* Enterprise API integration
* Multi-language OCR
* Batch verification

---

## 📜 License

This project currently does not have a specified license.

All rights are reserved by the author unless stated otherwise.


## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.
Your support helps improve and grow the project.

---

**Fake Certificate Detector** — Building trust in digital credentials through intelligent verification.
