import requests
import re
import random
import time

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
]

def verifyAlison(certUrl):
    if not certUrl:
        return {"status": "Fake", "reason": "No verification link provided."}
        
    max_retries = 3
    for attempt in range(max_retries):
        try:
            stealth_headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            if attempt > 0:
                time.sleep(random.uniform(1.0, 2.5))
                
            response = requests.get(certUrl, headers=stealth_headers, timeout=15)
            
            if response.status_code in [403, 429]:
                print(f"DEBUG - Alison Anti-Bot triggered on attempt {attempt + 1}. Retrying...")
                continue
                
            if response.status_code != 200:
                return {"status": "Fake", "reason": "Alison verification link returned an error."}

            html = response.text

            studentName = ""
            courseName = ""
            issueDate = ""
            hours = ""
            score = ""

            # 1. Extract Name
            name_match = re.search(r'<span class="blue-label">(.*?)</span>', html, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r'<h3>(.*?)</h3>', html, re.IGNORECASE)
            if name_match: studentName = name_match.group(1).strip()

            # 2. Extract Course
            course_match = re.search(r'<span>Course Completed:</span>\s*(.*?)\s*</p>', html, re.IGNORECASE)
            if course_match: courseName = course_match.group(1).strip()

            # 3. Extract Date
            date_match = re.search(r'<span>Date of Completion:</span>\s*(.*?)\s*</p>', html, re.IGNORECASE)
            if date_match: issueDate = date_match.group(1).strip()

            # 4. Extract Hours
            hours_match = re.search(r'<span>Total Study Time:</span>\s*(.*?)\s*</p>', html, re.IGNORECASE)
            if hours_match: hours = hours_match.group(1).strip()

            # 5. Extract Score
            score_match = re.search(r'Final Assessment Score.*?<div class="right">\s*([^<]+)\s*</div>', html, re.IGNORECASE | re.DOTALL)
            if score_match: score = score_match.group(1).strip()

            if studentName and courseName:
                return {
                    "status": "Authentic",
                    "studentName": studentName,
                    "courseName": courseName,
                    "officialDate": issueDate,
                    "officialHours": hours,
                    "officialGrade": score
                }
                
            return {"status": "Fake", "reason": "Could not extract verification details from Alison."}

        except Exception as e:
            print(f"DEBUG - Alison Network Error on attempt {attempt + 1}: {e}")
            continue

    return {"status": "Fake", "reason": "Connection failed after multiple stealth attempts."}
