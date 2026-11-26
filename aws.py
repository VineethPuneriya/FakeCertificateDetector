import re
import time
import random
from playwright.sync_api import sync_playwright

userAgents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
]

def attemptCredlyScrape(url, currentUserAgent):
    studentName = ""
    courseName = ""
    issueDate = ""

    print(f"\n[DEBUG AWS/CREDLY] Attempting to scrape URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=currentUserAgent, viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            # domcontentloaded stops the infinite timeout loops
            response = page.goto(url, wait_until="domcontentloaded", timeout=25000)
            
            if response and response.status in [403, 429]:
                print(f"[DEBUG AWS/CREDLY] Blocked by server. Status code: {response.status}")
                browser.close()
                return {"status": "BotBlock"}

            # Give Javascript 2 seconds to render the badge details
            page.wait_for_timeout(2000)
            
            htmlContent = page.content()
            pageText = page.inner_text("body")
            
            if "not found" in pageText.lower() or "invalid" in pageText.lower():
                print("[DEBUG AWS/CREDLY] Page loaded, but Credly says badge is Not Found.")
                browser.close()
                return {"status": "Fake", "reason": "Badge not found or invalid on Credly database."}

            # 1. Extract Name using highly robust Regex on the raw HTML
            nameMatch = re.search(r'This badge was issued to\s*<a[^>]*>([^<]+)</a>', htmlContent, re.IGNORECASE)
            if not nameMatch:
                nameMatch = re.search(r'This badge was issued to\s*([A-Za-z\s]+)', pageText, re.IGNORECASE)
            if nameMatch:
                studentName = nameMatch.group(1).strip()

            # 2. Extract Course
            courseMatch = re.search(r'<h1[^>]*ac-heading--badge-name-hero[^>]*>(.*?)</h1>', htmlContent, re.IGNORECASE)
            if not courseMatch:
                courseMatch = re.search(r'(AWS Academy Graduate[^\n]+)', pageText, re.IGNORECASE)
            if courseMatch:
                courseName = courseMatch.group(1).strip()

            # 3. Extract Date
            dateMatch = re.search(r'Date issued:\s*([^<]+)<', htmlContent, re.IGNORECASE)
            if not dateMatch:
                dateMatch = re.search(r'Date issued:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', pageText, re.IGNORECASE)
            if dateMatch:
                issueDate = dateMatch.group(1).strip()

            print(f"[DEBUG AWS/CREDLY] Extracted Name: '{studentName}'")
            print(f"[DEBUG AWS/CREDLY] Extracted Course: '{courseName}'")
            print(f"[DEBUG AWS/CREDLY] Extracted Date: '{issueDate}'")

        except Exception as e:
            print(f"[DEBUG AWS/CREDLY] Fatal Scrape Exception: {str(e)}")
            
        browser.close()
        
    if studentName and courseName:
        result = {
            "status": "Authentic",
            "studentName": studentName,
            "courseName": courseName
        }
        if issueDate: result["officialDate"] = issueDate
        return result
        
    return {"status": "Fake", "reason": "Could not parse details from official Credly database. Link may be invalid."}


def verifyAws(credlyUrl):
    maxRetries = 3
    
    for attempt in range(maxRetries):
        currentUserAgent = random.choice(userAgents)
        result = attemptCredlyScrape(credlyUrl, currentUserAgent)
        
        if result.get("status") == "BotBlock" or "Could not parse" in result.get("reason", ""):
            if attempt < maxRetries - 1:
                print(f"[DEBUG AWS/CREDLY] Retrying... (Attempt {attempt + 2})")
                time.sleep(random.uniform(2.0, 4.0))
                continue
                
        return result
        
    return {"status": "Fake", "reason": "Failed to bypass Credly security or scrape data after multiple attempts."}
