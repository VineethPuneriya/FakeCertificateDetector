import re
import os
import fitz
import requests
import time
import random
from playwright.sync_api import sync_playwright

userAgents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
]

def attemptSaylorScrape(saylorId, currentUserAgent):
    certUrl = f"https://learn.saylor.org/admin/tool/certificate/index.php?code={saylorId}"
    
    studentName = ""
    courseName = ""
    grade = ""
    hours = ""
    issueDate = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=currentUserAgent, viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            response = page.goto(certUrl, wait_until="load", timeout=20000)
            
            if response and response.status in [403, 429]:
                browser.close()
                return {"status": "BotBlock"} 
            
            try:
                page.locator("button:has-text('Verify'), input[value='Verify']").first.click(timeout=3000)
            except:
                pass
            
            page.wait_for_timeout(3000)
            pageText = page.inner_text("body")
            
            pdfUrl = ""
            try:
                pdfUrl = page.locator("a[href$='.pdf']").first.get_attribute("href", timeout=2000)
            except:
                pass
                
            if not pdfUrl:
                pdfUrl = f"https://learn.saylor.org/pluginfile.php/1/tool_certificate/issues/1761468063/{saylorId}.pdf"

            try:
                headers = {'User-Agent': currentUserAgent}
                cookiesDict = {c['name']: c['value'] for c in context.cookies()}
                pdfResponse = requests.get(pdfUrl, headers=headers, cookies=cookiesDict, timeout=10)
                
                if pdfResponse.status_code == 200 and b"%PDF" in pdfResponse.content[:5]:
                    tempPdfPath = f"temp_official_{saylorId}.pdf"
                    with open(tempPdfPath, "wb") as f:
                        f.write(pdfResponse.content)
                        
                    doc = fitz.open(tempPdfPath)
                    officialText = ""
                    for i in range(len(doc)):
                        officialText += doc.load_page(i).get_text() + " \n "
                    doc.close()
                    if os.path.exists(tempPdfPath):
                        os.remove(tempPdfPath)
                    
                    gradeMatches = re.findall(r'\b\d{2,3}\.\d{2}\b', officialText)
                    if gradeMatches: grade = gradeMatches[-1]
                        
                    hoursMatch = re.search(r'(\d+(?:\.\d+)?)\s*Hours', officialText, re.IGNORECASE)
                    if hoursMatch: hours = hoursMatch.group(1).strip()
                        
                    dateMatch = re.search(r'(\d{1,2}\s+[A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},\s+\d{4})', officialText)
                    if dateMatch: issueDate = dateMatch.group(1).strip()
                    
                    lines = [line.strip() for line in officialText.split('\n') if line.strip()]
                    for i, line in enumerate(lines):
                        lowerLine = line.lower()
                        if "awards" in lowerLine and i + 1 < len(lines) and not studentName:
                            studentName = lines[i+1]
                        if "achievement for" in lowerLine and i + 1 < len(lines) and not courseName:
                            courseName = lines[i+1]
                            
            except Exception:
                pass

            if not studentName or not courseName:
                allCells = page.locator("td, th").all_inner_texts()
                for i, text in enumerate(allCells):
                    cleanText = text.lower().replace(':', '').strip()
                    if cleanText in ["full name", "name", "student", "student name", "participant", "issued to", "awarded to"] and i + 1 < len(allCells):
                        studentName = allCells[i+1].strip()
                    if cleanText in ["certificate", "course", "course name", "program"] and i + 1 < len(allCells):
                        courseName = allCells[i+1].strip()

                if not studentName or studentName.lower() in ["full name", "name"]:
                    m1 = re.search(r'(?:full name|name|student|issued to|awarded to)\s*[:\-]*\s*([^\n]+)', pageText, re.IGNORECASE)
                    if m1: studentName = m1.group(1).strip()
                    
                if not courseName or courseName.lower() in ["certificate", "course"]:
                    m2 = re.search(r'(?:certificate|course|program)\s*[:\-]*\s*([^\n]+)', pageText, re.IGNORECASE)
                    if m2: courseName = m2.group(1).strip()

        except Exception:
            pass
            
        browser.close()
        
    if studentName and courseName:
        result = {
            "status": "Authentic",
            "studentName": studentName,
            "courseName": courseName
        }
        if grade: result["officialGrade"] = grade
        if hours: result["officialHours"] = hours
        if issueDate: result["officialDate"] = issueDate
        return result
        
    return {"status": "Fake", "reason": "Certificate ID not found, invalid, or could not parse Saylor database."}

def verifySaylor(saylorId):
    maxRetries = 3
    
    for attempt in range(maxRetries):
        currentUserAgent = random.choice(userAgents)
        result = attemptSaylorScrape(saylorId, currentUserAgent)
        
        if result.get("status") == "BotBlock" or "not parse" in result.get("reason", "") or "not found" in result.get("reason", ""):
            if attempt < maxRetries - 1: 
                time.sleep(random.uniform(2.0, 4.0)) 
                continue
        
        return result
        
    return {"status": "Fake", "reason": "Failed to bypass Saylor security or scrape table after multiple attempts."}