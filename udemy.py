import re
import time
import os
import random
import requests
import pytesseract
from PIL import Image
from playwright.sync_api import sync_playwright

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

userAgents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
]

def verifyUdemy(certId):
    certId = certId.replace('ude.my/', '').replace('udemy.com/certificate/', '').strip()
    if not certId.startswith('UC-'):
        certId = 'UC-' + certId
        
    url = f"https://www.udemy.com/certificate/{certId}/"
    
    studentName = ""
    courseName = ""
    issueDate = ""
    hours = ""
    htmlCourseName = ""
    
    maxRetries = 3
    
    for attempt in range(maxRetries):
        if attempt > 0:
            time.sleep(random.uniform(1.5, 3.5))

        currentUserAgent = random.choice(userAgents)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=currentUserAgent
            )
            page = context.new_page()
            
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
                
                if response and response.status in [403, 429]:
                    browser.close()
                    continue

                # 1. Grab Base HTML text for Candidate Name and Date
                page.wait_for_selector('div[data-purpose="certificate-description"]', timeout=10000)
                pageText = page.inner_text("body")
                
                verifyMatch = re.search(r'verifies that\s+(.+?)\s+successfully completed the course\s+(.+?)\s+on\s+(.+?)\s+as taught by', pageText, re.IGNORECASE | re.DOTALL)
                
                if verifyMatch:
                    studentName = verifyMatch.group(1).replace('\n', ' ').strip()
                    htmlCourseName = verifyMatch.group(2).replace('\n', ' ').strip()
                    issueDate = verifyMatch.group(3).replace('\n', ' ').strip()
                    
                hoursMatch = re.search(r'(\d+(?:\.\d+)?)\s*total hours', pageText, re.IGNORECASE)
                if hoursMatch:
                    hours = hoursMatch.group(1).strip()
                    
                browser.close()
                
                # 2. Direct S3 Image Download (Bypassing HTML Search)
                jpgUrl = f"https://udemy-certificate.s3.amazonaws.com/image/{certId}.jpg"
                print(f"\n[DEBUG UDEMY] Downloading High-Res JPG for Tesseract: {jpgUrl}")
                
                headers = {
                    "User-Agent": currentUserAgent,
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Referer": url
                }
                
                imgResponse = requests.get(jpgUrl, headers=headers, timeout=15)
                
                if imgResponse.status_code == 200:
                    imgPath = f"temp_udemy_highres_{certId}.jpg"
                    with open(imgPath, 'wb') as f:
                        f.write(imgResponse.content)
                        
                    try:
                        # 3. Run Tesseract on High-Res Image
                        screenText = pytesseract.image_to_string(Image.open(imgPath))
                        
                        # Crash-proof OCR regex (accounts for O/0 and I/1 mixups)
                        courseMatchImg = re.search(r'C[O0]MPLET[I1][O0]N\s*\n+(.+?)\n+(?:Instructors?|Instructor|Reference)', screenText, re.IGNORECASE | re.DOTALL)
                        
                        if courseMatchImg:
                            ocrCourse = courseMatchImg.group(1).replace('\n', ' ').strip()
                            ocrCourse = re.sub(r'[^a-zA-Z0-9\s:,\-\+&]', '', ocrCourse).strip()
                            
                            if len(ocrCourse) > 5:
                                courseName = ocrCourse
                                print(f"[DEBUG UDEMY] Tesseract Successfully Extracted: {courseName}")
                        else:
                            print("[DEBUG UDEMY] Regex failed to match text in OCR output.")
                            
                    except Exception as e:
                        print(f"[DEBUG UDEMY] Tesseract Error: {e}")
                    finally:
                        if os.path.exists(imgPath):
                            os.remove(imgPath)
                else:
                    print(f"[DEBUG UDEMY] Failed to download image. HTTP {imgResponse.status_code}")

            except Exception as e:
                print(f"[DEBUG UDEMY] Scrape Error: {e}")
                try:
                    browser.close()
                except:
                    pass
            
        if studentName:
            if not courseName:
                print("[DEBUG UDEMY] Tesseract failed. Falling back to HTML SEO Name.")
                courseName = htmlCourseName
            break 

    if studentName and courseName:
        return {
            "status": "Authentic",
            "studentName": studentName,
            "courseName": courseName,
            "officialDate": issueDate,
            "officialHours": hours
        }
        
    return {"status": "Fake", "reason": "Could not parse official Udemy verification page. Certificate ID may be invalid or servers blocked request."}