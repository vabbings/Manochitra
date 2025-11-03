from flask import Flask, request, jsonify, render_template
import os
import requests
from pathlib import Path
import sqlite3
import json
import time
from typing import Optional, List, Dict, Any
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# PDF Processing imports
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.tag import pos_tag
    from collections import Counter
    NLTK_AVAILABLE = True
    # Download required NLTK data if not already downloaded
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
    except:
        pass
except ImportError:
    NLTK_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'  # Change this in production!
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Optional: load environment variables from a local .env file (no extra deps) ---
BASE_DIR = Path(__file__).resolve().parent
def load_env_from_dotenv(filepath: Path = BASE_DIR / '.env') -> None:
    env_path = Path(filepath)
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v and not os.getenv(k):
                os.environ[k] = v
    except Exception:
        pass

# Attempt to load .env early so os.getenv works below
load_env_from_dotenv()

# --- SQLite databases ---
DB_PATH = 'cache.db'
DOCUMENTS_DB_PATH = 'documents.db'
CACHE_TTL_SECONDS = 3600  # 1 hour

def init_cache_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mindmap_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                model TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cache_topic_model ON mindmap_cache(topic, model)")
        conn.commit()
    finally:
        conn.close()

def init_documents_db():
    try:
        conn = sqlite3.connect(DOCUMENTS_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_email TEXT NOT NULL,
                filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                uploaded_at INTEGER NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)")
        conn.commit()
    finally:
        conn.close()

def get_cached_response(topic: str, model: str):
    now_ts = int(time.time())
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT response_json, created_at FROM mindmap_cache WHERE topic = ? AND model = ? ORDER BY id DESC LIMIT 1",
            (topic, model),
        )
        row = cur.fetchone()
        if not row:
            return None
        response_json, created_at = row
        if now_ts - int(created_at) > CACHE_TTL_SECONDS:
            return None
        try:
            return json.loads(response_json)
        except Exception:
            return None
    finally:
        conn.close()

def set_cached_response(topic: str, model: str, data: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO mindmap_cache(topic, model, response_json, created_at) VALUES (?, ?, ?, ?)",
            (topic, model, json.dumps(data), int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()

# Initialize databases
init_cache_db()
init_documents_db()

# Preferred models (in order). We'll try to pick the first one your API key can access.
PREFERRED_MODEL_KEYS = [
    # Prefer higher-quality models first
    "gemini-2.5-pro",
    "gemini-1.5-pro-latest",
    "gemini-1.5-pro",
    "gemini-2.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]

MODELS_LIST_URL = "https://generativelanguage.googleapis.com/v1beta/models"

def list_available_models(api_key: str) -> List[str]:
    """Return list of model names (short form like 'gemini-2.5-flash' or 'models/gemini-2.5-flash')."""
    try:
        r = requests.get(f"{MODELS_LIST_URL}?key={api_key}", timeout=20)
        r.raise_for_status()
        payload = r.json()
        models = payload.get("models") or []
        names = []
        for m in models:
            name = m.get("name")
            if not name:
                continue
            # name often is "models/gemini-2.5-flash". Normalize to short name.
            if name.startswith("models/"):
                names.append(name.split("/", 1)[1])
            else:
                names.append(name)
        return names
    except Exception:
        return []

def choose_model(api_key: str) -> Optional[str]:
    """
    Choose the best model available from PREFERRED_MODEL_KEYS.
    Returns the short model name (e.g. 'gemini-2.5-flash') or None if none available.
    """
    available = list_available_models(api_key)
    if not available:
        return None
    for prefer in PREFERRED_MODEL_KEYS:
        for a in available:
            if a == prefer or a.startswith(prefer):
                return a
    # If none matched, return first available as last resort
    return available[0] if available else None

def generate_content_url_for_model(model_short_name: str, api_key: str) -> str:
    """Construct the generateContent URL; include ?key= for API-key auth (and we also send header)."""
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model_short_name}:generateContent?key={api_key}"

def build_fallback_response(topic: str) -> dict:
    """Return a deterministic fallback mind map so the UI always renders something."""
    base_learn = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
    return {
        "topic": topic,
        "root": {
            "title": topic,
            "image": "",
            "learn_more": base_learn,
            "children": [
                {
                    "title": "Overview",
                    "image": "",
                    "learn_more": base_learn,
                    "children": []
                },
                {
                    "title": "Key Concepts",
                    "image": "",
                    "learn_more": base_learn,
                    "children": []
                },
                {
                    "title": "Further Reading",
                    "image": "",
                    "learn_more": base_learn,
                    "children": []
                }
            ]
        }
    }

# --- PDF Processing Functions ---

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file using available libraries."""
    text = ""
    
    # Try pdfplumber first (better for complex PDFs)
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text.strip()
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
    
    # Fallback to PyPDF2
    if PYPDF2_AVAILABLE:
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
    
    raise Exception("Could not extract text from PDF. Please ensure pdfplumber or PyPDF2 is installed.")

def analyze_topics_hierarchy(text: str) -> Dict[str, Any]:
    """
    Analyze text and extract hierarchical topics structure.
    Returns a mindmap structure with main topic, subtopics, and super topics.
    """
    if not NLTK_AVAILABLE:
        # Basic fallback without NLP
        return create_basic_mindmap(text)
    
    try:
        # Extract sentences
        sentences = sent_tokenize(text[:10000])  # Limit to first 10k chars for performance
        
        # Find headings and topics (typically capitalized or short sentences)
        headings = []
        for sentence in sentences:
            words = word_tokenize(sentence)
            if len(words) <= 8 and len(sentence) < 100:  # Likely a heading
                tagged = pos_tag(words)
                # Check if it starts with a noun or proper noun
                if tagged and tagged[0][1] in ['NN', 'NNP', 'NNS', 'NNPS']:
                    headings.append(sentence.strip())
        
        # Get main topic (most common heading or first heading)
        main_topic = headings[0] if headings else "Document Topics"
        
        # Extract key concepts as subtopics
        words = word_tokenize(text[:5000].lower())
        stop_words = set(stopwords.words('english'))
        filtered_words = [w for w in words if w.isalnum() and w not in stop_words]
        word_freq = Counter(filtered_words)
        
        # Get top concepts
        top_words = [word for word, count in word_freq.most_common(20)]
        
        # Create subtopics from headings or key concepts
        subtopics = headings[1:7] if len(headings) > 1 else top_words[:6]
        
        # Build mindmap structure
        children = []
        for idx, subtopic in enumerate(subtopics):
            # Create super topics (sub-concepts) for each subtopic
            super_topics = []
            # Extract sentences mentioning this subtopic
            for sentence in sentences[:50]:
                if subtopic.lower() in sentence.lower():
                    words = word_tokenize(sentence)
                    # Get descriptive words
                    descriptive = [w for w in words if w.isalnum() and len(w) > 3 and w not in stop_words]
                    if descriptive:
                        super_topics.append({
                            "title": ' '.join(descriptive[:4]),
                            "image": "",
                            "learn_more": "",
                            "children": []
                        })
                        if len(super_topics) >= 3:
                            break
            
            # Add bullet points from relevant sentences
            bullet_points = []
            for sentence in sentences[:30]:
                if subtopic.lower() in sentence.lower() and len(sentence) < 200:
                    bullet_points.append(sentence.strip()[:150])
                    if len(bullet_points) >= 5:
                        break
            
            children.append({
                "title": subtopic,
                "image": "",
                "learn_more": "",
                "children": super_topics,
                "bulletPoints": bullet_points[:5] if bullet_points else []
            })
        
        return {
            "topic": main_topic,
            "root": {
                "title": main_topic,
                "image": "",
                "learn_more": "",
                "children": children,
                "bulletPoints": []
            }
        }
        
    except Exception as e:
        print(f"Error in topic analysis: {e}")
        return create_basic_mindmap(text)

def create_basic_mindmap(text: str) -> Dict[str, Any]:
    """Create a basic mindmap structure without advanced NLP."""
    # Split text into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()][:20]
    
    main_topic = paragraphs[0][:100] if paragraphs else "Document"
    
    # Create subtopics from paragraphs
    children = []
    for i, para in enumerate(paragraphs[1:7]):  # Take first 6 paragraphs
        # Split into sentences for description
        sentences = para.split('.')[:3]
        description = '. '.join(s for s in sentences if s.strip())[:200]
        
        children.append({
            "title": f"Section {i+1}",
            "image": "",
            "learn_more": "",
            "children": [],
            "bulletPoints": [desc[:100] for desc in para.split('.')[:5] if desc.strip()]
        })
    
    return {
        "topic": main_topic[:100],
        "root": {
            "title": main_topic[:100],
            "image": "",
            "learn_more": "",
            "children": children,
            "bulletPoints": []
        }
    }

@app.route("/")
def landing_page():
    """Login page route"""
    return render_template("landingpage.html")
@app.route("/login")
def login_page():
    """Login page route"""
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    """Sign up page route"""
    return render_template("signup.html")

@app.route("/frontpage")
def frontpage():
    """Frontpage route - protected by Firebase on client side"""
    return render_template("frontpage.html")

@app.route("/mindmap")
def mindmap_page():
    """Mind map page route"""
    return render_template("mindmap.html")

@app.route("/api/mindmap", methods=["GET"])
def api_mindmap():
    """Generate a mind map JSON for a given topic via Gemini."""
    topic = request.args.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "Missing 'topic' query parameter"}), 400

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY environment variable not set on server"}), 500

    # Allow memory-cache bypass
    no_cache = request.args.get("nocache", "0").strip() == "1"

    # Determine model dynamically (and cache choice in request-lifetime)
    chosen_model = choose_model(api_key)
    if not chosen_model:
        return jsonify({
            "error": "Unable to list available models with provided API key. "
                     "Ensure your key is a valid Gemini API key and has access to models.",
            "hint": "Try creating an API key at https://aistudio.google.com/app/apikey and set GEMINI_API_KEY."
        }), 502

    model_for_cache = chosen_model
    if not no_cache:
        cached = get_cached_response(topic, model_for_cache)
        if cached and isinstance(cached, dict) and cached.get("topic") and cached.get("root"):
            return jsonify(cached)

    system_prompt = (
        "You output STRICT JSON for a mind map. Build a deeply structured, study-ready outline for the topic. "
        "REQUIREMENTS (enforce strictly):\n"
        "- Top-level: 6-8 sections tailored to the topic (no filler).\n"
        "- For EACH top-level section: include bulletPoints with 5-9 short, factual bullets.\n"
        "- For EACH top-level section: include 3-5 children subsections.\n"
        "- For EACH subsection child: include bulletPoints with 3-6 bullets (concise) and may include its own children if helpful.\n"
        "- Every node fields: title (string), learn_more (string URL or empty), bulletPoints (array<string>), children (array).\n"
        "- Prefer concrete, current terminology; avoid placeholders like '[current name]'.\n"
        "- If the topic is an institution (e.g., Indian Army), good top-level sections are: Overview; Organizational Structure; Major Operations & Wars; Modernization & Technology; Recruitment & Training; Contributions & Roles; Future Vision; Notable Units/Regiments.\n"
        "- If the topic is a concept, adapt the section names accordingly (Definition; Key Concepts; Mechanisms; Applications; History; Case Studies; Common Misconceptions; Further Reading)."
    )

    simple_payload = {
        "contents": [{
            "parts": [{
                "text": (
                    "Return ONLY valid JSON for a mind map with fields: "
                    "topic (string), root (object: title, learn_more, bulletPoints[array<string>], children[] of same shape).\n"
                    f"{system_prompt}\nUser topic: {topic}"
                )
            }]
        }]
    }

    try:
        url = generate_content_url_for_model(chosen_model, api_key)
        data = post_and_parse(url, simple_payload, api_key)

        # If the service returned direct JSON
        if isinstance(data, dict) and "topic" in data and "root" in data:
            try:
                set_cached_response(topic, model_for_cache, data)
            except Exception:
                pass
            return jsonify(data)

        # Otherwise inspect 'candidates' -> content -> parts -> text (common Gemini shape)
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
        for c in candidates:
            parts = (((c or {}).get("content") or {}).get("parts")) or []
            for p in parts:
                text = p.get("text")
                if not text:
                    continue
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and "topic" in parsed and "root" in parsed:
                        try:
                            set_cached_response(topic, model_for_cache, parsed)
                        except Exception:
                            pass
                        return jsonify(parsed)
                except Exception:
                    continue

        # If we reach here, format wasn't found
        fallback = build_fallback_response(topic)
        try:
            set_cached_response(topic, model_for_cache, fallback)
        except Exception:
            pass
        return jsonify(fallback), 200

    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        body = None
        try:
            body = e.response.text
        except Exception:
            body = None

        # Helpful troubleshooting info for 404/403
        if status == 404:
            # Serve fallback to keep UX working
            fallback = build_fallback_response(topic)
            return jsonify(fallback), 200

        if status == 403:
            fallback = build_fallback_response(topic)
            return jsonify(fallback), 200

        fallback = build_fallback_response(topic)
        return jsonify(fallback), 200

    except requests.RequestException as e:
        fallback = build_fallback_response(topic)
        return jsonify(fallback), 200

@app.route("/api/upload-pdf", methods=["POST"])
def upload_pdf():
    """Handle PDF file uploads"""
    try:
        if 'pdf' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['pdf']
        user_id = request.form.get('user_id', '').strip()
        user_email = request.form.get('user_email', '').strip()
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not user_id or not user_email:
            return jsonify({"error": "User authentication required"}), 401
        
        # Check if it's a PDF
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        # Secure filename
        original_filename = file.filename
        timestamp = int(time.time())
        safe_filename = secure_filename(original_filename)
        stored_filename = f"{user_id}_{timestamp}_{safe_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
        
        # Save file
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Store metadata in database
        try:
            conn = sqlite3.connect(DOCUMENTS_DB_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO documents (user_id, user_email, filename, stored_filename, file_path, file_size, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, user_email, original_filename, stored_filename, file_path, file_size, timestamp)
            )
            conn.commit()
            doc_id = cur.lastrowid
            conn.close()
        except Exception as db_error:
            # Clean up file if database insert fails
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": "Failed to save document metadata"}), 500
        
        return jsonify({
            "success": True,
            "message": "File uploaded successfully",
            "document_id": doc_id,
            "filename": original_filename,
            "size": file_size
        }), 200
        
    except RequestEntityTooLarge:
        return jsonify({"error": "File too large. Maximum size is 16MB"}), 413
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@app.route("/api/user-documents", methods=["GET"])
def get_user_documents():
    """Get all documents for a specific user"""
    try:
        user_id = request.args.get('user_id', '').strip()
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        conn = sqlite3.connect(DOCUMENTS_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, filename, file_size, uploaded_at
            FROM documents
            WHERE user_id = ?
            ORDER BY uploaded_at DESC
            """,
            (user_id,)
        )
        
        rows = cur.fetchall()
        conn.close()
        
        documents = []
        for row in rows:
            documents.append({
                "id": row[0],
                "filename": row[1],
                "file_size": row[2],
                "uploaded_at": row[3]
            })
        
        return jsonify({"documents": documents}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch documents: {str(e)}"}), 500

@app.route("/api/delete-document/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    """Delete a specific document"""
    try:
        # Get document info first
        conn = sqlite3.connect(DOCUMENTS_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT file_path FROM documents WHERE id = ?",
            (doc_id,)
        )
        row = cur.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"error": "Document not found"}), 404
        
        file_path = row[0]
        
        # Delete from database
        cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
        
        # Delete file from disk
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass  # Continue even if file deletion fails
        
        return jsonify({"success": True, "message": "Document deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to delete document: {str(e)}"}), 500

@app.route("/api/pdf-mindmap/<int:doc_id>", methods=["GET"])
def generate_pdf_mindmap(doc_id):
    """Generate a mindmap from an uploaded PDF document."""
    try:
        # Get document info from database
        conn = sqlite3.connect(DOCUMENTS_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT file_path, user_id FROM documents WHERE id = ?",
            (doc_id,)
        )
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Document not found"}), 404
        
        file_path = row[0]
        user_id = row[1]
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({"error": "PDF file not found on server"}), 404
        
        # Extract text from PDF
        text = extract_text_from_pdf(file_path)
        
        if not text or len(text) < 100:
            return jsonify({"error": "Could not extract meaningful text from PDF"}), 400
        
        # Analyze topics and create mindmap
        mindmap = analyze_topics_hierarchy(text)
        
        return jsonify(mindmap), 200
        
    except Exception as e:
        print(f"Error generating PDF mindmap: {e}")
        return jsonify({"error": f"Failed to generate mindmap: {str(e)}"}), 500

@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not found", "path": request.path}), 404
    return e

@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Server error", "path": request.path}), 500
    return e

def post_and_parse(url_to_use: str, payload_to_use: dict, api_key: str):
    headers = {"Content-Type": "application/json", "Accept": "application/json", "x-goog-api-key": api_key}
    # Retry with exponential backoff to mitigate transient network slowness/timeouts
    max_retries = 3
    backoff = 2
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(url_to_use, json=payload_to_use, headers=headers, timeout=60)
            r.raise_for_status()
            return r.json()
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            if attempt == max_retries:
                break
            time.sleep(backoff)
            backoff *= 2
        except requests.HTTPError:
            # For HTTP errors, don't retry here; let caller handle status codes
            raise
    # If we exhausted retries on network errors
    raise requests.RequestException(f"Network error after retries: {last_exc}")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5173, debug=True)
