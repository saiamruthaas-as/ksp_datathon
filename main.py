import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))


LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
}

class RAGSystem:
    def __init__(self, data_dir: str, top_k: int = 4):
        self.data_dir = Path(data_dir)
        self.top_k = top_k
        self.documents: List[Dict[str, str]] = []
        self.embeddings: List[List[float]] = []
        self.vocabulary: List[str] = []

    def load_data(self) -> None:
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory does not exist: {self.data_dir}")

        self.documents = []
        csv_files = sorted(self.data_dir.glob("*.csv"))
        text_files = sorted(self.data_dir.rglob("*.txt"))

        for csv_path in csv_files:
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    text = " | ".join(f"{key}: {value}" for key, value in row.items() if value not in (None, ""))
                    self.documents.append({"source": str(csv_path.name), "text": text})

        for text_path in text_files:
            content = text_path.read_text(encoding="utf-8")
            for chunk in self._chunk_text(content):
                self.documents.append({"source": str(text_path.name), "text": chunk})

        if not self.documents:
            raise ValueError(f"No CSV or TXT documents found in {self.data_dir}")

        self.vocabulary = self._build_vocabulary(self.documents)

    def _chunk_text(self, text: str, chunk_size: int = 450, overlap: int = 70) -> List[str]:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            if chunk:
                chunks.append(chunk)
            if end == len(words):
                break
            start = max(0, end - overlap)
        return chunks

    def _build_vocabulary(self, docs: List[Dict[str, str]]) -> List[str]:
        tokens = set()
        for doc in docs:
            for token in self._tokenize(doc["text"]):
                tokens.add(token)
        return sorted(tokens)

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def build_index(self) -> None:
        self.load_data()
        self.embeddings = [self._embed_text(doc["text"]) for doc in self.documents]

    def _embed_text(self, text: str) -> List[float]:
        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            try:
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=text,
                    task_type="retrieval_document"
                )
                return result['embedding']
            except Exception as e:
                print(f"Gemini embedding failed: {e}")
                pass
        return self._keyword_embedding(text)

    def _keyword_embedding(self, text: str) -> List[float]:
        counts = {token: 0 for token in self.vocabulary}
        for token in self._tokenize(text):
            if token in counts:
                counts[token] += 1
        return [counts[token] for token in self.vocabulary]

    def retrieve(self, query: str) -> List[Dict[str, object]]:
        query_embedding = self._embed_text(query)
        scored = []
        for idx, doc_embedding in enumerate(self.embeddings):
            score = self._cosine_similarity(query_embedding, doc_embedding)
            scored.append((score, idx))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, idx in scored[: self.top_k]:
            results.append({"score": round(score, 4), "document": self.documents[idx]})
        return results

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _translate_text(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        if source_lang == target_lang or not text:
            return text

        source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
        target_name = LANGUAGE_NAMES.get(target_lang, target_lang)

        prompt = (
            f"Translate the following text from {source_name} to {target_name}. "
            "Preserve meaning and keep the tone professional. Output only the translation.\n\n"
            f"Text:\n{text}"
        )

        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            try:
                model = genai.GenerativeModel("gemini-flash-latest")
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception:
                pass

        return text

    def generate_answer(self, query: str, language: str = "en") -> str:
        source_lang = language if language in LANGUAGE_NAMES else "en"
        target_lang = source_lang
        english_query = query

        if source_lang != "en":
            english_query = self._translate_text(query, "en", source_lang=source_lang)

        hits = self.retrieve(english_query)
        if not hits:
            fallback = "The available documents do not contain relevant information for this query. Please consult official crime policy sources or provide additional data."
            return self._translate_text(fallback, target_lang, source_lang="en") if target_lang != "en" else fallback

        context = "\n\n".join(f"[{i + 1}] Source: {item['document']['source']}\n{item['document']['text']}" for i, item in enumerate(hits))
        prompt = f"""You are a crime information assistant. Answer the user's question using only the context below.
If the context does not contain the answer, respond professionally and explain that the information is not available in the current documents.
Do not use phrases such as 'I don't know', 'I am not sure', or 'I don't have enough information'.

Question: {english_query}

Context:
{context}

Provide a concise, factual, and professional response in bullet points, using short sentences and clear structure.
"""

        answer = None
        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            try:
                model = genai.GenerativeModel("gemini-flash-latest")
                response = model.generate_content(prompt)
                if response and response.text:
                    answer = response.text.strip()
            except Exception as e:
                answer = f"Gemini API Error: {str(e)}"
        else:
            answer = "System Error: GEMINI_API_KEY is missing. Please add it to your environment variables in Vercel and REDEPLOY."

        if not answer:
            top_doc = hits[0]["document"]["text"]
            source = hits[0]["document"]["source"]
            answer = f"The available information from {source} indicates: {top_doc}"

        if target_lang != "en":
            answer = self._translate_text(answer, target_lang, source_lang="en")

        return answer

def main() -> None:
    parser = argparse.ArgumentParser(description="Local RAG assistant for CSV and text crime data")
    parser.add_argument("--data-dir", default="data", help="Folder containing CSV and TXT files")
    parser.add_argument("--query", help="Ask one question and exit")
    parser.add_argument("--top-k", type=int, default=4, help="Number of retrieved chunks")
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY not found in environment. Using fallback keyword embeddings.")

    rag = RAGSystem(args.data_dir, top_k=args.top_k)

    try:
        rag.build_index()
    except Exception as exc:
        print(f"Initialization failed: {exc}")
        print("Make sure your data folder exists.")
        sys.exit(1)

    if args.query:
        print(rag.generate_answer(args.query))
        return

    print("RAG assistant ready. Type 'exit' to quit.")
    while True:
        try:
            user_query = input("\nAsk a question: ").strip()
        except KeyboardInterrupt:
            print("\nGoodbye")
            break
        if user_query.lower() in {"exit", "quit"}:
            print("Goodbye")
            break
        try:
            print(rag.generate_answer(user_query))
        except Exception as exc:
            print(f"Error: {exc}")

if __name__ == "__main__":
    main()
