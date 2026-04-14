import re
import time
import random
from playwright.sync_api import sync_playwright

userAgents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
]

def attemptCiscoScrape(url, currentUserAgent):
    studentName = ""
    courseName = ""
    issueDate = ""

    print(f"\n[DEBUG CISCO] Attempting to scrape QR URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=currentUserAgent, viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            print(f"[DEBUG CISCO] Page loaded. Final resolved URL: {page.url}")
            print(f"[DEBUG CISCO] HTTP Response Status: {response.status if response else 'Unknown'}")
            
            if response and response.status in [403, 429]:
                print(f"[DEBUG CISCO] Blocked by server.")
                browser.close()
                return {"status": "BotBlock"}

            page.wait_for_timeout(3000) # Give the page time to hydrate
            pageText = page.inner_text("body")
            htmlContent = page.content()

            print(f"[DEBUG CISCO] --- SNIPPET OF PAGE TEXT ---")
            print(pageText[:400].replace('\n', ' | '))
            print(f"[DEBUG CISCO] --------------------------")

            if "credly.com" in page.url:
                print("[DEBUG CISCO] Detected Credly backend. Applying Credly Logic.")
                try:
                    studentName = page.locator('.badge-banner-issued-to-text a').first.inner_text(timeout=3000).strip()
                except Exception as e:
                    print(f"[DEBUG CISCO] Failed to find name via Credly locator: {e}")
                    nameMatch = re.search(r'This badge was issued to\s*([A-Za-z\s]+)', pageText, re.IGNORECASE)
                    if nameMatch: studentName = nameMatch.group(1).strip()

                try:
                    courseName = page.locator('h1').first.inner_text(timeout=3000).strip()
                except Exception as e:
                    print(f"[DEBUG CISCO] Failed to find course via Credly locator: {e}")
                    courseMatch = re.search(r'(AWS Academy Graduate[^\n]+|Cisco[^\n]+)', pageText, re.IGNORECASE)
                    if courseMatch: courseName = courseMatch.group(1).strip()

                try:
                    rawDate = page.locator('p:has-text("Date issued:")').first.inner_text(timeout=3000)
                    issueDate = rawDate.replace("Date issued:", "").strip()
                except Exception as e:
                    print(f"[DEBUG CISCO] Failed to find date via Credly locator: {e}")
                    dateMatch = re.search(r'Date issued:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', pageText, re.IGNORECASE)
                    if dateMatch: issueDate = dateMatch.group(1).strip()

            else:
                print("[DEBUG CISCO] Detected native Cisco verification page. Applying generic scan.")
                nameMatch = re.search(r'(?:Name|Student|Issued to):\s*([A-Za-z\s]+)', pageText, re.IGNORECASE)
                if nameMatch: studentName = nameMatch.group(1).strip()
                
                courseMatch = re.search(r'(?:Course|Certificate of Completion for|Credential for completing)\s*([^\n]+)', pageText, re.IGNORECASE)
                if courseMatch: courseName = courseMatch.group(1).strip()

                dateMatch = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', pageText)
                if dateMatch: issueDate = dateMatch.group(1).strip()

            print(f"[DEBUG CISCO] Extracted Name: '{studentName}'")
            print(f"[DEBUG CISCO] Extracted Course: '{courseName}'")
            print(f"[DEBUG CISCO] Extracted Date: '{issueDate}'")

        except Exception as e:
            print(f"[DEBUG CISCO] Fatal Scrape Exception: {str(e)}")
            
        browser.close()
        
    if studentName and courseName:
        result = {
            "status": "Authentic",
            "studentName": studentName,
            "courseName": courseName
        }
        if issueDate: result["officialDate"] = issueDate
        return result
        
    return {"status": "Fake", "reason": "Could not parse details from Cisco URL. If URL is valid, HTML update is required."}

def verifyCisco(url):
    maxRetries = 3
    for attempt in range(maxRetries):
        currentUserAgent = random.choice(userAgents)
        result = attemptCiscoScrape(url, currentUserAgent)
        if result.get("status") == "BotBlock" or "Could not parse" in result.get("reason", ""):
            if attempt < maxRetries - 1:
                print(f"[DEBUG CISCO] Retrying... (Attempt {attempt + 2})")
                time.sleep(random.uniform(2.0, 4.0))
                continue
        return result
    return {"status": "Fake", "reason": "Failed to bypass Credly security or scrape data after multiple attempts."}