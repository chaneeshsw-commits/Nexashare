from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import uuid
import cv2
import numpy as np
from PIL import Image
import qrcode

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# temporary storage
shared_files = {}

# HOME PAGE
@app.route("/")
def home():
    return render_template("index.html")


# STEP 1 → Upload files
@app.route("/upload_files", methods=["POST"])
def upload_files():
    files = request.files.getlist("files")

    if not files:
        return jsonify({
            "success": False,
            "message": "No files uploaded"
        })

    session_id = str(uuid.uuid4())
    uploaded_names = []

    for file in files:
        if file.filename != "":
            filename = file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            uploaded_names.append(filename)

    # session temp save
    shared_files[session_id] = uploaded_names

    return jsonify({
        "success": True,
        "count": len(uploaded_names),
        "session_id": session_id
    })


# STEP 2 → Convert QR + create share link
@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json()
    session_id = data.get("session_id")

    if not session_id or session_id not in shared_files:
        return jsonify({
            "success": False,
            "message": "Invalid session"
        })

    share_id = str(uuid.uuid4())

    # files mapping
    shared_files[share_id] = shared_files[session_id]

    # REAL SHARE LINK
    share_url = request.host_url + "share/" + share_id

    # QR generate in static folder
    qr = qrcode.make(share_url)
    qr.save("static/qr.png")

    return jsonify({
        "success": True,
        "share_id": share_id,
        "share_url": share_url
    })


# STEP 3 → Result page
@app.route("/share/<share_id>")
def share_page(share_id):
    if share_id not in shared_files:
        return "Invalid link ❌"

    files = shared_files[share_id]

    return render_template(
        "result.html",
        files=files,
        share_id=share_id
    )


# OPEN uploaded files
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)




# scaner uplode  
@app.route("/scan_qr_upload", methods=["POST"])
def scan_qr_upload():
    qr_file = request.files.get("qr_file")

    if not qr_file:
        return {"success": False}

    try:
        # image read
        img = Image.open(qr_file).convert("RGB")
        img_np = np.array(img)

        detector = cv2.QRCodeDetector()
        qr_data, bbox, _ = detector.detectAndDecode(img_np)

        if not qr_data:
            return {
                "success": False,
                "message": "QR not detected"
            }

        print("QR DATA:", qr_data)

        if "/share/" not in qr_data:
            return {
                "success": False,
                "message": "Invalid share link"
            }

        share_id = qr_data.split("/share/")[-1]

        return {
            "success": True,
            "share_id": share_id
        }

    except Exception as e:
        print("QR Decode Error:", str(e))
        return {
            "success": False,
            "message": "QR decode failed"
        }



# scann result 
@app.route("/scan-result/<share_id>")
def scan_result(share_id):

    if share_id not in shared_files:
        return "Invalid link ❌"

    files = shared_files[share_id]

    return render_template(
        "scan_result.html",
        files=files,
        share_id=share_id
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )