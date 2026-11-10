import re
from role_data import (
    ROLE_SKILLS,
    SKILL_ALIASES,
    SKILL_GAP_SUGGESTIONS,
)

def generate_summary(roles, skills):

    top_role = roles[0][0]

    skill_text = ", ".join(skills[:8])

    return (
        f"The candidate is best suited for the role of {top_role}. "
        f"The resume demonstrates knowledge of {skill_text}."
    )
    

def get_top_skills(role, skills):
    required = ROLE_SKILLS.get(role, [])

    current = {skill.upper() for skill in skills}

    top_skills = [
        skill for skill in required
        if skill.upper() in current
    ]

    # Fallback if no role-specific skills are found
    if not top_skills:
        return skills[:5]

    return top_skills[:6]

def get_strengths(skills):

    strengths = []

    if {"react", "node", "express"} & set(skills):
        strengths.append("Full Stack Web Development")

    if "graphql" in skills or "jwt" in skills:
        strengths.append("REST API Development")

    if "docker" in skills:
        strengths.append("Containerization")

    if "git" in skills:
        strengths.append("Version Control")

    if (
        "tensorflow" in skills
        or "pytorch" in skills
        or "opencv" in skills
    ):
        strengths.append("Deep Learning & Computer Vision")

    if "mongodb" in skills or "mysql" in skills:
        strengths.append("Database Design")

    return strengths[:5]
def get_weaknesses(contact,skills):

    weaknesses=[]

    s=set(skills)

    if contact["github"]=="Not Found":
        weaknesses.append("GitHub profile missing")

    if contact["linkedin"]=="Not Found":
        weaknesses.append("LinkedIn profile missing")

    if "docker" not in s:
        weaknesses.append("Docker not mentioned")

    if "aws" not in s:
        weaknesses.append("Cloud platform experience missing")

    return weaknesses

def _normalize_role(role, role_skills):
    """Match a predicted role string to the correct ROLE_SKILLS key,
    tolerant of casing/spacing/hyphen differences."""
    if not role:
        return None

    cleaned = role.strip().lower().replace("-", " ")
    cleaned = " ".join(cleaned.split())

    for key in role_skills:
        if key.strip().lower().replace("-", " ") == cleaned:
            return key

    return None
def get_missing_skills(role, skills):
    matched_role = _normalize_role(role, ROLE_SKILLS)

    if not matched_role:
        return []

    role_data = ROLE_SKILLS[matched_role]
    required = role_data.get("required", set())
    advanced = role_data.get("advanced", set())

    current = {_normalize_skill(s) for s in (skills or []) if s}

    return sorted((required | advanced) - current)



def calculate_ats_score(score, contact, skills, text):
    ats = score
    lower = text.lower()

    # ---- Contact information ----
    email_valid = bool(contact.get("email")) and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", contact["email"])
    phone_valid = bool(contact.get("phone")) and len(re.sub(r"\D", "", contact.get("phone", ""))) >= 7

    if not email_valid:
        ats -= 5
    if not phone_valid:
        ats -= 3
    if not contact.get("linkedin"):
        ats -= 2
    if not contact.get("github"):
        ats -= 1  # optional, soft penalty

    # ---- Skills ----
    skill_count = len(skills)
    if skill_count < 8:
        ats -= 5
    elif skill_count < 12:
        ats -= 2
    elif skill_count >= 15:
        ats += 2  # bonus for a broad, well-rounded skillset

    # ---- Resume length ----
    words = len(text.split())
    if words < 150:
        ats -= 5
    elif words < 250:
        ats -= 2
    elif words > 1000:
        ats -= 2  # too long — ATS parsers often truncate

    # ---- Section presence ----
    section_keywords = {
        "skills": ["technical skills", "skills"],
        "experience": ["experience", "work history", "employment"],
        "education": ["education", "academic"],
        "projects": ["projects", "project work"],
        "certifications": ["certification", "certifications", "licenses"],
        "summary": ["summary", "objective", "profile"],
    }
    found = {name: any(kw in lower for kw in kws) for name, kws in section_keywords.items()}

    if not found["skills"]:
        ats -= 3
    if not found["experience"]:
        ats -= 4  # experience is the section ATS parsers weight most

    # Reward optional-but-valuable sections instead of just avoiding a penalty
    if found["projects"]:
        ats += 3
    if found["certifications"]:
        ats += 2
    if found["summary"]:
        ats += 1

    # ---- Quantifiable achievements ("increased revenue by 20%", "$50k saved") ----
    metric_hits = len(re.findall(r"\b\d+%|\b\d+\+|\$\d+", text))
    if metric_hits >= 3:
        ats += 3
    elif metric_hits >= 1:
        ats += 1

    # ---- Strong action verbs ----
    action_verbs = ["led", "built", "developed", "designed", "managed",
                     "implemented", "improved", "launched", "optimized", "created"]
    verb_hits = sum(1 for v in action_verbs if v in lower)
    if verb_hits >= 4:
        ats += 2
    elif verb_hits >= 2:
        ats += 1

    return max(0, min(round(ats), 100))

def recommend_roles(roles):

    result=[]

    stars=[
        "★★★★★",
        "★★★★☆",
        "★★★☆☆"
    ]

    for i,(role,prob) in enumerate(roles):

        result.append({
            "role":role,
            "rating":stars[min(i,2)],
            "confidence":round(prob*100,2)
        })

    return result



def _normalize_skill(s):
    """Skills can arrive as plain strings or (skill, category) tuples
    depending on the extractor. Also resolves known aliases (e.g. "node"
    -> "node.js") so gap-checking matches ROLE_SKILLS reliably."""
    if isinstance(s, str):
        raw = s.lower().strip()
    elif isinstance(s, (tuple, list)) and s:
        raw = str(s[0]).lower().strip()
    else:
        raw = str(s).lower().strip()

    return SKILL_ALIASES.get(raw, raw)


def ai_suggestions(contact, skills, role):
    contact = contact or {}
    skills = skills or []

    # Handle tuple role
    if isinstance(role, tuple):
        role = role[0]

    role = str(role or "Unknown").strip()

    suggestions = []

    # Normalize skills
    current = {_normalize_skill(s) for s in skills if s}

    # ---------------- Contact Suggestions ----------------
    if not contact.get("github"):
        suggestions.append("Add your GitHub profile link.")

    if not contact.get("linkedin"):
        suggestions.append("Add your LinkedIn profile link.")

    if not contact.get("email"):
        suggestions.append("Add a professional email address.")

    if not contact.get("phone"):
        suggestions.append("Add your phone number.")

    # ---------------- Role-Based Skill Suggestions ----------------
    role_data = ROLE_SKILLS.get(role)

    if role_data:
        required = role_data["required"]
        advanced = role_data["advanced"]

        missing = list(required - current) + list(advanced - current)

        for skill in missing:
            if skill in SKILL_GAP_SUGGESTIONS:
                suggestions.append(SKILL_GAP_SUGGESTIONS[skill])
            else:
                suggestions.append(
                    f"Learn {skill.title()} to strengthen your profile for a {role} role."
                )

    # Remove duplicates while preserving order
    suggestions = list(dict.fromkeys(suggestions))

    return suggestions[:5]
def analyze_resume(
    roles,
    skills,
    contact,
    score,
    text
):

    return {

        "summary":
            generate_summary(
                roles,
                skills,
            ),

        "strengths":
            get_strengths(skills),

        "weaknesses":
            get_weaknesses(contact,skills),

        "missing_skills":
            get_missing_skills(
                roles[0][0],
                skills
            ),

        "ats_score":
            calculate_ats_score(
                score,
                contact,
                skills,
                text
            ),

        "career_recommendation":
            recommend_roles(roles),

        "suggestions":
         ai_suggestions(contact, skills, roles[0][0]),
            
        "top_skills":
    get_top_skills(
        roles[0][0],
        skills
    ),
    }