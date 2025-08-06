import os
import uuid
import base64
import datetime
import json
from io import BytesIO
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image, ImageFilter
import requests
from flask_caching import Cache
from dotenv import load_dotenv
from pi_network import PiNetwork

# Load environment variables
load_dotenv()

# Initialize Pi Network
pi = PiNetwork(
    api_key=os.getenv("PI_API_KEY"),
    wallet_private_seed=os.getenv("PI_WALLET_PRIVATE_SEED")
)

# --- APP SETUP ---
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "default-secret-key")
app.config.update(
    UPLOAD_FOLDER="static/user_artworks",
    LINE_ART_FOLDER="static/line_art",
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
    MUSIC_FILES=["forest.mp3", "piano.mp3", "waves.mp3"],
    PI_APP_ID=os.getenv("PI_APP_ID", "Natsly"),
    PI_WALLET_ADDRESS=os.getenv("PI_APP_WALLET_ADDRESS"),
    PI_SANDBOX=os.getenv("PI_SANDBOX", "False").lower() == "true"
)

# Create required directories
required_dirs = [
    "static/user_artworks",
    "static/line_art/mandalas",
    "static/line_art/animals",
    "static/line_art/nature",
    "static/line_art/ai_generated",
    "static/sounds"
]

for directory in required_dirs:
    os.makedirs(directory, exist_ok=True)

# Get categories and images
def get_categories():
    categories = {}
    base_path = app.config["LINE_ART_FOLDER"]
    for category in os.listdir(base_path):
        category_path = os.path.join(base_path, category)
        if os.path.isdir(category_path):
            images = [f for f in os.listdir(category_path) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            if images:
                categories[category] = images
    return categories

# AI configuration
AI_API_URL = "https://api.deepai.org/api/text2img"
AI_API_KEY = os.getenv("AI_API_KEY")

# ------------------
def get_daily_image():
    all_images = []
    for category, images in get_categories().items():
        all_images.extend([(category, img) for img in images])
    
    if not all_images:
        return ("default", "default.png")
    
    try:
        today = datetime.datetime.utcnow()
        idx = (today.year + today.month + today.day) % len(all_images)
        return all_images[idx]
    except Exception:
        return ("default", "default.png")

def generate_ai_pattern(prompt, w=512, h=512):
    key = f"ai::{prompt}::{w}x{h}"
    cached = cache.get(key)
    if cached:
        cached.seek(0)
        return cached
    
    # Create fallback image
    img = Image.new("RGB", (w, h), "white")
    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    
    # Try calling DeepAI if API key exists
    if AI_API_KEY:
        try:
            resp = requests.post(
                AI_API_URL,
                data={"text": prompt},
                headers={"api-key": AI_API_KEY},
                timeout=20
            )
            if resp.status_code == 200 and resp.json().get("output_url"):
                img_url = resp.json()["output_url"]
                img_data = requests.get(img_url, timeout=20).content
                bio = BytesIO(img_data)
                cache.set(key, bio)
                bio.seek(0)
                return bio
        except Exception as e:
            print(f"AI Generation Error: {e}")
    
    return bio

def convert_to_line_art(in_path):
    try:
        img = Image.open(in_path).convert("L")
        # Enhance edges
        img = img.filter(ImageFilter.FIND_EDGES)
        # Increase contrast
        img = ImageOps.autocontrast(img, cutoff=5)
        # Binarize
        bw = img.point(lambda p: 255 if p > 50 else 0)
        return bw
    except Exception as e:
        print(f"Line art conversion error: {e}")
        return None

# Initialize cache
cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600})
cache.init_app(app)

# ---- ROUTES ----

@app.route("/")
def gallery():
    categories = get_categories()
    daily_category, daily_filename = get_daily_image()
    daily_url = url_for("static", filename=f"line_art/{daily_category}/{daily_filename}")
    
    return render_template(
        "gallery.html",
        categories=categories,
        music_files=app.config["MUSIC_FILES"],
        daily_image=daily_url,
        daily_category=daily_category,
        daily_filename=daily_filename,
        pi_app_id=app.config["PI_APP_ID"],
        pi_wallet_address=app.config["PI_WALLET_ADDRESS"],
        sandbox=app.config["PI_SANDBOX"]
    )

@app.route("/coloring/<category>/<image_name>")
def coloring(category, image_name):
    safe_category = secure_filename(category)
    safe_image_name = secure_filename(image_name)
    image_path = os.path.join(app.config["LINE_ART_FOLDER"], safe_category, safe_image_name)
    
    if not os.path.exists(image_path):
        return redirect(url_for('gallery'))
    
    image_url = url_for("static", filename=f"line_art/{safe_category}/{safe_image_name}")
    return render_template(
        "coloring.html",
        image_url=image_url,
        music_files=app.config["MUSIC_FILES"],
        pi_app_id=app.config["PI_APP_ID"],
        pi_wallet_address=app.config["PI_WALLET_ADDRESS"],
        sandbox=app.config["PI_SANDBOX"]
    )

@app.route("/privacy")
def privacy_policy():
    return render_template("privacy.html")

@app.route("/terms")
def terms_of_service():
    return render_template("terms.html")

@app.route("/generate_ai", methods=["POST"])
def generate_ai_art():
    prompt = request.json.get("prompt", "mandala line art").strip()
    if not prompt:
        return jsonify(error="Prompt is required"), 400
    
    bio = generate_ai_pattern(prompt)
    data = "data:image/png;base64," + base64.b64encode(bio.read()).decode()
    return jsonify(image=data)

@app.route("/upload_artwork", methods=["POST"])
def upload_sketch():
    if 'file' not in request.files:
        return jsonify(error="No file part"), 400
        
    f = request.files['file']
    if f.filename == '':
        return jsonify(error="No selected file"), 400
    
    ai_category = "ai_generated"
    ai_path = os.path.join(app.config["LINE_ART_FOLDER"], ai_category)
    os.makedirs(ai_path, exist_ok=True)
    
    filename = secure_filename(f.filename)
    raw_path = os.path.join(ai_path, filename)
    f.save(raw_path)
    
    line_art = convert_to_line_art(raw_path)
    if not line_art:
        return jsonify(error="Image processing failed"), 500
    
    output_filename = f"line_art_{uuid.uuid4().hex}.png"
    output_path = os.path.join(ai_path, output_filename)
    line_art.save(output_path)
    
    return jsonify(
        status="success",
        url=url_for("static", filename=f"line_art/{ai_category}/{output_filename}")
    )

@app.route("/save_artwork", methods=["POST"])
def save_artwork():
    try:
        data = request.json.get("image", "")
        if not data or "," not in data:
            return jsonify(error="Invalid image data"), 400
            
        header, encoded = data.split(",", 1)
        image_data = base64.b64decode(encoded)
        filename = f"art_{uuid.uuid4().hex}.png"
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        
        with open(path, "wb") as f:
            f.write(image_data)
            
        return jsonify(
            status="success", 
            url=url_for("static", filename=f"user_artworks/{filename}")
        )
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    data = request.json
    txid = data.get('txid')
    
    if not txid:
        return jsonify(error="Transaction ID is required"), 400
    
    try:
        # Use Pi Network SDK to verify payment
        payment = pi.get_payment(txid)
        if payment and payment.get("status") == "completed":
            amount = float(payment.get("amount", 0.1))
            
            # Calculate revenue split
            developer_share = amount * 0.2
            artist_share = amount * 0.8
            
            # In a real app, store this in a database
            print(f"Verified payment: {txid}, Amount: {amount} PI")
            
            return jsonify(
                status="verified",
                developer=developer_share,
                artist=artist_share
            )
        return jsonify(error="Payment not found or incomplete"), 404
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/health')
def health_check():
    return jsonify(
        status="healthy", 
        version="1.0",
        wallet=app.config["PI_WALLET_ADDRESS"],
        categories=list(get_categories().keys())
    )

@app.route('/.well-known/pi-validation.txt')
def validation_file():
    return send_from_directory('static', 'validation-key.txt')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/images', 'logo.png')

if __name__ == "__main__":
    print("Starting Natsly Coloring App...")
    print(f"Pi Wallet Address: {app.config['PI_WALLET_ADDRESS']}")
    print(f"Sandbox Mode: {app.config['PI_SANDBOX']}")
    
    categories = get_categories()
    print(f"Found {len(categories)} categories:")
    for category, images in categories.items():
        print(f" - {category}: {len(images)} images")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
