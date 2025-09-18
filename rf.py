from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import joblib
import datetime
import os
from typing import Optional
from bson import ObjectId

app = Flask(__name__)
CORS(app)

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = "municipal_complaints"
COLLECTION_NAME = "complaints"
MODEL_VERSION = "1.2.0"

# Connect to MongoDB
try:
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    complaints_collection = db[COLLECTION_NAME]
    print("✅ MongoDB connected successfully!")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    db = None

# ML component paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "random_forest_model_retrained.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "tfidf_vectorizer_retrained.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "label_encoder_retrained.pkl")

# Load ML components
try:
    model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
    tfidf_vectorizer = joblib.load(VECTORIZER_PATH) if os.path.exists(VECTORIZER_PATH) else None
    label_encoder = joblib.load(ENCODER_PATH) if os.path.exists(ENCODER_PATH) else None

    if all([model, tfidf_vectorizer, label_encoder]):
        print(f"✅ ML components loaded successfully! (v{MODEL_VERSION})")
    else:
        print("⚠️ Warning: Some ML components are missing!")
except Exception as e:
    print(f"❌ Error loading ML components: {e}")
    model, tfidf_vectorizer, label_encoder = None, None, None

CATEGORIES = [
    "Water Issues", "Road Issues", "Garbage Issues",
    "Electricity", "Drainage Issues", "Other"
]

CATEGORY_KEYWORDS = {
    "Water Issues": ["water", "drinking", "supply", "leak", "pipe", "tap", "smell", "taste", "pressure"],
    "Road Issues": ["road", "pothole", "asphalt", "street", "highway", "repair", "damage", "construction"],
    "Garbage Issues": ["garbage", "trash", "waste", "collection", "dump", "bin", "clean", "disposal"],
    "Electricity": ["electricity", "power", "outage", "blackout", "wire", "transformer", "voltage", "flickering"],
    "Drainage Issues": ["drainage", "sewer", "flood", "waterlogging", "blockage", "clog", "overflow"],
    "Other": ["noise", "loudspeaker", "park", "tree", "animal", "stray", "public", "nuisance"]
}

# ✅ Safer sanitization (keeps most characters but avoids surrogate errors)
def sanitize_text(text):
    if not isinstance(text, str):
        return ""
    try:
        return text.encode("utf-8", "replace").decode("utf-8")
    except Exception:
        return text.encode("ascii", "ignore").decode("ascii")

def manual_category_detection(complaint_text: str) -> Optional[str]:
    complaint_text = complaint_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in complaint_text for keyword in keywords):
            print(f"🔧 Manual match: {category}")
            return category
    return None

def validate_prediction(predicted_category: str, complaint_text: str) -> str:
    return predicted_category if predicted_category in CATEGORIES else "Other"

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "active",
        "model_version": MODEL_VERSION,
        "endpoints": ["/submit_complaint", "/get_categories", "/get_complaints", "/vote"],
        "categories": CATEGORIES
    })

@app.route("/submit_complaint", methods=["POST"])
def submit_complaint():
    try:
        data = request.get_json(force=True, silent=True) or {}
        raw_complaint = str(data.get("complaint", "")).strip()

        # ✅ Clean input
        complaint_text = sanitize_text(raw_complaint).lower()

        if len(complaint_text) < 10:
            return jsonify({"error": "Complaint must be at least 10 characters"}), 400

        manual_category = manual_category_detection(complaint_text)

        if manual_category:
            predicted_category = manual_category
        elif model and tfidf_vectorizer and label_encoder:
            tfidf = tfidf_vectorizer.transform([complaint_text])
            category_index = model.predict(tfidf)[0]
            predicted_category = label_encoder.inverse_transform([category_index])[0]
            predicted_category = validate_prediction(predicted_category, complaint_text)
        else:
            predicted_category = manual_category_detection(complaint_text) or "Other"

        complaint_entry = {
            "complaint": complaint_text,
            "category": predicted_category,
            "timestamp": datetime.datetime.utcnow(),
            "votes": 0,
            "prediction_source": "manual" if manual_category else "model",
            "model_version": MODEL_VERSION
        }

        complaints_collection.insert_one(complaint_entry)

        return jsonify({
            "message": "Complaint submitted successfully!",
            "category": predicted_category,
            "auto_corrected": bool(manual_category)
        }), 200
    except Exception as e:
        print(f"❌ Error in submit_complaint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_categories", methods=["GET"])
def get_categories():
    return jsonify(CATEGORIES)

@app.route("/get_complaints", methods=["GET"])
def get_complaints():
    try:
        category = request.args.get('category', 'All').strip()
        page = int(request.args.get('page', 1))
        per_page = 20

        query = {} if category == "All" else {"category": {"$regex": f"^{category}$", "$options": "i"}}
        complaints = list(complaints_collection.find(query).sort("timestamp", -1).skip((page - 1) * per_page).limit(per_page))
        total = complaints_collection.count_documents(query)

        return jsonify({
            "complaints": [
                {
                    "_id": str(c["_id"]),
                    "complaint": c["complaint"],
                    "category": c["category"],
                    "votes": c.get("votes", 0),
                    "timestamp": c["timestamp"].strftime('%Y-%m-%d %H:%M:%S'),
                    "prediction_source": c.get("prediction_source", "unknown")
                } for c in complaints
            ],
            "total": total,
            "page": page,
            "per_page": per_page
        })
    except Exception as e:
        print(f"❌ Error in get_complaints: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/vote", methods=["POST"])
def vote():
    try:
        data = request.json
        complaint_id = data.get("id")

        if not complaint_id:
            return jsonify({"success": False, "error": "Missing complaint ID"}), 400

        result = complaints_collection.update_one(
            {"_id": ObjectId(complaint_id)},
            {"$inc": {"votes": 1}}
        )

        if result.modified_count == 1:
            return jsonify({"success": True, "message": "Vote counted"})
        else:
            return jsonify({"success": False, "error": "Complaint not found"}), 404

    except Exception as e:
        print(f"❌ Error in vote: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
