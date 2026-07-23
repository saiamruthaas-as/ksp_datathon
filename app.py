import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
from main import RAGSystem

app = Flask(__name__)

allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "https://kspdatathon06.vercel.app,https://breeze-ascertain-unwind.ngrok-free.dev"
)
allowed_origin_list = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]

if allowed_origin_list and allowed_origin_list != ["*"]:
    CORS(app, resources={r"/api/*": {"origins": allowed_origin_list}})
else:
    CORS(app, resources={r"/api/*": {"origins": "*"}})

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))

# Initialize RAG system
try:
    rag = RAGSystem(
        data_dir=os.getenv("DATA_DIR", "data"),
        embed_model=os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
        llm_model=os.getenv("OLLAMA_LLM_MODEL", "llama3.2"),
        top_k=int(os.getenv("TOP_K", 4))
    )
    rag.build_index()
    print("RAG system initialized successfully")
except Exception as exc:
    print(f"Failed to initialize RAG system: {exc}")
    print("Make sure Ollama is running and data files exist")
    sys.exit(1)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "RAG system is running"})


@app.route("/api/query", methods=["POST"])
def query():
    try:
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "Missing 'query' field"}), 400

        user_query = data["query"].strip()
        language = data.get("language", "en")

        if not user_query:
            return jsonify({"error": "Query cannot be empty"}), 400

        answer = rag.generate_answer(user_query, language)
        return jsonify({
            "query": user_query,
            "language": language,
            "answer": answer,
            "status": "success"
        })
    except Exception as exc:
        return jsonify({
            "error": str(exc),
            "status": "error"
        }), 500


@app.route("/api/retrieve", methods=["POST"])
def retrieve():
    try:
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "Missing 'query' field"}), 400

        user_query = data["query"].strip()
        if not user_query:
            return jsonify({"error": "Query cannot be empty"}), 400

        results = rag.retrieve(user_query)
        return jsonify({
            "query": user_query,
            "results": results,
            "count": len(results),
            "status": "success"
        })
    except Exception as exc:
        return jsonify({
            "error": str(exc),
            "status": "error"
        }), 500


@app.route("/api/info", methods=["GET"])
def info():
    return jsonify({
        "name": "KSP Crime RAG Assistant",
        "version": "1.0.0",
        "documents_loaded": len(rag.documents),
        "embed_model": rag.embed_model,
        "llm_model": rag.llm_model,
        "top_k": rag.top_k
    })


@app.route("/", methods=["GET"])
def index():
    return send_from_directory("templates", "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


if __name__ == "__main__":
    app.run(debug=False, host=HOST, port=PORT)
