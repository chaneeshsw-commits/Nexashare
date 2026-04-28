from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
import zipfile
import qrcode

# =====================================================
# APP CONFIG
# =====================================================

app = Flask(__name__)
app.secret_key = "novashare_secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB

db = SQLAlchemy(app)

# Create uploads folder if not exists
if not os.path.exists("uploads"):
    os.makedirs("uploads")


# =====================================================
# DATABASE MODEL
# =====================================================

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # same code for grouped files
    code = db.Column(db.String(100))

    # actual saved filename
    filename = db.Column(db.String(300))

    # optional password
    password = db.Column(db.String(100), nullable=True)

    # expiry system
    # 0 = never expire
    expiry_days = db.Column(db.Integer, default=0)

    # analytics
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    downloads = db.Column(db.Integer, default=0)


with app.app_context():
    db.create_all()


# =====================================================
# HELPER FUNCTION
# =====================================================

def is_expired(item):
    if item.expiry_days == 0:
        return False

    expiry_date = item.created_at + timedelta(days=item.expiry_days)
    return datetime.utcnow() > expiry_date


# =====================================================
# PWA ROUTES
# =====================================================

@app.route("/manifest.json")
def manifest():
    return send_from_directory(".", "manifest.json")


@app.route("/service-worker.js")
def service_worker():
    return send_from_directory(".", "service-worker.js")


# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
def index():
    return render_template("index.html")


# =====================================================
# FILE UPLOAD + QR GENERATE
# =====================================================

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")

    if not files or files[0].filename == "":
        return "No file selected"

    password = request.form.get("password", "")
    expiry = request.form.get("expiry", 0)

    try:
        expiry = int(expiry)
    except:
        expiry = 0

    # shared code for all uploaded files
    code = str(uuid.uuid4())[:8]

    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)

            # unique saved filename
            unique_name = f"{code}_{filename}"

            save_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                unique_name
            )

            # save file
            file.save(save_path)

            # save DB row
            new_upload = Upload(
                code=code,
                filename=unique_name,
                password=password,
                expiry_days=expiry
            )

            db.session.add(new_upload)

    db.session.commit()

    # Generate QR for scan page
    qr_url = request.host_url + "result/" + code

    qr = qrcode.make(qr_url)

    qr_path = os.path.join(
        "static",
        f"{code}.png"
    )

    qr.save(qr_path)

    # Redirect to upload result page
    return redirect(
        url_for(
            "upload_result",
            code=code
        )
    )


# =====================================================
# UPLOAD RESULT PAGE
# (QR visible here)
# =====================================================

@app.route("/upload-result/<code>")
def upload_result(code):
    files = Upload.query.filter_by(code=code).all()

    if not files:
        return "Files not found"

    return render_template(
        "result.html",
        files=files,
        code=code
    )


# =====================================================
# SCAN RESULT PAGE
# (password + expiry + analytics)
# =====================================================

@app.route("/result/<code>", methods=["GET", "POST"])
def result(code):
    files = Upload.query.filter_by(code=code).all()

    if not files:
        return "Files not found"

    first_file = files[0]

    # Expiry Check
    if is_expired(first_file):
        return "This link has expired"

    # Password Protection
    if first_file.password:
        if request.method == "POST":
            entered_password = request.form.get("password")

            if entered_password != first_file.password:
                return render_template(
                    "password.html",
                    code=code,
                    error="Wrong Password"
                )
        else:
            return render_template(
                "password.html",
                code=code
            )

    # Analytics update
    for file in files:
        file.views += 1

    db.session.commit()

    return render_template(
        "scan_result.html",
        files=files,
        code=code
    )


# =====================================================
# FILE PREVIEW PAGE
# =====================================================

@app.route("/preview/<path:filename>")
def preview(filename):
    return render_template(
        "preview.html",
        filename=filename
    )


# =====================================================
# OPEN FILE (preview inside browser)
# =====================================================

@app.route("/file/<path:filename>")
def file_open(filename):
    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    if not os.path.exists(file_path):
        return "File not found"

    item = Upload.query.filter_by(
        filename=filename
    ).first()

    if item:
        item.downloads += 1
        db.session.commit()

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=False
    )


# =====================================================
# DOWNLOAD ALL FILES AS ZIP
# =====================================================

@app.route("/download-all/<code>")
def download_all(code):
    files = Upload.query.filter_by(code=code).all()

    if not files:
        return "Files not found"

    zip_filename = f"{code}_files.zip"

    zip_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        zip_filename
    )

    with zipfile.ZipFile(
        zip_path,
        "w"
    ) as zipf:

        for file in files:
            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                file.filename
            )

            if os.path.exists(file_path):
                zipf.write(
                    file_path,
                    arcname=file.filename
                )

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        zip_filename,
        as_attachment=True
    )


# =====================================================
# ADMIN PANEL
# =====================================================

@app.route("/admin")
def admin():
    uploads = Upload.query.order_by(
        Upload.created_at.desc()
    ).all()

    return render_template(
        "admin.html",
        uploads=uploads
    )


@app.route("/delete/<int:id>")
def delete(id):
    item = Upload.query.get_or_404(id)

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        item.filename
    )

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(item)
    db.session.commit()

    return redirect(
        url_for("admin")
    )


# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )