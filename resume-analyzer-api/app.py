from flask import Flask, request, jsonify
from utils import *
from ai_analysis import analyze_resume

app = Flask(__name__)

@app.route("/")
def home():
    return {"message": "API running 🚀"}

@app.route("/analyze", methods=["POST"])
def analyze():

    if "file" not in request.files:
        return jsonify({"error": "Upload a PDF"}), 400

    file = request.files["file"]

    # Extract resume text
    text = extract_text_from_pdf(file)

    # Extract information
    skills = extract_skills(text)
    soft_skills = extract_all_soft_skills(text)
    contact = extract_contact_info(text,file)

    # Predict roles
    roles = predict_roles(text)
    roles = adjust_roles_soft(skills, roles, text)
    predicted_role = roles[0] if roles else "Unknown"


    # Resume score
    score = calculate_score(
    skills,
    text,
    contact,
    predicted_role
)

    # AI analysis
    analysis = analyze_resume(
        roles,
        skills,
        contact,
        score,
        text
    )

    return jsonify({
        "roles": roles,
        "skills": skills,
        "soft_skills": soft_skills,
        "contact": contact,
        "resume_score": score,
        "analysis": analysis,
        "resumeText": text
    })
if __name__ == "__main__":
    app.run(debug=True)