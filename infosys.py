import json
import re
from datetime import datetime

def format_date(iso_string):
    if not iso_string: 
        return ""
    try:
        # Split at 'T' to just grab the YYYY-MM-DD
        date_part = iso_string.split('T')[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        # Format as "April 2, 2025" (avoids zero-padding like "April 02")
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    except:
        return iso_string

def verifyInfosys(qrData):
    if not qrData:
        return {"status": "Fake", "reason": "No QR Data"}

    json_str = qrData
    match = re.search(r'\{.*\}', qrData)
    if match:
        json_str = match.group(0)

    try:
        data = json.loads(json_str)
        
        subject = data.get("credentialSubject", {})
        student_name = subject.get("issuedTo", "")
        course_name = subject.get("course", "")
        
        # EXTRACT THE DATES
        completed_on = subject.get("completedOn", "")
        created_on = data.get("proof", {}).get("created", "")

        if not student_name:
            name_keys = ["name", "candidateName", "studentName", "candidate_name", "student_name", "user"]
            student_name = next((data[key] for key in name_keys if key in data), "")
        
        if not course_name:
            course_keys = ["course", "courseName", "title", "course_name", "program"]
            course_name = next((data[key] for key in course_keys if key in data), "")

        if student_name:
            return {
                "status": "Authentic",
                "studentName": str(student_name).strip(),
                "courseName": str(course_name).strip(),
                "completedDate": format_date(completed_on),
                "issuedDate": format_date(created_on)
            }
        else:
            return {"status": "Fake", "reason": "JSON missing candidate name"}

    except json.JSONDecodeError:
        return {"status": "Fake", "reason": "QR payload is not valid JSON"}