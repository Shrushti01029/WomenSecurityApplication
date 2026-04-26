from flask import Flask, render_template, request, redirect, jsonify, send_file , session, url_for , flash
from flask_bcrypt import Bcrypt
from flask_session import Session
import os
import uuid
from flask import send_from_directory, flash
import json
import pip
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import mysql.connector
from twilio.rest import Client
from deep_translator import GoogleTranslator
import random
import time
import smtplib
from email.message import EmailMessage
import smtplib
from email.mime.text import MIMEText


openai.api_key = "YOUR_OPENAI_API_KEY"
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

bcrypt = Bcrypt(app)
Session(app)

# ================= DATABASE =================
db = mysql.connector.connect(
    host="Railway",
    user="root",
    password="root",
    database="women_security_db"
)

cursor = db.cursor(dictionary=True)


ACCOUNT_SID = "ACb12a34567890abcdef1234567890ab"
AUTH_TOKEN = "9c5e7c7e8b5c9e9e3c12345678abcdef"
TWILIO_PHONE = "+14155238886"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ================= HOME =================
@app.route('/')
def home():
    return render_template("index.html")

# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # ✅ Safe form access
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        mobile = request.form.get("mobile")
        age = request.form.get("age")
        state = request.form.get("state")
        district = request.form.get("district")
        education = request.form.get("education")
        employment = request.form.get("employment")
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        # ✅ Password match check (your original feature)
        if password != confirm:
            flash("Passwords do not match!", "error")
            return redirect("/register")

        cursor = db.cursor(dictionary=True)

        # ✅ Email already exists check (your original feature)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered!", "error")
            return redirect("/register")

        # ✅ NEW: Basic password strength check
        if len(password) < 6:
            flash("Password must be at least 6 characters!", "error")
            return redirect("/register")

        # ✅ Hash password (same as yours)
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # ✅ Insert user (same structure as yours)
        cursor.execute("""
            INSERT INTO users
            (full_name,email,mobile,age,state,district,education,employment,password)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (full_name,email,mobile,age,state,district,education,employment,hashed_password))

        db.commit()

        # ✅ NEW: Save activity log
        cursor.execute("""
            INSERT INTO account_activity (user_id, activity)
            VALUES (%s, %s)
        """, (cursor.lastrowid, "New user registered"))

        db.commit()

        flash("Registration Successful! Please Login.", "success")
        return redirect("/login")

    return render_template("register.html")
# ================= LOGIN =================
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user["password"], password):

            # ✅ KEEPING YOUR EXISTING FEATURES
            session["user"] = user["full_name"]
            session["user_id"] = user["id"]

            cursor = db.cursor()

            # ✅ NEW: Update last login time
            cursor.execute("""
                UPDATE users 
                SET last_login = NOW() 
                WHERE id = %s
            """, (user["id"],))

            # ✅ NEW: Save login history
            cursor.execute("""
                INSERT INTO login_history (user_id, ip_address)
                VALUES (%s, %s)
            """, (user["id"], request.remote_addr))

            # ✅ NEW: Save activity log
            cursor.execute("""
                INSERT INTO account_activity (user_id, activity)
                VALUES (%s, %s)
            """, (user["id"], "User logged in"))

            db.commit()

            return redirect("/dashboard")

        else:
            flash("Invalid Email or Password!", "error")
            return redirect("/login")

    return render_template("login.html")
# ================= USER DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", name=session["user"])

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ------------------- SUBMIT APPLICATION -------------------
@app.route("/submit_application", methods=["POST"])
def submit_application():
    scheme_id = request.form["scheme_id"]
    full_name = request.form["full_name"]
    email = request.form.get("email", "")
    phone = request.form["phone"]
    dob = request.form.get("dob")
    if not dob:
      dob = None
    gender = request.form.get("gender", "")
    address = request.form["address"]
    notes = request.form.get("notes", "")

    # Files
    photo = request.files.get("photo")
    aadhar = request.files.get("aadhar")
    income = request.files.get("income_certificate")

    photo_name = photo.filename if photo else ""
    aadhar_name = aadhar.filename if aadhar else ""
    income_name = income.filename if income else ""

    if photo_name:
        photo.save(os.path.join("static/uploads", photo_name))
    if aadhar_name:
        aadhar.save(os.path.join("static/uploads", aadhar_name))
    if income_name:
        income.save(os.path.join("static/uploads", income_name))

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO scheme_applications
        (user_id, scheme_id, full_name, email, phone, dob, gender, address,
         photo, aadhar, income_certificate, notes, application_status, applied_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending', NOW())
    """, (
        session["user_id"], scheme_id, full_name, email, phone, dob, gender, address,
        photo_name, aadhar_name, income_name, notes
    ))
    db.commit()
    return "✅ Application Submitted Successfully!"

# ------------------- APPLY FORM -------------------
@app.route("/apply_form/<int:scheme_id>")
def apply_form(scheme_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM schemes WHERE id=%s", (scheme_id,))
    scheme = cursor.fetchone()
    if not scheme:
        return "Scheme not found", 404
    return render_template("apply_form.html", scheme=scheme)


# ================= ADMIN LOGIN =================
@app.route('/admin_login', methods=['POST'])
def admin_login():
    admin_id = request.form['admin_id']
    password = request.form['password']

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admin WHERE admin_id=%s", (admin_id,))
    admin = cursor.fetchone()

    if admin and admin['password'] == password:
        session['admin'] = admin['admin_id']
        return redirect('/admin_dashboard')
    else:
        flash("Invalid Admin Credentials", "error")
        return redirect("/")

# ================= ADMIN DASHBOARD =================
@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    # ===== OLD FEATURES =====
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM schemes")
    total_schemes = cursor.fetchone()["total"]

    # Optional tables (safe)
    try:
        cursor.execute("SELECT COUNT(*) as total FROM feedback")
        feedback = cursor.fetchone()["total"]
    except:
        feedback = 0

    
    try:
       cursor.execute("SELECT COUNT(*) as total FROM sos_alerts")
       sos = cursor.fetchone()["total"]
    except:
        sos = 0

        
    # ===== NEW APPLICATION FEATURES =====
    try:
        cursor.execute("SELECT COUNT(*) as total FROM scheme_applications")
        total_applications = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM scheme_applications WHERE application_status='Pending'")
        pending = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM scheme_applications WHERE application_status='Approved'")
        approved = cursor.fetchone()["total"]
    except:
        total_applications = 0
        pending = 0
        approved = 0

    return render_template(
        "admin_dashboard.html",
        users=total_users,
        schemes=total_schemes,
        feedback=feedback,
        sos=sos,
        total_applications=total_applications,
        pending=pending,
        approved=approved
    )








# ================= SCHEME LIST =================
@app.route("/schemes")
def schemes():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM schemes")
    all_schemes = cursor.fetchall()
    return render_template("schemes.html", schemes=all_schemes)








# ------------------- ADMIN VIEW APPLICATIONS -------------------
@app.route("/admin/applications")
def admin_applications():
    if "admin" not in session:
        return redirect("/")
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
    SELECT 
        sa.id,
        u.full_name,
        u.email,
        u.phone,
        u.dob,
        s.scheme_name,
        sa.application_status,
        sa.applied_date
    FROM scheme_applications sa
    JOIN users u ON sa.user_id = u.id
    JOIN schemes s ON sa.scheme_id = s.id
    ORDER BY sa.applied_date DESC
""")
    applications = cursor.fetchall()
    return render_template("admin_applications.html", applications=applications)






@app.route("/scheme_search")
def scheme_search():
    return render_template("scheme_search.html")


@app.route("/scheme_results", methods=["POST"])
def scheme_results():
    education = request.form["education"].strip()
    income = int(request.form["income"])
    caste = request.form["caste"].strip()
    marital_status = request.form["marital_status"].strip()

    cursor = db.cursor(dictionary=True)

    query = """
        SELECT * FROM schemes
        WHERE 
        (LOWER(required_education) = LOWER(%s) OR LOWER(required_education)='any')
        AND max_income >= %s
        AND (LOWER(allowed_caste) = LOWER(%s) OR LOWER(allowed_caste)='all')
        AND (LOWER(required_marital_status) = LOWER(%s) OR LOWER(required_marital_status)='any')
    """

    cursor.execute(query, (education, income, caste, marital_status))
    schemes = cursor.fetchall()

    return render_template("scheme_results.html", schemes=schemes)

        







@app.route("/admin/delete/<int:application_id>")
def delete_application(application_id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM scheme_applications WHERE id=%s", (application_id,))
    db.commit()
    return redirect(url_for("admin_applications"))


@app.route("/admin/update_status/<int:application_id>/<string:new_status>")
def update_status(application_id, new_status):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE scheme_applications SET status=%s WHERE id=%s",
        (new_status, application_id)
    )
    db.commit()
    return redirect(url_for("admin_applications"))

@app.route("/admin_logout", endpoint="admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))



@app.route("/admin_reports")
def admin_reports():

    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT ir.*, u.full_name 
        FROM incident_reports ir
        JOIN users u ON ir.user_id = u.id
        ORDER BY created_at DESC
    """)

    reports = cursor.fetchall()

    return render_template("admin_reports.html", reports=reports)



@app.route("/safety_helpline")
def safety_helpline():

    if "user" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    # Get unique helpline categories
    cursor.execute("SELECT DISTINCT category FROM safety_helplines")
    categories = cursor.fetchall()

    # Get all helplines
    cursor.execute("SELECT * FROM safety_helplines ORDER BY category")
    helplines = cursor.fetchall()

    # Get safety tips grouped by condition
    cursor.execute("SELECT DISTINCT condition_name FROM safety_tips")
    conditions = cursor.fetchall()

    cursor.execute("SELECT * FROM safety_tips ORDER BY condition_name")
    tips = cursor.fetchall()

    return render_template("safety_helpline.html",
                           categories=categories,
                           helplines=helplines,
                           conditions=conditions,
                           tips=tips)

#Document Vault Routes

@app.route("/document_vault")
def document_vault():

    if "user_id" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_documents WHERE user_id=%s ORDER BY uploaded_at DESC",
                   (session["user_id"],))
    documents = cursor.fetchall()

    return render_template("document_vault.html", documents=documents)

@app.route("/upload_document", methods=["POST"])
def upload_document():

    if "user" not in session:
        return redirect("/")

    if 'file' not in request.files:
        flash("No file selected")
        return redirect("/document_vault")

    file = request.files['file']
    category = request.form['category']
    emergency = request.form.get('emergency')

    if file.filename == '':
        flash("No selected file")
        return redirect("/document_vault")

    if file and allowed_file(file.filename):

        original_name = secure_filename(file.filename)
        unique_name = str(uuid.uuid4()) + "_" + original_name

       

        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO user_documents 
            (user_id, file_name, stored_name, category, emergency_access)
            VALUES (%s, %s, %s, %s, %s)
        """, (session["user_id"], original_name,
              unique_name, category, bool(emergency)))

        db.commit()

        flash("Document uploaded successfully!")

    else:
        flash("Invalid file type. Only PNG, JPG, JPEG, PDF allowed.")

    return redirect("/document_vault")

@app.route("/delete_document/<int:id>")
def delete_document(id):

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_documents WHERE id=%s AND user_id=%s",
                   (id, session["user_id"]))
    doc = cursor.fetchone()

    if doc:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], doc['stored_name']))
        cursor.execute("DELETE FROM user_documents WHERE id=%s", (id,))
        db.commit()

    return redirect("/document_vault")


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename,
                               as_attachment=True)

@app.route("/admin_emergency_docs")
def admin_emergency_docs():

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_documents WHERE emergency_access=1")
    docs = cursor.fetchall()

    return render_template("admin_emergency_docs.html", docs=docs)


#Profile update routes

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE id=%s",
                   (session["user_id"],))
    user = cursor.fetchone()

    # Stats
    cursor.execute("SELECT COUNT(*) total FROM user_documents WHERE user_id=%s",
                   (session["user_id"],))
    total_docs = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) emergency FROM user_documents WHERE user_id=%s AND emergency_access=1",
                   (session["user_id"],))
    emergency_docs = cursor.fetchone()["emergency"]

    cursor.execute("SELECT COUNT(*) shared FROM user_documents WHERE user_id=%s AND share_token IS NOT NULL",
                   (session["user_id"],))
    shared_docs = cursor.fetchone()["shared"]

    # Profile completion %
    fields = [user["phone"], user["address"], user["dob"], user["profile_photo"]]
    completed = sum(1 for f in fields if f)
    completion = int((completed / len(fields)) * 100)

    return render_template("profile.html",
                           user=user,
                           total_docs=total_docs,
                           emergency_docs=emergency_docs,
                           shared_docs=shared_docs,
                           completion=completion)


@app.route("/update_profile", methods=["POST"])
def update_profile():

    if "user_id" not in session:
        return redirect("/")

    cursor = db.cursor()

    # ✅ Get data from form (MATCH HTML names)
    full_name = request.form.get("full_name")
    email = request.form.get("email")
    mobile = request.form.get("mobile")
    state = request.form.get("state")
    district = request.form.get("district")
    education = request.form.get("education")
    employment = request.form.get("employment")

    # ✅ Update user data
    cursor.execute("""
        UPDATE users SET 
        full_name=%s,
        email=%s,
        mobile=%s,
        state=%s,
        district=%s,
        education=%s,
        employment=%s
        WHERE id=%s
    """, (full_name, email, mobile, state, district, education, employment, session["user_id"]))

    # ✅ Handle profile photo upload
    if 'profile_photo' in request.files:
        photo = request.files['profile_photo']
        if photo.filename != "":
            filename = str(uuid.uuid4()) + "_" + secure_filename(photo.filename)
            photo.save(os.path.join("static/uploads", filename))

            cursor.execute("""
                UPDATE users SET profile_photo=%s WHERE id=%s
            """, (filename, session["user_id"]))

    db.commit()
    flash("Profile updated successfully", "success")

    return redirect("/profile")

    






    



@app.route("/change_password", methods=["POST"])
def change_password():

    old = request.form["old_password"]
    new = request.form["new_password"]

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT password FROM users WHERE id=%s",
                   (session["user_id"],))
    user = cursor.fetchone()

    if check_password_hash(user["password"], old):

        hashed = generate_password_hash(new)

        cursor = db.cursor()
        cursor.execute("UPDATE users SET password=%s WHERE id=%s",
                       (hashed,session["user_id"]))

        cursor.execute("INSERT INTO account_activity (user_id, activity) VALUES (%s,%s)",
                       (session["user_id"], "Changed password"))

        db.commit()

    return redirect("/profile")


@app.route("/toggle_emergency")
def toggle_emergency():

    cursor = db.cursor()
    cursor.execute("""
        UPDATE users
        SET emergency_mode = NOT emergency_mode
        WHERE id=%s
    """, (session["user_id"],))

    db.commit()
    return redirect("/profile")


@app.route("/revoke_share/<int:id>")
def revoke_share(id):

    cursor = db.cursor()
    cursor.execute("""
        UPDATE user_documents
        SET share_token=NULL
        WHERE id=%s AND user_id=%s
    """, (id,session["user_id"]))

    db.commit()
    return redirect("/profile")


@app.route("/download_data")
def download_data():

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s",
                   (session["user_id"],))
    user = cursor.fetchone()

    file_path = "user_data.json"
    with open(file_path,"w") as f:
        json.dump(user,f,indent=4,default=str)

    return send_file(file_path, as_attachment=True)


@app.route("/delete_account")
def delete_account():

    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s",
                   (session["user_id"],))
    db.commit()

    session.clear()
    return redirect("/")



#chatbot

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

 

@app.route("/chatbot_response", methods=["POST"])
def chatbot_response():

    data = request.json
    msg = data["message"].lower()

    # ======================
    # Greetings
    # ======================
    if any(word in msg for word in ["hi","hello","hey"]):
        reply = random.choice([
            "Hello! I am SafeShe AI. How can I help you today?",
            "Hi there! Your safety assistant is here.",
            "Hello! Ask me anything about women safety."
        ])

    # ======================
    # Emergency Responses
    # ======================
    elif "help" in msg or "danger" in msg:
        reply = "If you are in danger, call Police Emergency Number: 112."

    elif "sos" in msg:
        reply = "🚨 SOS Alert! Please contact emergency number 112."

    elif "helpline" in msg or "emergency" in msg:
        reply = (
            "Important helplines:\n"
            "- Police Emergency: 112\n"
            "- Women’s Helpline: 1091\n"
            "- Child Helpline: 1098\n"
            "- Cyber Crime: 1930\n"
            "- Ambulance: 108"
        )

    # ======================
    # Women Safety Advice
    # ======================
    elif "night" in msg:
        reply = "Stay in well-lit areas and share your live location with someone you trust."

    elif "cyber" in msg or "online harassment" in msg:
        reply = "Do not share personal information online and report the offender."

    elif "self defense" in msg:
        reply = "Try to stay calm and aim for vulnerable points like eyes or knees."

    elif "stalking" in msg:
        reply = "Collect evidence and report stalking to police or women helpline."

    elif "legal" in msg:
        reply = "You can contact Women's Helpline 1091 for legal support."

    elif "location" in msg:
        reply = "Sharing your live location with trusted contacts increases safety."

    elif "tools" in msg or "unsafe" in msg:
        reply = "Carry pepper spray, a personal alarm, or use women safety apps for quick alerts."

    elif "police" in msg or "station" in msg:
        reply = (
            "Nearest police stations in Swargate, Pune:\n"
            "- Swargate Police Station\n"
            "- Market Yard Police Station\n"
            "- Laxmi Nagar Police Station"
        )

    # ======================
    # Additional Women Safety Questions
    # ======================
    elif "travel alone" in msg:
        reply = "When traveling alone, share your live location and avoid isolated areas."

    elif "public transport safety" in msg:
        reply = "Sit near the driver or crowded areas and avoid empty compartments."

    elif "pepper spray" in msg:
        reply = "Pepper spray is a useful self-defense tool. Keep it easily accessible."

    elif "followed" in msg:
        reply = "If someone follows you, go to a crowded place or enter a nearby shop."

    elif "taxi safety" in msg or "cab safety" in msg:
        reply = "Verify the vehicle number and share trip details with trusted contacts."

    elif "unsafe area" in msg:
        reply = "Avoid poorly lit areas and always stay aware of surroundings."

    elif "emergency contact" in msg:
        reply = "Add trusted contacts in the emergency contact list for quick SOS alerts."

    elif "workplace harassment" in msg:
        reply = "Report workplace harassment to HR or the Internal Complaints Committee."

    elif "domestic violence" in msg:
        reply = "Seek help from the women helpline 1091 or contact local support services."

    elif "kidnapping" in msg:
        reply = "Immediately call 112 and try to share your location with trusted contacts."

    elif "crowded place safety" in msg:
        reply = "Stay alert in crowded places and keep personal belongings secure."

    elif "late night safety" in msg:
        reply = "Avoid walking alone late at night and prefer trusted transport."

    elif "social media safety" in msg:
        reply = "Avoid sharing personal details and location publicly online."

    elif "self defense classes" in msg:
        reply = "Self-defense training can improve confidence and personal safety."

    elif "street harassment" in msg:
        reply = "Seek help from nearby people or authorities if harassed in public."

    elif "safety tips" in msg:
        reply = "Stay alert, trust your instincts, and keep emergency contacts ready."

    elif "unsafe situation" in msg:
        reply = "Move to a safe place and use the SOS feature if necessary."

    elif "personal safety" in msg:
        reply = "Always stay aware of your surroundings and keep emergency tools ready."

    # ======================
    # Government Schemes
    # ======================
    elif "women schemes" in msg:
        reply = "There are many government schemes supporting women like Beti Bachao Beti Padhao."

    elif "education scheme" in msg:
        reply = "Government education schemes provide scholarships for girls."

    elif "business scheme" in msg:
        reply = "Women entrepreneurs can apply for Mudra Loans and Stand Up India."

    elif "self employment" in msg:
        reply = "Self-employment schemes help women start small businesses."

    elif "loan for women" in msg:
        reply = "Many banks offer special loan schemes for women entrepreneurs."

    elif "scholarship for girls" in msg:
        reply = "Scholarships are available for girls pursuing higher education."

    elif "widow support scheme" in msg:
        reply = "Widow pension schemes provide financial support."

    elif "pregnancy scheme" in msg:
        reply = "Pradhan Mantri Matru Vandana Yojana supports pregnant women."

    elif "rural women scheme" in msg:
        reply = "Self-help group programs support rural women's employment."

    elif "skill development" in msg:
        reply = "Skill development schemes help women gain training for jobs."

    elif "startup scheme" in msg:
        reply = "Startup support schemes help women launch businesses."

    elif "financial support" in msg:
        reply = "Many schemes provide financial assistance for women."

    elif "employment scheme" in msg:
        reply = "Employment programs help women gain job opportunities."

    elif "health scheme" in msg:
        reply = "Health schemes support maternal care and medical aid."

    elif "housing scheme" in msg:
        reply = "Some housing schemes prioritize women ownership."

    elif "insurance scheme" in msg:
        reply = "Insurance schemes provide financial security for women."

    elif "education loan" in msg:
        reply = "Education loans with lower interest rates are available."

    elif "single mother" in msg:
        reply = "Special welfare programs support single mothers."

    elif "government benefits" in msg:
        reply = "Benefits include scholarships, loans, training, and healthcare."

    elif "latest schemes" in msg:
        reply = "Check the scheme recommendation section on the dashboard."

    # ======================
    # Closing
    # ======================
    elif "thank" in msg:
        reply = "You're welcome! Stay safe."

    elif "bye" in msg:
        reply = "Goodbye! I'm here whenever you need help."

    else:
        reply = "Sorry, I didn't understand. Ask about safety tips, SOS, government schemes, or helplines."

    return jsonify({"response": reply})






#Emergency contact support

@app.route("/emergency", methods=["GET"])
def emergency():
    if "user_id" not in session:
        session["user_id"] = 3  # example, replace with login
    cursor.execute(
        "SELECT * FROM emergency_contacts WHERE user_id=%s",
        (session["user_id"],)
    )
    contacts = cursor.fetchall()
    return render_template("emergency.html", contacts=contacts)


@app.route("/add_contact", methods=["POST"])
def add_contact():
    session["user_id"] = 3   # temporary (replace with login later)

    # ✅ GET DATA FROM FORM
    name = request.form.get("name")
    phone = request.form.get("phone")

    cursor.execute(
        "INSERT INTO emergency_contacts(user_id, name, phone) VALUES(%s,%s,%s)",
        (session["user_id"], name, phone)
    )
    db.commit()

    return redirect("/emergency")   # reload page

@app.route("/delete_contact/<int:id>")
def delete_contact(id):

    cursor.execute(
        "DELETE FROM emergency_contacts WHERE id=%s AND user_id=%s",
        (id, session["user_id"])   # ✅ secure
    )
    db.commit()

    return redirect("/emergency")



    
# ===============================
# Share Location
# ===============================
@app.route("/send_location", methods=["POST"])
def send_location():
    data = request.json
    latitude = data["lat"]
    longitude = data["lon"]
    map_link = f"https://maps.google.com/?q={latitude},{longitude}"

    cursor.execute(
        "INSERT INTO emergency_locations(user_id, latitude, longitude) VALUES (%s,%s,%s)",
        (session["user_id"], latitude, longitude)
    )
    db.commit()
    return jsonify({"status": "Location saved", "map_link": map_link})



# Voice SOS
@app.route("/send_voice_sos", methods=["POST"])
def send_voice_sos():

    audio = request.files["audio"]

    lat = request.form.get("lat")
    lon = request.form.get("lon")

    filename = f"voice_sos_{session['user_id']}_{int(time.time())}.wav"

    path = os.path.join("static/voice", filename)

    audio.save(path)

    location_link = f"https://maps.google.com/?q={lat},{lon}"

    cursor.execute(
        "SELECT name,phone,email FROM emergency_contacts WHERE user_id=%s",
        (session["user_id"],)
    )

    contacts = cursor.fetchall()

    message = f"🚨 Voice SOS Alert!\nUser needs help.\nLocation: {location_link}"

    for c in contacts:

        phone = c["phone"]
        email = c["email"]

        # SMS
        try:
            client.messages.create(
                body=message,
                from_=TWILIO_PHONE,
                to=phone
            )
        except Exception as e:
            print("SMS error:", e)

        # WhatsApp
        try:
            client.messages.create(
                body=message,
                from_='whatsapp:+14155238886',
                to='whatsapp:'+phone
            )
        except Exception as e:
            print("WhatsApp error:", e)

        # Email
        try:
            msg = EmailMessage()
            msg["Subject"] = "Emergency Voice SOS Alert"
            msg["From"] = "youremail@gmail.com"
            msg["To"] = email
            msg.set_content(message)

            with smtplib.SMTP_SSL("smtp.gmail.com",465) as smtp:
                smtp.login("youremail@gmail.com","your_app_password")
                smtp.send_message(msg)

        except Exception as e:
            print("Email error:", e)

    return jsonify({"status":"Voice SOS sent"})

@app.route("/save_voice_evidence", methods=["POST"])
def save_voice_evidence():

    audio=request.files["audio"]
    lat=request.form.get("lat")
    lon=request.form.get("lon")

    filename=f"evidence_{session['user_id']}_{int(time.time())}.webm"

    path=os.path.join("static/voice",filename)

    audio.save(path)

    cursor.execute(
        "INSERT INTO voice_evidence(user_id,file_path,latitude,longitude) VALUES(%s,%s,%s,%s)",
        (session["user_id"],filename,lat,lon)
    )

    db.commit()

    return jsonify({"status":"Evidence saved"})


@app.route("/save_tracking", methods=["POST"])
def save_tracking():

    data = request.get_json()

    lat = data.get("lat")
    lon = data.get("lon")

    cursor.execute(
        "INSERT INTO tracking_logs(user_id, latitude, longitude) VALUES(%s,%s,%s)",
        (session["user_id"], lat, lon)
    )

    db.commit()

    return jsonify({"message":"Tracking saved"})

@app.route("/get_last_location")
def get_last_location():

    cursor.execute(
        "SELECT latitude, longitude FROM tracking_logs WHERE user_id=%s ORDER BY id DESC LIMIT 1",
        (session["user_id"],)
    )

    result = cursor.fetchone()

    return jsonify(result)


#Emergency button routes



    contacts = cursor.fetchall()

    # Send email alert
@app.route("/trigger_sos", methods=["POST"])
def trigger_sos():

    data = request.get_json()

    lat = data["latitude"]
    lon = data["longitude"]

    user_name = session.get("name")

    location_link = f"https://maps.google.com/?q={lat},{lon}"

    sos_message = f"""
🚨 SOS ALERT 🚨

{user_name} needs help immediately.

📍 Live Location:
{location_link}

Please contact or reach them immediately.
"""

    cursor = db.cursor()

    cursor.execute("""
    INSERT INTO sos_alerts(user_id, latitude, longitude, message)
    VALUES(%s,%s,%s,%s)
    """, (session["user_id"], lat, lon, sos_message))

    db.commit()

    return jsonify({
        "message": sos_message
    })





#Incident Reporting & Feedback System

@app.route("/incident_reporting")
def incident_reporting():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("incident_reporting.html")


@app.route("/submit_report", methods=["POST"])
def submit_report():

    if "user_id" not in session:
        return redirect("/login")

    incident_type = request.form["incident_type"]
    description = request.form["description"]
    location = request.form["location"]
    urgency = request.form["urgency"]

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO incident_reports 
        (user_id, incident_type, description, location, urgency_level)
        VALUES (%s,%s,%s,%s,%s)
    """, (session["user_id"], incident_type, description, location, urgency))

    report_id = cursor.lastrowid

    # Evidence upload
    if "evidence" in request.files:

        file = request.files["evidence"]

        if file.filename != "":
            filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
            path = os.path.join("static/evidence", filename)
            file.save(path)

            cursor.execute("""
                INSERT INTO incident_evidence 
                (report_id,file_path,file_type)
                VALUES (%s,%s,%s)
            """, (report_id, filename, file.content_type))

    db.commit()

    flash("Incident reported successfully!", "success")

    return redirect("/dashboard")

@app.route("/feedback")
def feedback():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("feedback.html")



@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():

    rating = request.form["rating"]
    feedback_type = request.form["feedback_type"]
    comments = request.form["comments"]

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO feedback
        (user_id,rating,feedback_type,comments)
        VALUES (%s,%s,%s,%s)
    """, (session["user_id"], rating, feedback_type, comments))

    db.commit()

    flash("Thank you for your feedback!", "success")

    return redirect("/dashboard")


@app.route("/incident_center")
def incident_center():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("incident_center.html")



# ================= MANAGE SCHEMES =================
@app.route("/manage_schemes")
def manage_schemes():
    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM schemes")
    schemes = cursor.fetchall()

    return render_template("manage_schemes.html", schemes=schemes)


# ================= ADD SCHEME =================
@app.route("/add_scheme", methods=["GET","POST"])
def add_scheme():
    if request.method == "POST":
        name = request.form["scheme_name"]
        desc = request.form["description"]

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO schemes (scheme_name, description) VALUES (%s,%s)",
            (name, desc)
        )
        db.commit()
        return redirect("/manage_schemes")

    return render_template("add_scheme.html")


# ================= EDIT SCHEME =================
@app.route("/edit_scheme/<int:id>", methods=["GET","POST"])
def edit_scheme(id):
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["scheme_name"]
        desc = request.form["description"]

        cursor.execute(
            "UPDATE schemes SET scheme_name=%s, description=%s WHERE id=%s",
            (name, desc, id)
        )
        db.commit()
        return redirect("/manage_schemes")

    cursor.execute("SELECT * FROM schemes WHERE id=%s", (id,))
    scheme = cursor.fetchone()

    return render_template("edit_scheme.html", scheme=scheme)


# ================= DELETE SCHEME =================
@app.route("/delete_scheme/<int:id>")
def delete_scheme(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM schemes WHERE id=%s", (id,))
    db.commit()
    return redirect("/manage_schemes")



@app.route("/admin/users")
def admin_users_list():
    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, full_name, email, phone FROM users")
    users = cursor.fetchall()

    return render_template("admin_users.html", users=users)

@app.route("/delete_user/<int:id>")
def delete_user_account(id):
    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s", (id,))
    db.commit()

    return redirect("/admin/users")



@app.route("/admin/sos_alerts")
def admin_sos_alerts():
    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.*, u.full_name, u.phone
        FROM sos_alerts s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.created_at DESC
    """)

    alerts = cursor.fetchall()

    return render_template("admin_sos.html", alerts=alerts)


@app.route("/approve_application/<int:id>")
def approve_application(id):
    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor()
    cursor.execute(
        "UPDATE scheme_applications SET application_status='Approved' WHERE id=%s",
        (id,)
    )
    db.commit()

    return redirect("/admin/applications")

@app.route("/reject_application/<int:id>")
def reject_application(id):
    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor()
    cursor.execute(
        "UPDATE scheme_applications SET application_status='Rejected' WHERE id=%s",
        (id,)
    )
    db.commit()

    return redirect("/admin/applications")

@app.route("/admin_incidents")
def admin_incidents():

    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT ir.id, ir.description, ir.location, ir.status, ir.created_at,
               u.full_name
        FROM incident_reports ir
        JOIN users u ON ir.user_id = u.id
        ORDER BY ir.created_at DESC
    """)

    reports = cursor.fetchall()

    return render_template("admin_incidents.html", reports=reports)




@app.route("/admin_reports_advanced")
def admin_reports_advanced():

    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    # ================= SCHEME APPLICATIONS =================
    cursor.execute("""
        SELECT s.scheme_name, COUNT(sa.id) as total
        FROM schemes s
        LEFT JOIN scheme_applications sa ON s.id = sa.scheme_id
        GROUP BY s.id
    """)
    scheme_data = cursor.fetchall()

    # ================= STATUS DATA =================
    cursor.execute("""
        SELECT application_status, COUNT(*) as total
        FROM scheme_applications
        GROUP BY application_status
    """)
    status_data = cursor.fetchall()

    # ================= USER ACTIVITY (DATE WISE) =================
    cursor.execute("""
        SELECT DATE(applied_date) as date, COUNT(*) as total
        FROM scheme_applications
        GROUP BY DATE(applied_date)
        ORDER BY date
    """)
    user_activity = cursor.fetchall()

    return render_template(
        "admin_reports.html",
        scheme_data=scheme_data,
        status_data=status_data,
        user_activity=user_activity
    )







@app.route("/download_report_csv")
def download_report_csv():

    cursor = db.cursor()
    cursor.execute("SELECT * FROM scheme_applications")
    data = cursor.fetchall()

    import csv
    from flask import Response

    def generate():
        yield "ID,User,Scheme,Status\n"
        for row in data:
            yield f"{row[0]},{row[1]},{row[2]},{row[12]}\n"

    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=report.csv"})


@app.route('/admin/incidents')
def view_incidents():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="women_security_db"
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, user_id, description, location, status, created_at
        FROM incident_reports
        ORDER BY created_at DESC
    """)

    reports = cursor.fetchall()
    return render_template('admin_incidents.html', reports=reports)

@app.route('/update_incident/<int:id>/<status>')
def update_incident(id, status):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="women_security_db"
    )
    cursor = conn.cursor()

    cursor.execute("UPDATE incident_reports SET status=%s WHERE id=%s", (status, id))
    conn.commit()

    return redirect('/admin/incidents')

@app.route('/delete_incident/<int:id>')
def delete_incident(id):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="women_security_db"
    )
    cursor = conn.cursor()

    cursor.execute("DELETE FROM incident_reports WHERE id=%s", (id,))
    conn.commit()

    return redirect('/admin/incidents')


@app.route('/admin/scheme/<int:scheme_id>')
def view_scheme_applications(scheme_id):
    cursor = db.cursor(dictionary=True)

    # 1️⃣ Fetch applications
    cursor.execute("""
        SELECT full_name, email, phone, application_status, applied_date
        FROM scheme_applications
        WHERE scheme_id = %s
        ORDER BY applied_date DESC
    """, (scheme_id,))
    applications = cursor.fetchall()

    # 2️⃣ ADD THIS PART HERE 👇 (after applications)
    cursor.execute("SELECT scheme_name FROM schemes WHERE id = %s", (scheme_id,))
    scheme = cursor.fetchone()
    scheme_name = scheme['scheme_name'] if scheme else "Scheme"

    # 3️⃣ Return with scheme_name
    return render_template(
        'scheme_applications.html',
        applications=applications,
        scheme_name=scheme_name
    )



@app.route("/admin/user/<int:user_id>")
def admin_user_details(user_id):

    if "admin" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    # USER DATA
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    # USER APPLICATIONS
    cursor.execute("""
    SELECT sa.*, s.scheme_name, u.full_name
    FROM scheme_applications sa
    JOIN schemes s ON sa.scheme_id = s.id
    JOIN users u ON sa.user_id = u.id
    WHERE sa.user_id = %s
""", (user_id,))
    applications = cursor.fetchall()

    return render_template(
        "admin_user_details.html",
        user=user,
        applications=applications
    )


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)