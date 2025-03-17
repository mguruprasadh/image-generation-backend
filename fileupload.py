from flask import Flask, jsonify , request,send_file
from google import genai
from flask_cors import CORS
from google.genai import types
import pathlib
import base64
import os
import PyPDF2
import docx
import pandas as pd

app = Flask(__name__)
CORS(app)
client = genai.Client(api_key='AIzaSyCCyMhSt6XdZUcgNEORNMy4r6rLnTJCUA0')

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_text_from_file(file_path):
    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension == '.pdf':
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = "".join(page.extract_text() for page in reader.pages)
        return text

    elif file_extension == '.docx':
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    elif file_extension == '.txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    elif file_extension == '.csv':
        df = pd.read_csv(file_path)
        return df.to_string()

    elif file_extension in ['.xls', '.xlsx']:
        df = pd.read_excel(file_path)
        return df.to_string()

    else:
        return "Unsupported file format."

def generate_image(prompt):
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=['Image','Text'])
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            data = part.inline_data.data  # Fix tuple issue
            decoded_data = base64.b64decode(data)
            image_path = "generated_image.png"
            pathlib.Path(image_path).write_bytes(decoded_data)
            with open(image_path, "wb") as img_file:
                img_file.write(decoded_data)
            return image_path
    return None
# Upload File and Generate Image Endpoint
@app.route("/upload-file", methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    extracted_text = extract_text_from_file(file_path)
    if extracted_text in ["Unsupported file format.", "No text found in the PDF."]:
        return jsonify({"error": extracted_text}), 400

    image_path = generate_image(extracted_text[:500])  # Use first 500 characters as prompt

    if image_path:
        return send_file(image_path, mimetype='image/png')
    else:
        return jsonify({"error": "Failed to generate an image"}), 500
@app.route("/generated-image", methods=['POST'])
def generated_image_endpoint():
    data = request.json
    prompt = data.get("prompt")

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    image_path = generate_image(prompt)

    if image_path:
        return send_file(image_path, mimetype='image/png')
    else:
        return jsonify({"error": "failed to generate an image"}), 500

# ✅ Move this outside of function definitions
if __name__ == '__main__':
    app.run(debug=True, port=5000)