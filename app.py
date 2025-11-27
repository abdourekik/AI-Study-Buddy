from flask import Flask, render_template, request, jsonify, send_file
from groq import Groq
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import PyPDF2
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads folder if it doesn't exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Store conversations and PDFs in memory
conversations = {}
pdf_contents = {}

MODES = {
    "explain": """You are a friendly Study Buddy AI in EXPLAIN MODE. Explain concepts clearly with examples and analogies. Keep responses concise but thorough.""",
    
    "quiz": """You are a Study Buddy AI in QUIZ MODE. Generate engaging quiz questions and provide immediate feedback. Be educational and encouraging.""",
    
    "review": """You are a Study Buddy AI in REVIEW MODE. Create concise study notes and summaries. Highlight key points and important facts in a structured way.""",
    
    "practice": """You are a Study Buddy AI in PRACTICE MODE. Create practice problems and exercises. Provide step-by-step solutions and helpful hints.""",
    
    "summarize": """You are a Study Buddy AI in SUMMARIZE MODE. Create clear, concise summaries of content. Extract the most important information and present it in an organized way."""
}

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    session_id = data.get('session_id', 'default')
    mode = data.get('mode', 'explain')
    temperature = float(data.get('temperature', 0.7))
    max_tokens = int(data.get('max_tokens', 800))
    
    # Initialize conversation if needed
    if session_id not in conversations:
        conversations[session_id] = []
    
    # Check if there's PDF content for this session
    pdf_context = ""
    if session_id in pdf_contents:
        pdf_context = f"\n\nContext from uploaded document:\n{pdf_contents[session_id][:3000]}\n\n"
    
    # Add user message
    conversations[session_id].append({
        "role": "user",
        "content": user_message
    })
    
    # Get AI response
    try:
        messages_to_send = [{"role": "system", "content": MODES[mode] + pdf_context}] + conversations[session_id]
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_to_send,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        ai_message = response.choices[0].message.content
        
        # Add AI response to conversation
        conversations[session_id].append({
            "role": "assistant",
            "content": ai_message
        })
        
        return jsonify({
            "success": True,
            "message": ai_message
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"})
    
    file = request.files['pdf']
    session_id = request.form.get('session_id', 'default')
    
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"})
    
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text from PDF
        text = extract_text_from_pdf(filepath)
        
        if text:
            pdf_contents[session_id] = text
            
            # Generate summary
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": MODES['summarize']},
                        {"role": "user", "content": f"Please provide a concise summary of this document:\n\n{text[:4000]}"}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                summary = response.choices[0].message.content
                
                return jsonify({
                    "success": True,
                    "summary": summary,
                    "filename": filename
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Error generating summary: {str(e)}"
                })
        else:
            return jsonify({
                "success": False,
                "error": "Could not extract text from PDF"
            })
    
    return jsonify({
        "success": False,
        "error": "Invalid file type. Please upload a PDF."
    })

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    data = request.json
    session_id = data.get('session_id', 'default')
    
    if session_id not in pdf_contents:
        return jsonify({
            "success": False,
            "error": "No document uploaded. Please upload a PDF first."
        })
    
    try:
        content = pdf_contents[session_id][:4000]
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": MODES['quiz']},
                {"role": "user", "content": f"Based on this document, generate 5 multiple-choice questions to test understanding. Include the answer key at the end.\n\nDocument:\n{content}"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        quiz = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "quiz": quiz
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/clear', methods=['POST'])
def clear():
    data = request.json
    session_id = data.get('session_id', 'default')
    
    if session_id in conversations:
        conversations[session_id] = []
    if session_id in pdf_contents:
        del pdf_contents[session_id]
    
    return jsonify({"success": True})

@app.route('/save', methods=['POST'])
def save():
    data = request.json
    session_id = data.get('session_id', 'default')
    mode = data.get('mode', 'explain')
    
    if session_id not in conversations or not conversations[session_id]:
        return jsonify({"success": False, "error": "No conversation to save"})
    
    if not os.path.exists('study_sessions'):
        os.makedirs('study_sessions')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"study_sessions/session_{timestamp}.json"
    
    session_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "conversation": conversations[session_id],
        "had_pdf": session_id in pdf_contents
    }
    
    with open(filename, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    return jsonify({"success": True, "filename": filename})

@app.route('/get_history', methods=['GET'])
def get_history():
    if not os.path.exists('study_sessions'):
        return jsonify({"success": True, "sessions": []})
    
    sessions = []
    for filename in sorted(os.listdir('study_sessions'), reverse=True)[:10]:
        if filename.endswith('.json'):
            with open(f'study_sessions/{filename}', 'r') as f:
                session = json.load(f)
                sessions.append({
                    "filename": filename,
                    "date": session.get('date'),
                    "mode": session.get('mode'),
                    "messages": len(session.get('conversation', [])),
                    "had_pdf": session.get('had_pdf', False)
                })
    
    return jsonify({"success": True, "sessions": sessions})

if __name__ == '__main__':
    app.run(debug=True, port=5000)