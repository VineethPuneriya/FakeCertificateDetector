import re
import os
import requests
import pytesseract
from PIL import Image
import io
import random
import time

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
]

def verifyMindluster(certUrl):
    certId = certUrl.split('/')[-1]
    if not certId:
        return {"status": "Fake", "reason": "Invalid Mindluster URL format."}

    imageUrl = f"https://www.mindluster.com/storage/cer/{certId}.jpg"
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            stealth_headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            if attempt > 0:
                time.sleep(random.uniform(1.0, 2.5))
                
            response = requests.get(imageUrl, headers=stealth_headers, timeout=15)
            
            if response.status_code in [403, 429]:
                print(f"DEBUG - Mindluster Anti-Bot triggered on attempt {attempt + 1}. Retrying...")
                continue
                
            if response.status_code != 200:
                return {"status": "Fake", "reason": "Certificate ID not found on Mindluster server."}

            image = Image.open(io.BytesIO(response.content))
            screenText = pytesseract.image_to_string(image)
            
            studentName = ""
            courseName = ""
            startDate = ""
            issueDate = ""
            hours = ""

            nameMatch = re.search(r'presented to\s*\n+([A-Za-z\s]+)\n+for successfully', screenText, re.IGNORECASE)
            if nameMatch: studentName = nameMatch.group(1).replace('\n', ' ').strip()

            courseMatch = re.search(r'Course about\s*\n+([^\n]+)', screenText, re.IGNORECASE)
            if courseMatch: courseName = courseMatch.group(1).replace('\n', ' ').strip()

            startMatch = re.search(r'Course Start Date[\s:]*(\d{4}-\d{2}-\d{2})', screenText, re.IGNORECASE)
            if startMatch: startDate = startMatch.group(1).strip()

            allDates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', screenText)
            if allDates: issueDate = allDates[-1]

            hoursMatch = re.search(r'Duration[\s:]*(\d+\s*hour[s]?)', screenText, re.IGNORECASE)
            if hoursMatch: hours = hoursMatch.group(1).strip()
                
            if studentName and courseName:
                return {
                    "status": "Authentic",
                    "studentName": studentName,
                    "courseName": courseName,
                    "officialStartDate": startDate,
                    "officialDate": issueDate,
                    "officialHours": hours
                }
                
            return {"status": "Fake", "reason": "Could not accurately OCR the verification image."}

        except Exception as e:
            print(f"DEBUG - Mindluster Network Error on attempt {attempt + 1}: {e}")
            continue

    return {"status": "Fake", "reason": "Connection failed after multiple stealth attempts."}
