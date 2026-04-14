import os
import re
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import cv2
from pyzbar.pyzbar import decode
import fitz
import easyocr
from thefuzz import fuzz
from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from cryptography.fernet import Fernet
from infosys import verifyInfosys
from coursera import verifyCoursera
from saylor import verifySaylor
from udemy import verifyUdemy
from mindluster import verifyMindluster
from alison import verifyAlison
from aws import verifyAws
from cisco import verifyCisco

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

print("Loading EasyOCR model...")
ocrReader = easyocr.Reader(['en'], gpu=True)

dbEngine = create_engine('sqlite:///masterCache.db', echo=False)
baseModel = declarative_base()

encryptionKey = os.environ.get('CACHE_ENCRYPTION_KEY', b'cw_0x689ShIjoBw6k-uE93Y3m0C-pMh_4-u08G3wDk8=')
cipherSuite = Fernet(encryptionKey)

class MasterCache(baseModel):
    __tablename__ = 'masterCache'
    cacheKey = Column(String, primary_key=True)
    platform = Column(String)
    officialData = Column(Text)

baseModel.metadata.create_all(dbEngine)
sessionMaker = sessionmaker(bind=dbEngine)

def getCachedData(cacheKey):
    dbSession = sessionMaker()
    record = dbSession.query(MasterCache).filter_by(cacheKey=cacheKey).first()
    dbSession.close()
    if record:
        try:
            decryptedData = cipherSuite.decrypt(record.officialData.encode('utf-8')).decode('utf-8')
            print(f"\n[MASTER CACHE HIT] - Returning encrypted saved data for {cacheKey} instantly!\n")
            return json.loads(decryptedData)
        except Exception as e:
            print(f"\n[MASTER CACHE ERROR] - Decryption failed for {cacheKey}: {e}\n")
            return None
    return None

def saveToCache(cacheKey, platform, data):
    if data.get("status") == "Authentic":
        dbSession = sessionMaker()
        existing = dbSession.query(MasterCache).filter_by(cacheKey=cacheKey).first()
        jsonData = json.dumps(data)
        encryptedData = cipherSuite.encrypt(jsonData.encode('utf-8')).decode('utf-8')
        if existing:
            existing.officialData = encryptedData
            print(f"\n[MASTER CACHE AUTO-HEALED] - Refreshed encrypted {platform} data for {cacheKey}\n")
        else:
            newRecord = MasterCache(cacheKey=cacheKey, platform=platform, officialData=encryptedData)
            dbSession.add(newRecord)
            print(f"\n[MASTER CACHE SAVE] - Successfully saved encrypted {platform} data for {cacheKey}\n")
        dbSession.commit()
        dbSession.close()

def normalizeText(text):
    if not text: return ""
    text = re.sub(r'[^a-z0-9\s]', ' ', text.lower())
    return re.sub(r'\s+', ' ', text).strip()

def isTextInDocument(officialText, normDoc):
    if not officialText: return False
    exactClean = normalizeText(officialText)
    if exactClean in normDoc:
        return True
    words = exactClean.split()
    cleanWords = [w for w in words if len(w) > 2]
    if not cleanWords: return False
    docWords = normDoc.split()
    for word in cleanWords:
        if word not in docWords:
            return False
    return True

def fuzzyMatcher(officialText, documentText, threshold=80):
    if not officialText: return False
    cleanOfficial = re.sub(r'[^a-z0-9\s]', ' ', officialText.lower()).strip()
    cleanDoc = re.sub(r'[^a-z0-9\s]', ' ', documentText.lower()).strip()
    matchScore = fuzz.partial_ratio(cleanOfficial, cleanDoc)
    print(f"[DEBUG APP] Fuzzy Score for '{officialText}': {matchScore}%")
    return matchScore >= threshold

def smartMatch(officialText, documentText, isOcrUsed, threshold=80):
    if not officialText: return False
    if isOcrUsed:
        print(f"[DEBUG APP] Applying Fuzzy Matcher (OCR Detected) for: {officialText}")
        return fuzzyMatcher(officialText, documentText, threshold)
    else:
        print(f"[DEBUG APP] Applying Strict Matcher (Native PDF Detected) for: {officialText}")
        normDoc = normalizeText(documentText)
        return isTextInDocument(officialText, normDoc)

def extractQrData(imagePath):
    img = cv2.imread(imagePath)
    if img is None: return None
    decodedObjects = decode(img)
    for obj in decodedObjects:
        return obj.data.decode('utf-8')
    return None

def extractTextFromImage(imagePath):
    result = ocrReader.readtext(imagePath, detail=0, paragraph=True)
    return " \n ".join(result)

def checkPdfMetadata(pdfPath):
    try:
        doc = fitz.open(pdfPath)
        meta = doc.metadata
        if not meta: return "Clean"
        prod = meta.get("producer", "").lower()
        creat = meta.get("creator", "").lower()
        blacklistedEditors = ["photoshop", "illustrator", "canva", "ilovepdf", "sejda", "pdfescape", "foxit phantom", "coreldraw", "gimp", "inkscape", "pdf24"]
        for editor in blacklistedEditors:
            if editor in prod or editor in creat:
                print(f"[DEBUG APP] Forensic Tampering Detected! Editor found: {editor}")
                return f"Fake - Document metadata indicates tampering via {editor.title()}"
        return "Clean"
    except Exception as e:
        print(f"[DEBUG APP] Metadata extraction failed: {e}")
        return "Clean"

def processPdf(pdfPath, forceOcr=False):
    doc = fitz.open(pdfPath)
    finalNativeText = ""
    finalOcrText = ""
    finalQrData = None
    for pageNum in range(len(doc)):
        page = doc.load_page(pageNum)
        nativeText = page.get_text()
        finalNativeText += nativeText + " \n "
        mat = fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat)
        tempImagePath = f"{pdfPath}_page{pageNum}.png"
        pix.save(tempImagePath)
        if not finalQrData:
            qr = extractQrData(tempImagePath)
            if qr: finalQrData = qr
        if forceOcr or len(nativeText.strip()) < 250:
            finalOcrText += extractTextFromImage(tempImagePath) + " \n "
        if os.path.exists(tempImagePath):
            os.remove(tempImagePath)
    return finalQrData, finalNativeText, finalOcrText

def requiresAutoHeal(status):
    return "Extra field:" in status

def checkAwsDate(officialDateStr, documentText):
    try:
        dt = datetime.strptime(officialDateStr, "%B %d, %Y")
        datesToCheck = [dt, dt - timedelta(days=1), dt + timedelta(days=1)]
        docNorm = documentText.lower()
        for d in datesToCheck:
            m_pad = f"{d.month:02d}"
            m_nopad = str(d.month)
            d_pad = f"{d.day:02d}"
            d_nopad = str(d.day)
            y = str(d.year)
            formats = [
                f"{m_pad}/{d_pad}/{y}",
                f"{m_nopad}/{d_nopad}/{y}",
                f"{d_pad}/{m_pad}/{y}",
                f"{d_nopad}/{m_nopad}/{y}",
                f"{y}-{m_pad}-{d_pad}",
                d.strftime("%B %d, %Y").lower(),
                d.strftime("%b %d, %Y").lower()
            ]
            for f in formats:
                if f in docNorm:
                    print(f"[DEBUG APP] Date Match Confirmed via format: {f}")
                    return True
        if normalizeText(officialDateStr) in normalizeText(documentText):
            print(f"[DEBUG APP] Date Match Confirmed via exact normalized string.")
            return True
    except Exception as e:
        print(f"[DEBUG APP] Date processing error: {e}")
    print(f"[DEBUG APP] Date Check FAILED. None of the formats matched the document.")
    return False

def evaluateAws(officialData, documentText, isOcrUsed):
    if officialData["status"] != "Authentic":
        return f"Fake - {officialData.get('reason', 'Security Violation')}"
    officialName = officialData.get("studentName", "")
    officialCourse = officialData.get("courseName", "")
    officialDate = officialData.get("officialDate", "")
    print(f"\n[DEBUG APP] Evaluating AWS Rules for Name: '{officialName}' | Date: '{officialDate}'")
    normDoc = normalizeText(documentText)
    if not isTextInDocument(officialName, normDoc):
        print("[DEBUG APP] Failed at Name match.")
        return "Fake - Candidate Name does not match official database"
    cleanOfficialCourse = re.sub(r'\s+', ' ', officialCourse.lower().strip())
    cleanDocText = re.sub(r'\s+', ' ', documentText.lower().strip())
    if cleanOfficialCourse not in cleanDocText:
        if not isTextInDocument(officialCourse, normDoc):
            print("[DEBUG APP] Failed at Strict Course match.")
            return "Fake - Certification title altered or mismatched"
        else:
            print("[DEBUG APP] Failed at Strict Course punctuation match.")
            return "Fake - Certification title altered (Punctuation/Hyphen mismatch)"
    if officialDate:
        datePattern = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', documentText)
        hasDateClaim = bool(datePattern) or "issue" in normDoc or "date" in normDoc or "earned" in normDoc
        if hasDateClaim:
            isDateMatch = checkAwsDate(officialDate, documentText)
            if not isDateMatch:
                return f"Fake - Issue Date altered (Official Date is {officialDate})"
    print("[DEBUG APP] All checks passed. Returning Genuine.")
    return "Genuine"

def evaluateCisco(officialData, documentText, isOcrUsed):
    if officialData["status"] != "Authentic":
        return f"Fake - {officialData.get('reason', 'Security Violation')}"
    officialName = officialData.get("studentName", "")
    officialCourse = officialData.get("courseName", "")
    officialDate = officialData.get("officialDate", "")
    print(f"\n[DEBUG APP] Evaluating Cisco Rules for Name: '{officialName}' | Date: '{officialDate}'")
    if not smartMatch(officialName, documentText, isOcrUsed):
        print("[DEBUG APP] Failed at Name match.")
        return "Fake - Candidate Name does not match official database"
    print(f"[DEBUG APP] Cisco Course Check Initiated (Space-Stripped Strict Match).")
    cleanOfficialCourse = re.sub(r'\s+', '', officialCourse.lower())
    cleanDocText = re.sub(r'\s+', '', documentText.lower())
    if cleanOfficialCourse not in cleanDocText:
        print("[DEBUG APP] Strict match failed, attempting OCR Fuzzy Fallback...")
        if not isOcrUsed or not fuzzyMatcher(officialCourse, documentText, threshold=80):
            print("[DEBUG APP] Failed at Course match.")
            return "Fake - Certification title altered or mismatched"
    if officialDate:
        datePattern = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2},? \d{4}', documentText.lower())
        if datePattern:
            isDateMatch = checkAwsDate(officialDate, documentText)
            print(f"[DEBUG APP] isDateMatch evaluated to: {isDateMatch}")
            if not isDateMatch:
                return f"Fake - Issue Date altered (Official Date is {officialDate})"
        else:
            print("[DEBUG APP] No Date claim detected in document. Skipping date validation.")
    print("[DEBUG APP] All checks passed. Returning Genuine.")
    return "Genuine"

def evaluateCoursera(officialData, documentText, isOcrUsed):
    if officialData["status"] != "Authentic":
        return f"Fake - {officialData.get('reason', 'Security Violation')}", "N/A"
    officialName = officialData.get("studentName", "N/A").lstrip(": ")
    officialName = re.sub(r'\s+by\s+[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}.*$', '', officialName)
    if smartMatch(officialName, documentText, isOcrUsed):
        return "Genuine", officialName
    return "Fake - Candidate Name does not match official database", officialName

def evaluateMindluster(officialData, documentText, isOcrUsed):
    if officialData["status"] != "Authentic":
        return f"Fake - {officialData.get('reason', 'Security Violation')}", "N/A", "N/A"
    officialName = officialData.get("studentName", "")
    officialCourse = officialData.get("courseName", "")
    officialStartDate = officialData.get("officialStartDate", "")
    officialDate = officialData.get("officialDate", "")
    officialHours = officialData.get("officialHours", "")
    hasStartDateClaim = bool(re.search(r'\b(start|from)\b', documentText, re.IGNORECASE))
    hasHoursClaim = bool(re.search(r'\b\d+(?:\.\d+)?\s*hours?\b', documentText, re.IGNORECASE))
    displayStartDate = officialStartDate if hasStartDateClaim and officialStartDate else "N/A"
    displayHours = officialHours if hasHoursClaim and officialHours else "N/A"
    if not smartMatch(officialName, documentText, isOcrUsed):
        return "Fake - Candidate Name does not match official database", displayStartDate, displayHours
    if not smartMatch(officialCourse, documentText, isOcrUsed):
        return "Fake - Course title altered or mismatched", displayStartDate, displayHours
    normDoc = normalizeText(documentText)
    if officialDate and normalizeText(officialDate) not in normDoc:
        return f"Fake - Issue Date altered (Official Date is {officialDate})", displayStartDate, displayHours
    if officialStartDate and hasStartDateClaim:
        if normalizeText(officialStartDate) not in normDoc:
            return f"Fake - Start Date altered (Official Start Date is {officialStartDate})", displayStartDate, displayHours
    if hasHoursClaim:
        if not officialHours:
            return "Fake - Extra field: Uploaded document claims hours, but official database does not.", displayStartDate, displayHours
        elif normalizeText(officialHours) not in normDoc:
            return f"Fake - Course Hours altered (Official Hours are {officialHours})", displayStartDate, displayHours
    return "Genuine", displayStartDate, displayHours

def evaluateSaylor(officialData, documentText, isOcrUsed):
    if officialData["status"] != "Authentic":
        return f"Fake - {officialData.get('reason', 'Security Violation')}", "N/A", "N/A"
    officialName = officialData.get("studentName", "")
    officialCourse = officialData.get("courseName", "")
    officialDate = officialData.get("officialDate")
    officialHours = officialData.get("officialHours")
    officialGrade = officialData.get("officialGrade")
    hasHoursClaim = bool(re.search(r'\b\d+(?:\.\d+)?\s*hours\b', documentText, re.IGNORECASE))
    hasGradeClaim = bool(re.search(r'\b\d{2,3}\.\d{2}\b', documentText))
    displayHours = officialHours if hasHoursClaim and officialHours else "N/A"
    displayGrade = officialGrade if hasGradeClaim and officialGrade else "N/A"
    if not smartMatch(officialName, documentText, isOcrUsed):
        return "Fake - Candidate Name does not match official database", displayHours, displayGrade
    if not smartMatch(officialCourse, documentText, isOcrUsed):
        return "Fake - Course title altered or mismatched", displayHours, displayGrade
    normDoc = normalizeText(documentText)
    if officialDate and normalizeText(officialDate) not in normDoc:
        return f"Fake - Issue Date altered (Official Date is {officialDate})", displayHours, displayGrade
    if hasHoursClaim:
        if not officialHours:
            return "Fake - Extra field: Uploaded document claims hours, but official database does not.", displayHours, displayGrade
        elif normalizeText(officialHours) not in normDoc:
            return f"Fake - Course Hours altered (Official Hours are {officialHours})", displayHours, displayGrade
    if hasGradeClaim:
        if not officialGrade:
            return "Fake - Extra field: Uploaded document claims a grade, but official database does not.", displayHours, displayGrade
        else:
            normOfficialGrade = normalizeText(officialGrade)
            if normOfficialGrade not in normDoc:
                return f"Fake - Grade altered (Official Grade is {officialGrade})", displayHours, displayGrade
    return "Genuine", displayHours, displayGrade

def evaluateAlison(officialData, documentText, isOcrUsed):
    if officialData["status"] != "Authentic":
        return f"Fake - {officialData.get('reason', 'Security Violation')}"
    officialName = officialData.get("studentName", "")
    officialCourse = officialData.get("courseName", "")
    officialDate = officialData.get("officialDate", "")
    if not smartMatch(officialName, documentText, isOcrUsed):
        return "Fake - Candidate Name does not match official database"
    if not smartMatch(officialCourse, documentText, isOcrUsed):
        return "Fake - Course title altered or mismatched"
    normDoc = normalizeText(documentText)
    if officialDate and normalizeText(officialDate) not in normDoc:
        return f"Fake - Issue Date altered (Official Date is {officialDate})"
    return "Genuine"

def evaluateUdemy(officialData, documentText, isOcrUsed):
    if officialData["status"] != "Authentic":
        return "Fake - Could not verify ID"
    officialName = officialData.get("studentName", "")
    officialCourse = officialData.get("courseName", "")
    if not smartMatch(officialName, documentText, isOcrUsed):
        return "Fake - Candidate Name does not match official database"
    print(f"\n[DEBUG APP] Udemy SEO Course Check Initiated.")
    if not fuzzyMatcher(officialCourse, documentText, threshold=65):
        return "Fake - Course title altered or mismatched"
    return "Genuine"

@app.route('/')
def homePage():
    return render_template('index.html')

@app.route('/upload_and_verify', methods=['POST'])
def uploadAndVerify():
    file = request.files.get('certificateFile')
    platformName = request.form.get('platform')
    useCache = request.form.get('useCache') == 'true'
    if not file: return jsonify({"status": "error", "message": "No file"})
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    try:
        isPdf = filename.lower().endswith('.pdf')
        if isPdf:
            metaStatus = checkPdfMetadata(filepath)
            if "Fake" in metaStatus:
                return jsonify({"status": metaStatus, "officialName": "N/A", "officialCourse": "N/A", "officialDate": "N/A", "officialHours": "N/A", "officialGrade": "N/A", "verificationLink": "N/A"})
        isOcrUsed = False
        if isPdf:
            shouldForceOcr = (platformName in ["autodetect", "udemy", "cisco"])
            qrData, nativeText, ocrText = processPdf(filepath, forceOcr=shouldForceOcr)
            if platformName in ["udemy", "cisco"]:
                documentText = nativeText + " \n " + ocrText
                isOcrUsed = True
            else:
                if len(nativeText.strip()) > 250: 
                    documentText = nativeText
                    isOcrUsed = False
                else: 
                    documentText = nativeText + " \n " + ocrText
                    isOcrUsed = True
        else:
            qrData = extractQrData(filepath)
            nativeText = ""
            ocrText = extractTextFromImage(filepath)
            documentText = ocrText
            isOcrUsed = True
        if platformName == "autodetect":
            searchData = (nativeText + " " + ocrText).lower()
            platforms = ["infosys", "coursera", "udemy", "ude.my", "saylor", "mindluster", "alison", "credly", "aws", "cisco", "networking academy"]
            if not any(p in searchData for p in platforms) and isPdf:
                print("Auto-Detect: Running background EasyOCR scan to find platform logos...")
                qrData, nativeText, ocrText = processPdf(filepath, forceOcr=True)
                searchData = (nativeText + " " + ocrText).lower()
                documentText = nativeText + " \n " + ocrText
                isOcrUsed = True
            if "onwingspan" in searchData or "infosys" in searchData: platformName = "infosys"
            elif "coursera" in searchData: platformName = "coursera"
            elif "udemy" in searchData or "ude.my" in searchData: platformName = "udemy"
            elif "saylor" in searchData: platformName = "saylor"
            elif "mindluster" in searchData: platformName = "mindluster"
            elif "alison" in searchData: platformName = "alison"
            elif "cisco" in searchData or "networking academy" in searchData: platformName = "cisco"
            elif "aws academy" in searchData: platformName = "aws"
            else:
                return jsonify({"status": "Error", "message": "Auto-detect failed. Please select manually.", "verificationLink": "N/A"})
            if platformName in ["udemy", "cisco"] and isPdf:
                documentText = nativeText + " \n " + ocrText
                isOcrUsed = True
        print(f"\n[DEBUG APP] System determined isOcrUsed = {isOcrUsed}")
        print(f"\n================ RAW NATIVE TEXT ================\n{nativeText}\n=================================================")
        print(f"\n================ RAW OCR TEXT ===================\n{ocrText}\n=================================================")
        print(f"\n================ FINAL DOC TEXT =================\n{documentText}\n=================================================")
        textNoSpacesOriginalCase = re.sub(r'\s+', '', documentText)
        if platformName == "infosys":
            useCache = False
            officialData = verifyInfosys(qrData)
            if officialData["status"] == "Authentic":
                officialName = officialData.get("studentName", "")
                officialCourse = officialData.get("courseName", "")
                officialCompleted = officialData.get("completedDate", "")
                officialIssued = officialData.get("issuedDate", "")
                normDoc = normalizeText(documentText)
                if (smartMatch(officialName, documentText, isOcrUsed) and smartMatch(officialCourse, documentText, isOcrUsed) and
                   (isTextInDocument(officialCompleted, normDoc) if officialCompleted else True) and
                   (isTextInDocument(officialIssued, normDoc) if officialIssued else True)):
                    finalStatus = "Genuine"
                else:
                    if not smartMatch(officialName, documentText, isOcrUsed):
                        finalStatus = "Fake - Candidate Name does not match QR owner"
                    elif not smartMatch(officialCourse, documentText, isOcrUsed):
                        finalStatus = "Fake - Course title altered or mismatched"
                    else:
                        finalStatus = "Fake - Details altered"
            else: finalStatus = f"Fake - {officialData.get('reason', 'Security Violation')}"
            return jsonify({"status": finalStatus, "officialName": officialData.get("studentName", "N/A"), "officialCourse": officialData.get("courseName", "N/A"), "officialCompleted": officialData.get("completedDate", "N/A"), "officialDate": officialData.get("issuedDate", "N/A"), "officialHours": "N/A", "officialGrade": "N/A", "verificationLink": qrData or "N/A"})
        elif platformName == "cisco":
            print(f"\n[DEBUG APP] Extracted QR Data for Cisco: '{qrData}'")
            if not qrData or not qrData.startswith("http"):
                return jsonify({"status": "Fake", "message": "No valid QR link found in document. The file may be compressed or missing its QR code.", "officialName": "N/A", "officialCourse": "N/A", "officialDate": "N/A", "officialHours": "N/A", "officialGrade": "N/A", "verificationLink": "N/A"})
            officialData = getCachedData(qrData) if useCache else None
            isCached = bool(officialData)
            if not isCached:
                print("[DEBUG APP] Fetching fresh Cisco data...")
                officialData = verifyCisco(qrData)
                if useCache and officialData.get("status") == "Authentic":
                    saveToCache(qrData, "cisco", officialData)
            finalStatus = evaluateCisco(officialData, documentText, isOcrUsed)
            return jsonify({"status": finalStatus, "officialName": officialData.get("studentName", "N/A"), "officialCourse": officialData.get("courseName", "N/A"), "officialDate": officialData.get("officialDate", "N/A"), "officialHours": "N/A", "officialGrade": "N/A", "verificationLink": qrData})
        elif platformName == "aws":
            match = re.search(r'(credly\.com/go/[A-Za-z0-9]+)', documentText)
            if not match: return jsonify({"status": "Fake", "message": "No valid Credly URL found in document.", "verificationLink": "N/A"})
            extractedUrl = "https://www." + match.group(1)
            print(f"\n[DEBUG APP] Extracted URL from PDF: {extractedUrl}")
            officialData = getCachedData(extractedUrl) if useCache else None
            isCached = bool(officialData)
            if not isCached:
                print("[DEBUG APP] Fetching fresh AWS data...")
                officialData = verifyAws(extractedUrl)
                if useCache and officialData.get("status") == "Authentic":
                    saveToCache(extractedUrl, "aws", officialData)
            finalStatus = evaluateAws(officialData, documentText, isOcrUsed)
            return jsonify({"status": finalStatus, "officialName": officialData.get("studentName", "N/A"), "officialCourse": officialData.get("courseName", "N/A"), "officialDate": officialData.get("officialDate", "N/A"), "officialHours": "N/A", "officialGrade": "N/A", "verificationLink": extractedUrl})
        elif platformName == "coursera":
            match = re.search(r'(coursera\.org/verify/(?:professional-cert/)?[A-Za-z0-9]{12})', textNoSpacesOriginalCase)
            if not match: return jsonify({"status": "Fake", "message": "No valid Coursera link found.", "verificationLink": "N/A"})
            extractedUrl = "https://" + match.group(1)
            officialData = getCachedData(extractedUrl) if useCache else None
            isCached = bool(officialData)
            if not isCached:
                officialData = verifyCoursera(extractedUrl)
                if useCache: saveToCache(extractedUrl, "coursera", officialData)
            finalStatus, officialName = evaluateCoursera(officialData, documentText, isOcrUsed)
            return jsonify({"status": finalStatus, "officialName": officialName, "officialCourse": officialData.get("courseName", "N/A"), "verificationLink": extractedUrl})
        elif platformName == "mindluster":
            certUrl = qrData if (qrData and "mindluster.com" in qrData.lower()) else None
            if not certUrl:
                match = re.search(r'Certified\s*No\.?\s*([A-Za-z0-9]{6,12})', documentText, re.IGNORECASE)
                if match: certUrl = f"https://www.mindluster.com/student/certificate/{match.group(1)}"
            if not certUrl: return jsonify({"status": "Fake", "message": "No valid Mindluster Link or ID found.", "verificationLink": "N/A"})
            officialData = getCachedData(certUrl) if useCache else None
            isCached = bool(officialData)
            if not isCached:
                officialData = verifyMindluster(certUrl)
                if useCache: saveToCache(certUrl, "mindluster", officialData)
            finalStatus, finalStartDate, finalHours = evaluateMindluster(officialData, documentText, isOcrUsed)
            if "Fake" in finalStatus and isCached and requiresAutoHeal(finalStatus):
                print(f"\n[CACHE MISMATCH] Extra field detected. Re-scraping {certUrl}...\n")
                freshData = verifyMindluster(certUrl)
                if freshData != officialData:
                    if useCache: saveToCache(certUrl, "mindluster", freshData)
                    officialData = freshData
                    finalStatus, finalStartDate, finalHours = evaluateMindluster(officialData, documentText, isOcrUsed)
            return jsonify({"status": finalStatus, "officialName": officialData.get("studentName", "N/A"), "officialCourse": officialData.get("courseName", "N/A"), "officialStartDate": finalStartDate, "officialDate": officialData.get("officialDate", "N/A"), "dateFormat": "(YYYY-MM-DD)", "officialHours": finalHours, "officialGrade": "N/A", "verificationLink": certUrl})
        elif platformName == "saylor":
            saylorId = None
            match = re.search(r'(?:certificate\s*id:?|code=)\s*([A-Za-z0-9]{10,15})', documentText, re.IGNORECASE)
            if match: saylorId = match.group(1)
            else:
                for word in documentText.split():
                    cleanWord = re.sub(r'[^A-Za-z0-9]', '', word)
                    if 10 <= len(cleanWord) <= 15 and any(c.isdigit() for c in cleanWord) and any(c.isalpha() for c in cleanWord):
                        saylorId = cleanWord; break
            if not saylorId: return jsonify({"status": "Fake", "message": "No valid Saylor ID found.", "verificationLink": "N/A"})
            officialData = getCachedData(saylorId) if useCache else None
            isCached = bool(officialData)
            if not isCached:
                officialData = verifySaylor(saylorId)
                if useCache: saveToCache(saylorId, "saylor", officialData)
            finalStatus, finalHours, finalGrade = evaluateSaylor(officialData, documentText, isOcrUsed)
            if "Fake" in finalStatus and isCached and requiresAutoHeal(finalStatus):
                print(f"\n[CACHE MISMATCH] Extra field detected. Re-scraping Saylor ID: {saylorId}...\n")
                freshData = verifySaylor(saylorId)
                if freshData != officialData:
                    if useCache: saveToCache(saylorId, "saylor", freshData)
                    officialData = freshData
                    finalStatus, finalHours, finalGrade = evaluateSaylor(officialData, documentText, isOcrUsed)
            return jsonify({"status": finalStatus, "officialName": officialData.get("studentName", "N/A"), "officialCourse": officialData.get("courseName", "N/A"), "officialDate": officialData.get("officialDate", "N/A"), "officialHours": finalHours, "officialGrade": finalGrade, "verificationLink": f"https://learn.saylor.org/admin/tool/certificate/index.php?code={saylorId}"})
        elif platformName == "alison":
            certUrl = qrData if (qrData and "alison.com" in qrData.lower()) else None
            if not certUrl: return jsonify({"status": "Fake", "message": "No valid Alison Link found.", "verificationLink": "N/A"})
            officialData = getCachedData(certUrl) if useCache else None
            isCached = bool(officialData)
            if not isCached:
                officialData = verifyAlison(certUrl)
                if useCache: saveToCache(certUrl, "alison", officialData)
            finalStatus = evaluateAlison(officialData, documentText, isOcrUsed)
            return jsonify({"status": finalStatus, "officialName": officialData.get("studentName", "N/A"), "officialCourse": officialData.get("courseName", "N/A"), "officialCompleted": "N/A", "officialStartDate": "N/A", "officialDate": officialData.get("officialDate", "N/A"), "officialHours": officialData.get("officialHours", "N/A"), "officialGrade": "N/A", "verificationLink": certUrl})
        elif platformName == "udemy":
            rawIds = re.findall(r'(UC-[A-Za-z0-9\-]{30,})', documentText, re.IGNORECASE)
            if not rawIds: return jsonify({"status": "Fake", "message": "No valid Udemy ID found.", "verificationLink": "N/A"})
            cleanedIds = list(set([uid[:3] + uid[3:].replace('O','0').replace('o','0').replace('l','1').replace('I','1').replace('i','1').replace('S','5').replace('s','5').lower() for uid in rawIds]))
            officialData = None
            isValidIdFound = False
            usedId = ""
            if useCache:
                for candidateId in cleanedIds:
                    cachedData = getCachedData(candidateId)
                    if cachedData:
                        officialData = cachedData
                        isValidIdFound = True
                        usedId = candidateId
                        break
            if not isValidIdFound:
                for candidateId in cleanedIds:
                    officialData = verifyUdemy(candidateId)
                    if officialData.get("status") == "Authentic":
                        if useCache: saveToCache(candidateId, "udemy", officialData)
                        isValidIdFound = True
                        usedId = candidateId
                        break
            if not isValidIdFound:
                return jsonify({"status": "Fake - Could not verify Udemy ID.", "officialName": "N/A", "officialCourse": "N/A", "officialDate": "N/A", "officialHours": "N/A", "officialGrade": "N/A", "verificationLink": "N/A"})
            finalStatus = evaluateUdemy(officialData, documentText, isOcrUsed)
            return jsonify({"status": finalStatus, "officialName": officialData.get("studentName", "N/A"), "officialCourse": officialData.get("courseName", "N/A"), "officialDate": officialData.get("officialDate", "N/A"), "dateFormat": "(MM/DD/YYYY)", "officialHours": "N/A", "officialGrade": "N/A", "verificationLink": f"https://www.udemy.com/certificate/{usedId}/"})
        return jsonify({"status": "error", "message": "Platform not configured."})
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True) 