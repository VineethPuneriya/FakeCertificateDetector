import re
import random
import time
from playwright.sync_api import sync_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
]

def verifyCoursera(certUrl):
    max_retries = 3
    
    for attempt in range(max_retries):
        if attempt > 0:
            time.sleep(random.uniform(1.5, 3.0))
            
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # INJECT RANDOM USER AGENT INTO PLAYWRIGHT CONTEXT
            context = browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = context.new_page()
            
            try:
                response = page.goto(certUrl, timeout=20000, wait_until="domcontentloaded")
                
                # Check for bot block
                if response and response.status in [403, 429]:
                    print(f"DEBUG - Coursera Anti-Bot triggered on attempt {attempt + 1}. Retrying...")
                    browser.close()
                    continue
                
                try:
                    page.wait_for_selector(".course-name-header, h3:has-text('Completed by')", timeout=10000)
                except:
                    pass
                    
                pageText = page.inner_text("body").lower()
                
                if response and response.status == 404 or "page not found" in pageText or "interesting discovery" in pageText:
                    browser.close()
                    return {"status": "Fake", "reason": "Certificate URL not found on Coursera database."}
                    
                studentName = ""
                courseName = ""
                certType = "Professional Certificate" if "professional-cert" in certUrl.lower() else "Standard Course"
                
                courseLocators = [".course-name-header", "[data-e2e='course-name']", ".course-name", "h1"]
                for loc in courseLocators:
                    try:
                        elements = page.locator(loc)
                        if elements.count() > 0:
                            courseName = elements.first.inner_text(timeout=2000).strip()
                            if courseName: break
                    except:
                        pass
                
                try:
                    nameLoc = page.locator("*:has-text('Completed by')").last
                    if nameLoc.count() > 0:
                        text = nameLoc.inner_text(timeout=2000).strip()
                        studentName = re.sub(r'(?i)^completed by\s*', '', text).strip()
                        studentName = studentName.split('\n')[0].strip()
                except:
                    pass

                if not studentName:
                    nameFallbackLocators = [".rc-CertificateRecipientName", "[data-e2e='learner-name']"]
                    for loc in nameFallbackLocators:
                        try:
                            elements = page.locator(loc)
                            if elements.count() > 0:
                                text = elements.first.inner_text(timeout=2000).strip()
                                if text and text.lower() != courseName.lower():
                                    studentName = text
                                    break
                        except:
                            pass
                
                browser.close()
                
                if studentName and courseName:
                    return {
                        "status": "Authentic",
                        "studentName": studentName,
                        "courseName": courseName,
                        "certType": certType
                    }
                    
                return {"status": "Fake", "reason": "Could not accurately scrape name from valid URL."}
                
            except Exception as e:
                print(f"DEBUG - Coursera Connection Error on attempt {attempt + 1}: {e}")
                browser.close()
                continue
                
    return {"status": "Fake", "reason": "Connection failed or timed out after multiple stealth attempts."}
