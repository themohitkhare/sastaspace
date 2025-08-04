import google.generativeai as genai
import os

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

def generate_portfolio_from_data(resume_text, linkedin_data):
    prompt = f"""
Analyze the following professional data and return a JSON object.
**Do not include any preamble or explanation outside of the JSON object itself.**
The JSON object must have the following keys: "professional_summary", "skills", "formatted_experience", "formatted_education", "actionable_feedback".

- "professional_summary": A 3-4 sentence professional summary written in the first person.
- "skills": An array of the top 10-15 most relevant technical and soft skills as strings.
- "formatted_experience": An array of objects, where each object has "title", "company", "dates", and "description" keys. Convert the descriptions into 2-3 impactful bullet points, starting with action verbs.
- "formatted_education": An array of objects with "institution", "degree", and "dates" keys.
- "actionable_feedback": An array of 3-5 strings providing specific advice to improve the resume or LinkedIn profile.

Here is the data:
---
RESUME TEXT:
{resume_text}
---
LINKEDIN DATA:
{linkedin_data}
---
"""
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response.text
