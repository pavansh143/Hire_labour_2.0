import os
import re
import base64
import json
import numpy as np
import cv2
import pytesseract
import google.generativeai as genai
from flask import Flask, request, jsonify
from PIL import Image
import io

# ─── Try importing face_recognition (optional, legacy) ──────────────────────
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("[WARN] face_recognition not installed. Legacy /verify endpoint will return defaults.")

app = Flask(__name__)

# ─── Configure Gemini ────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_AVAILABLE = True
    print("[OK] Google Gemini configured successfully.")
else:
    GEMINI_AVAILABLE = False
    print("[WARN] GEMINI_API_KEY not set. /validate-registration will return safe defaults.")

# ─── Tesseract (optional) ────────────────────────────────────────────────────
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ════════════════════════════════════════════════════════════════════════════
# HELPER: Build the Gemini system prompt
# ════════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """
ROLE & OBJECTIVE:
You are the core AI Security and Validation engine for a multi-role Hire Labour marketplace.
Your job is to analyze incoming registration data and selfie images to authenticate real human
laborers, validate their professional profiles, and eliminate fraud/fake profiles.

TASK 1: FACE DETECTION & ANTI-SPOOFING (IMAGE ANALYSIS)
Analyze the provided selfie image for:
1. Liveness Detection: Is this a live capture of a real human being? Look for signs of spoofing
   such as digital screen borders, paper edges (holding up a physical photo), printed photo
   textures, or heavy digital manipulation/deepfakes.
2. Clarity: Is the face clearly visible, well-lit, and not heavily obscured by filters, masks,
   or extreme angles?
3. Verdict: Issue a PASSED or FAILED status for physical identity.

TASK 2: PROFILE & SKILL VALIDATION (TEXT ANALYSIS)
Analyze the provided registration text data (Name, Bio, Skills, Experience):
1. Consistency Check: Do the claimed skills match the background description?
2. Spam & Fake Detection: Identify gibberish text, keyboard smashes, offensive language,
   or placeholder text.
3. Professionalism: Rate whether the profile description is legitimate enough to be shown
   to employers.

CRITICAL OUTPUT RULE:
Return ONLY raw JSON — no markdown, no code fences, no explanation text.
Use exactly this structure:
{
  "authentication": {
    "face_verified": true,
    "liveness_detected": true,
    "confidence_score": 0.00,
    "anti_spoofing_notes": "Reasoning here."
  },
  "validation": {
    "profile_legitimate": true,
    "spam_detected": false,
    "data_quality_score": 0.00,
    "validation_notes": "Reasoning here."
  },
  "final_action": "ALLOW_REGISTRATION"
}
final_action must be exactly "ALLOW_REGISTRATION" or "REJECT_REGISTRATION".
"""

def build_user_message(full_name, bio, skills, experience):
    return f"""
Please analyze the following registration submission:

PROFILE TEXT DATA:
- Full Name: {full_name or 'Not provided'}
- Skills: {skills or 'Not provided'}
- Bio / Description: {bio or 'Not provided'}
- Years of Experience: {experience or 'Not provided'}

Also analyze the attached selfie image for liveness and anti-spoofing.

Return ONLY the raw JSON object as specified. Do not wrap in markdown.
""".strip()


def run_gemini_validation(image_bytes, full_name, bio, skills, experience):
    """Send image + text to Gemini and parse the JSON response."""
    if not GEMINI_AVAILABLE:
        return _default_validation_response("Gemini API key not configured on server.")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Encode image for Gemini
        img_part = {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(image_bytes).decode("utf-8")
        }

        user_text = build_user_message(full_name, bio, skills, experience)

        response = model.generate_content(
            [SYSTEM_PROMPT, img_part, user_text]
        )

        raw_text = response.text.strip()

        # Strip markdown code fences if Gemini wraps in them anyway
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r'\s*```$', '', raw_text, flags=re.MULTILINE)
        raw_text = raw_text.strip()

        result = json.loads(raw_text)
        return result

    except json.JSONDecodeError as je:
        print(f"[ERROR] Gemini JSON parse failed: {je}\nRaw response: {raw_text}")
        return _default_validation_response(f"JSON parse error: {je}")
    except Exception as e:
        print(f"[ERROR] Gemini call failed: {e}")
        return _default_validation_response(str(e))


def _default_validation_response(reason):
    """Returns a safe fallback when Gemini is unavailable."""
    return {
        "authentication": {
            "face_verified": False,
            "liveness_detected": False,
            "confidence_score": 0.0,
            "anti_spoofing_notes": f"AI service unavailable: {reason}"
        },
        "validation": {
            "profile_legitimate": True,
            "spam_detected": False,
            "data_quality_score": 0.5,
            "validation_notes": "Profile text could not be validated (AI offline). Defaulting to manual review."
        },
        "final_action": "ALLOW_REGISTRATION"
    }


# ════════════════════════════════════════════════════════════════════════════
# NEW ENDPOINT: /validate-registration  (Gemini-powered)
# ════════════════════════════════════════════════════════════════════════════
@app.route('/validate-registration', methods=['POST'])
def validate_registration():
    """
    Accepts multipart/form-data:
      - selfie: image file (required)
      - full_name: string
      - bio: string
      - skills: string
      - experience: string
    Returns the Gemini JSON result directly.
    """
    selfie_file = request.files.get('selfie')
    full_name   = request.form.get('full_name', '')
    bio         = request.form.get('bio', '')
    skills      = request.form.get('skills', '')
    experience  = request.form.get('experience', '')

    if not selfie_file:
        return jsonify({"error": "selfie image is required"}), 400

    # Read and normalize image bytes to JPEG
    try:
        img_bytes_raw = selfie_file.read()
        pil_img = Image.open(io.BytesIO(img_bytes_raw)).convert("RGB")
        # Resize to max 1024px to stay within Gemini token limits
        pil_img.thumbnail((1024, 1024))
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        image_bytes = buf.getvalue()
    except Exception as e:
        return jsonify({"error": f"Could not process image: {e}"}), 400

    result = run_gemini_validation(image_bytes, full_name, bio, skills, experience)
    return jsonify(result)


# ════════════════════════════════════════════════════════════════════════════
# LEGACY ENDPOINTS (preserved for backward-compatibility)
# ════════════════════════════════════════════════════════════════════════════
def extract_aadhaar(image_path):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        match = re.search(r'\d{4}\s\d{4}\s\d{4}', text)
        if match:
            return match.group(0).replace(" ", "")
        return None
    except Exception as e:
        print(f"[OCR Error] {e}")
        return None


@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    id_card_path   = data.get('id_card_path')
    selfie_path    = data.get('selfie_path')
    input_aadhaar  = data.get('input_aadhaar')

    root_path      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_id_path   = os.path.join(root_path, id_card_path) if id_card_path else None
    full_selfie_path = os.path.join(root_path, selfie_path) if selfie_path else None

    extracted_aadhaar = extract_aadhaar(full_id_path) if full_id_path else None
    face_matched      = False
    face_encoding_str = ""

    if FACE_RECOGNITION_AVAILABLE and full_id_path and full_selfie_path:
        try:
            id_img      = face_recognition.load_image_file(full_id_path)
            selfie_img  = face_recognition.load_image_file(full_selfie_path)
            id_enc      = face_recognition.face_encodings(id_img)
            selfie_enc  = face_recognition.face_encodings(selfie_img)
            if id_enc and selfie_enc:
                results = face_recognition.compare_faces([id_enc[0]], selfie_enc[0], tolerance=0.6)
                face_matched = bool(results[0])
                face_encoding_str = ",".join(map(str, selfie_enc[0].tolist()))
        except Exception as e:
            print(f"[Face Error] {e}")

    ocr_match   = bool(extracted_aadhaar and input_aadhaar and extracted_aadhaar == input_aadhaar)
    trust_score = 0
    if face_matched:      trust_score += 50
    if ocr_match:         trust_score += 40
    if extracted_aadhaar: trust_score += 10

    return jsonify({
        "ocr_match":          ocr_match,
        "face_match":         face_matched,
        "trust_score":        trust_score,
        "extracted_aadhaar":  extracted_aadhaar,
        "face_encoding":      face_encoding_str
    })


@app.route('/check-duplicate', methods=['POST'])
def check_duplicate():
    if not FACE_RECOGNITION_AVAILABLE:
        return jsonify({"is_duplicate": False})

    data = request.json
    new_enc_raw = data.get('new_encoding', '')
    if not new_enc_raw:
        return jsonify({"is_duplicate": False})

    new_encoding = np.array(list(map(float, new_enc_raw.split(','))))
    existing_encodings_raw = data.get('existing_encodings', [])

    for item in existing_encodings_raw:
        if not item.get('encoding'):
            continue
        ex_enc = np.array(list(map(float, item['encoding'].split(','))))
        match = face_recognition.compare_faces([ex_enc], new_encoding, tolerance=0.5)
        if match[0]:
            return jsonify({"is_duplicate": True, "duplicate_id": item['id']})

    return jsonify({"is_duplicate": False})


# ─── Health check ────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status":           "running",
        "gemini_available": GEMINI_AVAILABLE,
        "face_recognition": FACE_RECOGNITION_AVAILABLE
    })


if __name__ == '__main__':
    app.run(port=5001, debug=True)
