from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Admin, Labour, Public, Feedback, Message, WorkShowcase
from werkzeug.utils import secure_filename
import os
from sqlalchemy import func
from difflib import SequenceMatcher, get_close_matches

# Optional AI Dependencies
try:
    import cv2
    import pytesseract
    import face_recognition
    import numpy as np
    AI_ENABLED = True
except ImportError:
    AI_ENABLED = False
    print("WARNING: AI dependencies (opencv, face_recognition, pytesseract) not found. AI features will be disabled.")

import re

# ── NLP AI Search Engine ──────────────────────
# Load Gemini API Key from the node .env file
GEMINI_SEARCH_ENABLED = False
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hire_labour_node', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    gemini_key = os.environ.get('GEMINI_API_KEY', '')
    if gemini_key and gemini_key != 'your_gemini_api_key_here':
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        GEMINI_SEARCH_ENABLED = True
        print("[OK] Gemini NLP Search Engine: ACTIVE")
    else:
        print("[WARN] Gemini NLP Search: DISABLED (no valid API key found)")
except Exception as e:
    print(f"[WARN] Gemini NLP Search: DISABLED ({e})")

# Master list of known services on the platform
KNOWN_SERVICES = [
    'Electrician', 'Plumber', 'Carpenter', 'Painter', 'Mason',
    'Housekeeping', 'AC Technician', 'Driver', 'Gardener',
    'General Labour', 'Welding', 'Plumbing', 'Construction',
    'Cleaning', 'Mechanic', 'Cooking', 'Security Guard',
    'Delivery', 'Tailor', 'Barber'
]

# Common keyword-to-service mapping (instant, no API call needed)
KEYWORD_MAP = {
    'fix pipe': 'Plumber', 'water leak': 'Plumber', 'tap repair': 'Plumber',
    'bathroom': 'Plumber', 'drainage': 'Plumber', 'toilet': 'Plumber',
    'wiring': 'Electrician', 'light': 'Electrician', 'fan repair': 'Electrician',
    'switch': 'Electrician', 'power': 'Electrician', 'electrical': 'Electrician',
    'furniture': 'Carpenter', 'wood': 'Carpenter', 'door': 'Carpenter',
    'cabinet': 'Carpenter', 'shelf': 'Carpenter', 'table': 'Carpenter',
    'wall paint': 'Painter', 'painting': 'Painter', 'colour': 'Painter',
    'color': 'Painter', 'whitewash': 'Painter',
    'brick': 'Mason', 'tile': 'Mason', 'flooring': 'Mason',
    'cement': 'Mason', 'concrete': 'Mason', 'building': 'Mason',
    'clean house': 'Housekeeping', 'maid': 'Housekeeping', 'sweeping': 'Housekeeping',
    'dusting': 'Housekeeping', 'mopping': 'Housekeeping',
    'ac repair': 'AC Technician', 'air conditioner': 'AC Technician', 'cooling': 'AC Technician',
    'ac service': 'AC Technician', 'ac install': 'AC Technician',
    'cab': 'Driver', 'car': 'Driver', 'transport': 'Driver', 'ride': 'Driver',
    'plant': 'Gardener', 'garden': 'Gardener', 'lawn': 'Gardener', 'tree': 'Gardener',
    'labour': 'General Labour', 'helper': 'General Labour', 'worker': 'General Labour',
    'loading': 'General Labour', 'shifting': 'General Labour', 'moving': 'General Labour',
    'weld': 'Welding', 'iron': 'Welding', 'gate': 'Welding', 'grill': 'Welding',
    'stitch': 'Tailor', 'sewing': 'Tailor', 'clothes': 'Tailor', 'alteration': 'Tailor',
    'haircut': 'Barber', 'shave': 'Barber', 'salon': 'Barber',
    'cook': 'Cooking', 'food': 'Cooking', 'chef': 'Cooking',
    'guard': 'Security Guard', 'watchman': 'Security Guard', 'security': 'Security Guard',
}

def nlp_search(user_query):
    """
    Smart NLP search: resolves typos, keywords, and intent to a known service.
    Returns (resolved_service, was_corrected: bool)
    """
    if not user_query or not user_query.strip():
        return ('', False)
    
    query = user_query.strip()
    query_lower = query.lower()

    # 1. Exact match (case-insensitive)
    for svc in KNOWN_SERVICES:
        if query_lower == svc.lower():
            return (svc, False)

    # 2. Keyword / intent mapping (instant)
    for keyword, service in KEYWORD_MAP.items():
        if keyword in query_lower:
            return (service, True)

    # 3. Fuzzy match using difflib (typo correction, no API call)
    close = get_close_matches(query_lower, [s.lower() for s in KNOWN_SERVICES], n=1, cutoff=0.55)
    if close:
        matched = next(s for s in KNOWN_SERVICES if s.lower() == close[0])
        return (matched, True)

    # 4. Gemini AI fallback (for complex intent like "my sink is broken")
    if GEMINI_SEARCH_ENABLED:
        try:
            prompt = f"""You are a search query resolver for a labour hiring platform.
The user searched for: "{query}"

Our available service categories are: {', '.join(KNOWN_SERVICES)}

Your task:
1. If the query is a misspelling of a service, return the corrected service name.
2. If the query describes a problem or task, return the most relevant service category.
3. If no match is possible, return "NO_MATCH".

Return ONLY the service name (e.g. "Plumber") or "NO_MATCH". No explanation."""

            response = gemini_model.generate_content(prompt)
            result = response.text.strip().strip('"').strip("'")
            
            if result != "NO_MATCH" and result in KNOWN_SERVICES:
                return (result, True)
            # Also check fuzzy against the result in case Gemini returns slight variations
            close2 = get_close_matches(result.lower(), [s.lower() for s in KNOWN_SERVICES], n=1, cutoff=0.7)
            if close2:
                matched2 = next(s for s in KNOWN_SERVICES if s.lower() == close2[0])
                return (matched2, True)
        except Exception as e:
            print(f"Gemini search error: {e}")

    # 5. No match — return original query for standard DB search
    return (query, False)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hire_labour.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db.init_app(app)

# --- Automatic Database Fix (Self-Healing) ---
try:
    with app.app_context():
        import sqlite3
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            # Ensure instance folder exists
            if not os.path.exists(app.instance_path):
                os.makedirs(app.instance_path)
            db_path = os.path.join(app.instance_path, db_path)
        
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cols = [("id_card_image", "VARCHAR(255)"), ("selfie_image", "VARCHAR(255)"), 
                    ("face_encoding", "TEXT"), ("trust_score", "INTEGER DEFAULT 0"), 
                    ("status", "VARCHAR(20) DEFAULT 'Pending'")]
            for col_name, col_type in cols:
                try: cursor.execute(f"ALTER TABLE labours ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError: pass
            conn.commit()
            conn.close()
        db.create_all() # Ensure all tables exist
except Exception as e:
    print(f"Database Migration Warning: {e}")
# --------------------------------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# --- AI Verification Helpers ---
def extract_aadhaar_from_img(image_path):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        match = re.search(r'\d{4}\s\d{4}\s\d{4}', text)
        return match.group(0).replace(" ", "") if match else None
    except: return None

def verify_labourer_ai(labour_id, id_path, selfie_path):
    if not AI_ENABLED:
        print("AI Verification skipped (dependencies missing).")
        return
    
    labour = Labour.query.get(labour_id)
    if not labour: return

    trust_score = 0
    face_encoding_str = ""
    
    try:
        id_img = face_recognition.load_image_file(id_path)
        selfie_img = face_recognition.load_image_file(selfie_path)
        id_enc = face_recognition.face_encodings(id_img)
        selfie_enc = face_recognition.face_encodings(selfie_img)

        if id_enc and selfie_enc:
            match = face_recognition.compare_faces([id_enc[0]], selfie_enc[0], tolerance=0.6)
            if match[0]: trust_score += 50
            face_encoding_str = ",".join(map(str, selfie_enc[0].tolist()))
    except Exception as e: print(f"Face Match Error: {e}")

    extracted = extract_aadhaar_from_img(id_path)
    if extracted: trust_score += 10
    
    # Duplicate Check
    others = Labour.query.filter(Labour.labour_id != labour_id).all()
    is_duplicate = False
    if face_encoding_str:
        new_enc = np.array(list(map(float, face_encoding_str.split(','))))
        for other in others:
            if other.face_encoding:
                other_enc = np.array(list(map(float, other.face_encoding.split(','))))
                if face_recognition.compare_faces([other_enc], new_enc, tolerance=0.5)[0]:
                    is_duplicate = True; break

    if is_duplicate:
        labour.status = 'Fake'
        labour.trust_score = 0
    else:
        labour.trust_score = trust_score
        if trust_score > 40: labour.status = 'Verified'
        else: labour.status = 'Suspicious'
    
    labour.face_encoding = face_encoding_str
    db.session.commit()
# -------------------------------

# Translations Dictionary
TRANSLATIONS = {
    'en': {
        'welcome': 'Welcome to Hire Labour!',
        'description': 'Find skilled labour for your needs, or register as labour to offer your services.',
        'signup_public': 'Sign up as Public',
        'signup_labour': 'Sign up as Labour',
        'search_labour': 'Search for Labour',
        'recent_labour': 'Recently Registered Labourers',
        'login': 'Login',
        'register': 'Register',
        'logout': 'Logout',
        'admin_panel': 'Admin Panel',
        'dashboard': 'Dashboard',
        'manage_labours': 'Manage Labours',
        'manage_publics': 'Manage Publics'
    },
    'kn': { 'welcome': 'ಹೈರ್ ಲೇಬರ್ ಸ್ವಾಗತ!', 'description': 'ನಿಮ್ಮ ಅಗತ್ಯಗಳಿಗಾಗಿ ನುರಿತ ಕಾರ್ಮಿಕರನ್ನು ಹುಡುಕಿ.', 'signup_public': 'ಸಾರ್ವಜನಿಕವಾಗಿ ನೋಂದಾಯಿಸಿ', 'signup_labour': 'ಕಾರ್ಮಿಕರಾಗಿ ನೋಂದಾಯಿಸಿ', 'login': 'ಲಾಗಿನ್', 'logout': 'ಲಾಗೌಟ್' },
    'hi': { 'welcome': 'हायर लेबर में आपका स्वागत है!', 'description': 'अपनी जरूरतों के लिए कुशल श्रमिक खोजें।', 'signup_public': 'पब्लिक के रूप में जुड़ें', 'signup_labour': 'लेबर के रूप में जुड़ें', 'login': 'लॉगिन', 'logout': 'लॉगआउट' },
    'ta': { 'welcome': 'ஹையர் லேபருக்கு வரவேற்கிறோம்!', 'description': 'உங்கள் தேவைகளுக்கு திறமையான தொழிலாளர்களைக் கண்டறியவும்.', 'signup_public': 'பொதுமக்களாக பதிவு செய்யவும்', 'signup_labour': 'தொழிலாளியாக பதிவு செய்யவும்', 'login': 'உள்நுழை', 'logout': 'வெளியேறு' },
    'te': { 'welcome': 'హైర్ లేబర్‌కు స్వాగతం!', 'description': 'మీ అవసరాల కోసం నైపుణ్యం కలిగిన కార్మికులను కనుగొనండి.', 'signup_public': 'పబ్లిక్ గా నమోదు చేసుకోండి', 'signup_labour': 'కార్మికునిగా నమోదు చేసుకోండి', 'login': 'లాగిన్', 'logout': 'లాగౌట్' },
    'ml': { 'welcome': 'ഹയർ ലേബറിലേക്ക് സ്വാഗതം!', 'description': 'നിങ്ങളുടെ ആവശ്യങ്ങൾക്കായി വിദഗ്ധ തൊഴിലാളികളെ കണ്ടെത്തുക.', 'signup_public': 'പൊതുജനമായി രജിസ്റ്റർ ചെയ്യുക', 'signup_labour': 'തൊഴിലാളിയായി രജിസ്റ്റർ ചെയ്യുക', 'login': 'ലോഗിൻ', 'logout': 'ലോഗ്ഔട്ട്' },
    'mr': { 'welcome': 'हायर लेबरमध्ये स्वागत आहे!', 'description': 'तुमच्या गरजांसाठी कुशल कामगार शोधा.', 'signup_public': 'सार्वजनिक म्हणून नोंदणी करा', 'signup_labour': 'कामगार म्हणून नोंदणी करा', 'login': 'लॉगिन', 'logout': 'लॉगआउट' }
}

@login_manager.user_loader
def load_user(user_id):
    try:
        if user_id.startswith('admin_'):
            return Admin.query.get(int(user_id.split('_')[1]))
        elif user_id.startswith('labour_'):
            return Labour.query.get(int(user_id.split('_')[1]))
        elif user_id.startswith('public_'):
            return Public.query.get(int(user_id.split('_')[1]))
    except:
        return None
    return None

@app.context_processor
def inject_lang():
    lang = session.get('lang', 'en')
    en = TRANSLATIONS['en']
    current = TRANSLATIONS.get(lang, en)
    # Merge: current language with English fallback for missing keys
    merged = {**en, **current}
    return dict(lang=lang, t=merged)

@app.route('/set_lang/<lang>')
def set_lang(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    print(f"DEBUG: 404 Error - Path hit: {request.path}")
    return "Custom 404: Route Not Found in Flask App", 404

@app.route('/')
def index():
    print("DEBUG: Index route hit")
    recent_labours = Labour.query.order_by(Labour.registration_date.desc()).limit(5).all()
    top_rated = db.session.query(
        Labour, func.avg(Feedback.rating).label('average_rating')
    ).join(Feedback).group_by(Labour.labour_id).order_by(func.avg(Feedback.rating).desc()).limit(3).all()
    
    if not top_rated:
        top_rated = [(p, 0.0) for p in Labour.query.limit(3).all()]
        
    return render_template('index.html', recent_labours=recent_labours, top_rated=top_rated)

@app.route('/login', methods=['GET', 'POST'])
def login():
    print(f"DEBUG: Login route hit with method {request.method}")
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        user = None
        if role == 'admin':
            user = Admin.query.filter_by(username=username, password=password).first()
        elif role == 'labour':
            user = Labour.query.filter_by(username=username, password=password).first()
        elif role == 'public':
            user = Public.query.filter_by(username=username, password=password).first()

        if user:
            login_user(user)
            session['user_role'] = role
            flash('Logged in successfully!', 'success')
            if role == 'labour':
                return redirect(url_for('labour_dashboard'))
            elif role == 'public':
                return redirect(url_for('public_dashboard'))
            elif role == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/register_public', methods=['GET', 'POST'])
def register_public():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        # Check if username or email already exists
        if Public.query.filter((Public.username == username) | (Public.email == email)).first():
            flash('Username or Email already exists!', 'danger')
            return redirect(url_for('register_public'))

        new_user = Public(
            username=username,
            password=request.form.get('password'),
            full_name=request.form.get('full_name'),
            email=email,
            phone=request.form.get('phone')
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Public account created!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
            
    return render_template('register_public.html')

@app.route('/register_labour', methods=['GET', 'POST'])
def register_labour():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        # Check if username or email already exists
        if Labour.query.filter((Labour.username == username) | (Labour.email == email)).first():
            flash('Username or Email already exists!', 'danger')
            return redirect(url_for('register_labour'))

        # Handle file uploads
        id_card = request.files.get('id_card')
        selfie = request.files.get('selfie')
        selfie_base64 = request.form.get('selfie_base64')
        
        id_filename = ""
        selfie_filename = ""
        
        if id_card:
            id_filename = secure_filename(f"id_{username}_{id_card.filename}")
            id_card.save(os.path.join(app.config['UPLOAD_FOLDER'], id_filename))
        
        if selfie_base64 and "," in selfie_base64:
            # Handle Live Selfie (Base64)
            import base64
            header, encoded = selfie_base64.split(",", 1)
            data = base64.b64decode(encoded)
            selfie_filename = secure_filename(f"selfie_{username}_live.jpg")
            with open(os.path.join(app.config['UPLOAD_FOLDER'], selfie_filename), "wb") as f:
                f.write(data)
        elif selfie:
            # Handle Uploaded Selfie
            selfie_filename = secure_filename(f"selfie_{username}_{selfie.filename}")
            selfie.save(os.path.join(app.config['UPLOAD_FOLDER'], selfie_filename))

        new_user = Labour(
            username=username,
            password=request.form.get('password'),
            full_name=request.form.get('full_name'),
            email=email,
            phone=request.form.get('phone'),
            service_offered=request.form.get('service_offered'),
            address=request.form.get('address'),
            id_card_image=id_filename,
            selfie_image=selfie_filename
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Trigger AI Verification
            id_path = os.path.join(app.config['UPLOAD_FOLDER'], id_filename)
            selfie_path = os.path.join(app.config['UPLOAD_FOLDER'], selfie_filename)
            verify_labourer_ai(new_user.labour_id, id_path, selfie_path)
            
            flash('Labour account created and verification in progress!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('register_labour.html')

@app.route('/public_dashboard')
@login_required
def public_dashboard():
    raw_service = request.args.get('service', '')
    
    # ── NLP AI Search: resolve typos, keywords, intent ──
    ai_corrected = False
    original_query = raw_service
    if raw_service:
        resolved, was_corrected = nlp_search(raw_service)
        service = resolved
        ai_corrected = was_corrected
    else:
        service = ''
    
    # Base query for recommendations with feedback
    rec_query = db.session.query(
        Labour, func.avg(Feedback.rating).label('avg_rating')
    ).join(Feedback)

    if service:
        results = Labour.query.filter(Labour.service_offered.ilike(f'%{service}%')).all()
        recommendations = rec_query.filter(Labour.service_offered.ilike(f'%{service}%'))\
            .group_by(Labour.labour_id).order_by(func.avg(Feedback.rating).desc()).limit(3).all()
            
        # Fallback: if no feedback-based recommendations, show top professionals for that service
        if not recommendations:
            fallback_labours = Labour.query.filter(Labour.service_offered.ilike(f'%{service}%')).limit(3).all()
            recommendations = [(l, 0.0) for l in fallback_labours]
    else:
        results = Labour.query.all()
        recommendations = rec_query.group_by(Labour.labour_id).order_by(func.avg(Feedback.rating).desc()).limit(3).all()
        
        # Fallback: if no feedback-based recommendations, show any 3 professionals
        if not recommendations:
            fallback_labours = Labour.query.limit(3).all()
            recommendations = [(l, 0.0) for l in fallback_labours]
            
    return render_template('public_dashboard.html', 
                           results=results, 
                           service=service, 
                           recommendations=recommendations,
                           ai_corrected=ai_corrected,
                           original_query=original_query)

@app.route('/labour_dashboard')
@login_required
def labour_dashboard():
    if session.get('user_role') != 'labour':
        return redirect(url_for('index'))
    feedbacks = Feedback.query.filter_by(labour_id=current_user.labour_id).all()
    showcase = WorkShowcase.query.filter_by(labour_id=current_user.labour_id).all()
    return render_template('labour_dashboard.html', user=current_user, feedbacks=feedbacks, showcase=showcase)

@app.route('/view_labour/<int:id>')
@login_required
def view_labour(id):
    labour = Labour.query.get_or_404(id)
    feedbacks = Feedback.query.filter_by(labour_id=id).all()
    showcase = WorkShowcase.query.filter_by(labour_id=id).all()
    return render_template('view_labour.html', labour=labour, feedbacks=feedbacks, showcase=showcase)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if session.get('user_role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin/dashboard.html', labour_count=Labour.query.count(), public_count=Public.query.count(), feedback_count=Feedback.query.count())

@app.route('/admin/update_labour_status/<int:id>', methods=['POST'])
@login_required
def update_labour_status(id):
    if session.get('user_role') != 'admin':
        return redirect(url_for('index'))
    labour = Labour.query.get_or_404(id)
    new_status = request.form.get('status')
    if new_status:
        labour.status = new_status
        if new_status == 'Verified': labour.trust_score = 100
        elif new_status == 'Fake': labour.trust_score = 0
        db.session.commit()
        flash(f'Status for {labour.full_name} updated to {new_status}', 'success')
    return redirect(url_for('manage_labours'))

@app.route('/admin/manage_labours')
@login_required
def manage_labours():
    if session.get('user_role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin/manage_labours.html', labours=Labour.query.all())

@app.route('/admin/manage_publics')
@login_required
def manage_publics():
    if session.get('user_role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin/manage_publics.html', publics=Public.query.all())

@app.route('/admin/delete_user/<string:type>/<int:id>')
@login_required
def delete_user(type, id):
    if session.get('user_role') != 'admin':
        return redirect(url_for('index'))
    if type == 'labour':
        user = Labour.query.get(id)
        if user:
            Feedback.query.filter_by(labour_id=id).delete()
            db.session.delete(user)
            db.session.commit()
            flash('Labourer deleted successfully', 'success')
        return redirect(url_for('manage_labours'))
    elif type == 'public':
        user = Public.query.get(id)
        if user:
            Feedback.query.filter_by(public_id=id).delete()
            db.session.delete(user)
            db.session.commit()
            flash('Public user deleted successfully', 'success')
        return redirect(url_for('manage_publics'))
    return redirect(url_for('admin_dashboard'))

@app.route('/submit_feedback', methods=['POST'])
@login_required
def submit_feedback():
    if session.get('user_role') != 'public':
        flash('Only public users can give feedback', 'danger')
        return redirect(url_for('index'))
    new_fb = Feedback(public_id=current_user.public_id, labour_id=request.form.get('labour_id'), rating=request.form.get('rating'), comment=request.form.get('comment'))
    db.session.add(new_fb)
    db.session.commit()
    flash('Feedback submitted!', 'success')
    return redirect(url_for('view_labour', id=request.form.get('labour_id')))

@app.route('/upload_work', methods=['POST'])
@login_required
def upload_work():
    if session.get('user_role') != 'labour':
        return redirect(url_for('index'))
    
    if 'work_image' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('labour_dashboard'))
    
    file = request.files['work_image']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('labour_dashboard'))
    
    if file:
        filename = secure_filename(file.filename)
        # Add timestamp to filename to prevent collisions
        import time
        filename = f"{int(time.time())}_{filename}"
        
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_showcase = WorkShowcase(
            labour_id=current_user.labour_id,
            image_path=filename,
            description=request.form.get('description')
        )
        db.session.add(new_showcase)
        db.session.commit()
        flash('Work image uploaded successfully!', 'success')
        
    return redirect(url_for('labour_dashboard'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload_profile', methods=['POST'])
@login_required
def upload_profile():
    if 'profile_image' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.referrer)
    
    file = request.files['profile_image']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.referrer)
    
    if file:
        filename = secure_filename(file.filename)
        import time
        filename = f"profile_{int(time.time())}_{filename}"
        
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        role = session.get('user_role')
        if role == 'labour':
            current_user.profile_image = filename
        elif role == 'public':
            current_user.profile_image = filename
            
        db.session.commit()
        flash('Profile picture updated!', 'success')
        
    return redirect(request.referrer)

@app.route('/chat/<int:labour_id>')
@login_required
def chat(labour_id):
    role = session.get('user_role')
    if role == 'public':
        public_id = current_user.public_id
        labour = Labour.query.get_or_404(labour_id)
        messages = Message.query.filter_by(public_id=public_id, labour_id=labour_id).order_by(Message.timestamp).all()
        return render_template('chat.html', messages=messages, target=labour, target_role='labour')
    elif role == 'labour':
        # If labour is viewing, they need a public_id from args
        public_id = request.args.get('public_id', type=int)
        if not public_id:
            return redirect(url_for('messages'))
        public = Public.query.get_or_404(public_id)
        messages = Message.query.filter_by(public_id=public_id, labour_id=current_user.labour_id).order_by(Message.timestamp).all()
        # Mark as read
        for m in messages:
            if m.receiver_type == 'labour' and m.receiver_id == current_user.labour_id:
                m.is_read = True
        db.session.commit()
        return render_template('chat.html', messages=messages, target=public, target_role='public')
    return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    role = session.get('user_role')
    content = request.form.get('content')
    if not content:
        return redirect(request.referrer)

    if role == 'public':
        labour_id = request.form.get('labour_id', type=int)
        new_msg = Message(
            sender_type='public',
            sender_id=current_user.public_id,
            receiver_type='labour',
            receiver_id=labour_id,
            public_id=current_user.public_id,
            labour_id=labour_id,
            content=content
        )
    elif role == 'labour':
        public_id = request.form.get('public_id', type=int)
        new_msg = Message(
            sender_type='labour',
            sender_id=current_user.labour_id,
            receiver_type='public',
            receiver_id=public_id,
            public_id=public_id,
            labour_id=current_user.labour_id,
            content=content
        )
    else:
        return redirect(url_for('index'))

    db.session.add(new_msg)
    db.session.commit()
    return redirect(request.referrer)

@app.route('/messages')
@login_required
def messages():
    role = session.get('user_role')
    if role == 'public':
        # Get all labours this public has messaged
        chats = db.session.query(Message.labour_id).filter_by(public_id=current_user.public_id).distinct().all()
        chat_partners = [Labour.query.get(c[0]) for c in chats]
        return render_template('messages.html', chat_partners=chat_partners, role='public')
    elif role == 'labour':
        # Get all publics this labour has messaged
        chats = db.session.query(Message.public_id).filter_by(labour_id=current_user.labour_id).distinct().all()
        chat_partners = [Public.query.get(c[0]) for c in chats]
        return render_template('messages.html', chat_partners=chat_partners, role='labour')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            db.session.add_all([Admin(username='admin', password='admin123'), Public(username='raj', password='password', full_name='Raj Kumar', email='raj@example.com', phone='1234567890'), Labour(username='pavan', password='password', full_name='Pavan Kumar', email='pavan@example.com', phone='9353600120', service_offered='Plumbing', address='BIET Road')])
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)
