
from flask import Flask, render_template, request, send_from_directory
import os
import qrcode

app = Flask(__name__)

#folders
UPLOAD_FOLDER = "uploads"
QR_FOLDER = "static"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

#home page

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/view/<filename>")
def view_file(filename):
    return render_template("view.html", filename=filename)

#file upload and qr generation

@app.route("/upload", methods=["POST"])
def upload():
    
    file = request.files["file"]
    if file and file.filename != "":
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

    # crete file url

        file_url = f"http://192.168.56.1:5000/view/{file.filename}"

         # generate qr code
        qr=qrcode.make(file_url)
        qr_path=os.path.join(QR_FOLDER, "qr.png")
        qr.save(qr_path)

        #show result page
        return render_template("result.html", qr_image="qr.png")
    
    return "No file selected"
   
   # route to access files
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# run app

if __name__ == "__main__":
    import os
    app.run(host="192.168.56.1", port=int(os.environ.get("PORT", 5000)))