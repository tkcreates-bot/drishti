from flask import Flask, render_template, request, jsonify
import fitz
import json
from groq import Groq
import os

 from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.jinja_env.globals.update(enumerate=enumerate)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files['report']
    
    if file.filename == '':
        return render_template("error.html")
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    
    prompt = f"""
You are Drishti, a friendly and expert medical report explainer for everyday Indian people.

Analyze this medical report and respond in this EXACT JSON format only, nothing else, no markdown:

{{
  "health_score": <number between 0-100>,
  "score_label": "<Excellent/Good/Fair/Needs Attention>",
  "patient_name": "<name if found, else Patient>",
  "summary": "<2 line overall summary>",
  "abnormal_values": [
    {{"name": "<test name>", "value": "<value>", "status": "<HIGH/LOW>", "meaning": "<1 line simple explanation>"}}
  ],
  "normal_values": [
    {{"name": "<test name>", "value": "<value>"}}
  ],
  "key_findings": ["<finding 1>", "<finding 2>", "<finding 3>"],
  "foods_to_eat": ["<food 1>", "<food 2>", "<food 3>", "<food 4>"],
  "foods_to_avoid": ["<food 1>", "<food 2>"],
  "action_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "see_doctor": <true/false>,
  "doctor_reason": "<why or why not>"
}}

Report:
{text}
"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response.choices[0].message.content
    
    try:
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
    except:
        data = {"error": True, "raw": raw}
    
    return render_template("result.html", data=data)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("question")
    context = data.get("context")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": f"""You are Drishti, a friendly medical assistant.

User's report data:
{context}

Rules:
- Answer in simple, clear English only
- Be specific and helpful
- Mention Indian healthcare options like Practo, Apollo 24/7 when relevant
- Use bullet points for clarity
- Never diagnose — explain and guide only
- Be warm and reassuring"""},
            {"role": "user", "content": question}
        ]
    )
    
    answer = response.choices[0].message.content
    return jsonify({"answer": answer})

@app.route("/general-chat")
def general_chat():
    return render_template("general_chat.html")

@app.route("/general-chat-api", methods=["POST"])
def general_chat_api():
    data = request.get_json()
    history = data.get("history", [])
    
    messages = [
        {"role": "system", "content": """You are Drishti, a friendly health assistant for Indian users.

Rules:
- Answer in simple, clear English only
- Be warm and reassuring
- Give specific actionable advice
- For serious symptoms always recommend seeing a doctor
- Mention Practo, Apollo 24/7, 1mg when relevant
- Use bullet points and bold headings
- Never diagnose — explain and guide only"""}
    ] + history
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )
    return jsonify({"answer": response.choices[0].message.content})

@app.route("/analyze-image", methods=["POST"])
def analyze_image():
    data = request.get_json()
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are Drishti, a medical report analyzer. The user has uploaded an image of their medical report. Since you cannot see images directly, ask them to type out the key values from their report and you will explain them clearly."},
            {"role": "user", "content": "I uploaded my medical report image."}
        ]
    )
    return jsonify({"answer": response.choices[0].message.content})

if __name__ == "__main__":
    app.run(debug=True)