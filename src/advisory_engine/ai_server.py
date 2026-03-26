import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv
from src.advisory_engine.ai_mapper import OWASPLiveMapper
load_dotenv()

app = FastAPI()
mapper = OWASPLiveMapper()
categories = ", ".join(mapper.mapping.keys())

# 2. Initialize the New Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class DiffRequest(BaseModel):
    diff_text: str
    file_path: str

@app.post("/scout-risk")
async def scout_risk(request: DiffRequest):
    categories = ", ".join(mapper.mapping.keys())
    
    prompt = f"""
    Analyze this code diff for OWASP security risks. 
    File Path: {request.file_path}
    Diff:
    {request.diff_text}

    Return the result STRICTLY as a JSON object with this structure:
    {{
        "risk_level": "High/Medium/Low",
        "findings": [
            {{
                "issue": "Short name of bug",
                "reasoning": "Why it is dangerous",
                "category": "Match one from: {categories}"
            }}
        ]
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an OWASP Security Researcher. Respond only in valid JSON.",
                temperature=0.1
            )
        )
        
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        analysis = json.loads(clean_json)

        # --- MULTI-LINK FUZZY MATCH BLOCK ---
        for finding in analysis.get("findings", []):
            ai_category = finding.get("category", "")
            issue_name = finding.get("issue", "")

            # Use the Mapper to find the best link dynamically
            # We pass both category and issue name for better matching
            best_link = mapper.get_best_link(ai_category)
            
            # If the category match is weak, try matching the Issue name
            if "IndexTopTen" in best_link or "index.html" in best_link:
                best_link = mapper.get_best_link(issue_name)

            finding["owasp_link"] = best_link

        print("\n--- DEBUG: FINAL MULTI-ISSUE RESULT ---")
        print(json.dumps(analysis, indent=4))
        return analysis

    except Exception as e:
        print(f"Error during AI analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal Security Analysis Error")