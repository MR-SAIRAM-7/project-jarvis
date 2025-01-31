from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import os
import google.generativeai as genai
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
import docx

# Load API keys from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Set up Google Generative AI
genai_api_key = os.getenv("GOOGLE_API_KEY")
if not genai_api_key:
    raise ValueError("GOOGLE_API_KEY is missing in .env file")
genai.configure(api_key=genai_api_key)

# Function to interact with Gemini model (text-only)
def get_gemini_text_response(question):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(question)
        return response.text
    except Exception as e:
        return f"Error with Gemini model: {e}"

# Function to interact with Gemini model (image + text)
def get_gemini_image_response(input_text, image):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([input_text, image] if input_text else [image])
        return response.text
    except Exception as e:
        return f"Error with Gemini model: {e}"

# Route to handle chatbot interaction
@app.route('/get_response', methods=['POST'])
def get_response():
    user_input = request.json.get('question')
    if user_input:
        response_text = get_gemini_text_response(user_input)
        return jsonify({'answer': response_text})
    return jsonify({'error': 'No question provided'}), 400

# Serve the HTML and CSS files
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/styles.css')
def styles():
    return send_from_directory('static', 'style.css')

# Configurations
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to extract text from PDF
def extract_pdf_text(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            text = "".join(page.extract_text() for page in reader.pages)
        return text
    except Exception as e:
        return f"Error extracting PDF: {e}"

# Function to extract text from DOCX
def extract_docx_text(docx_path):
    try:
        doc = docx.Document(docx_path)
        text = "\n".join(para.text for para in doc.paragraphs)
        return text
    except Exception as e:
        return f"Error extracting DOCX: {e}"

# Handle file upload
@app.route('/upload_file', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'message': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process the file based on its type
            if filename.endswith('.txt'):
                with open(filepath, 'r') as f:
                    file_content = f.read()
            elif filename.endswith('.pdf'):
                file_content = extract_pdf_text(filepath)
            elif filename.endswith('.docx'):
                file_content = extract_docx_text(filepath)
            else:
                return jsonify({'message': 'Unsupported file type'}), 400

            # Send back the analyzed result (preview content)
            return jsonify({'message': f"File content preview: {file_content[:500]}..."})

        return jsonify({'message': 'Invalid file type'}), 400
    except Exception as e:
        return jsonify({'message': f"Error processing the file: {e}"}), 500

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
