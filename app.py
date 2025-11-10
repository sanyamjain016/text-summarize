from flask import Flask, render_template, request
import heapq
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import nltk
from string import punctuation
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

# ensure nltk data
for res, path in [("punkt","tokenizers/punkt"),("punkt_tab","tokenizers/punkt_tab"),("stopwords","corpora/stopwords")]:
    try:
        nltk.data.find(path)
    except LookupError:
        nltk.download(res, quiet=True)

app = Flask(__name__)

LENGTH_PRESETS = {
    "short":  {"target_words": 120, "max_sentences": 3},
    "medium": {"target_words": 220, "max_sentences": 5},
    "long":   {"target_words": 350, "max_sentences": 8},
}

def summarize_text(text: str, target_words: int = 120, max_sentences: int = 3) -> str:
    if not text:
        return ""
    text = re.sub(r"\[[0-9]*\]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n+", " ", text)
    sentences = sent_tokenize(text)
    if not sentences:
        return ""
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    try:
        stop_words = set(stopwords.words("english"))
    except Exception:
        stop_words = set()

    words = word_tokenize(text.lower())
    freq = {}
    for w in words:
        if w.isalpha() and w not in stop_words and w not in punctuation:
            freq[w] = freq.get(w, 0) + 1
    if not freq:
        return " ".join(sentences[:max_sentences])

    scored = []
    for idx, s in enumerate(sentences):
        s_words = word_tokenize(s.lower())
        score = sum(freq.get(w, 0) for w in s_words if w.isalpha())
        wcount = sum(1 for w in s_words if w.isalpha())
        if wcount > 0:
            scored.append((score, idx, s, wcount))
    if not scored:
        return " ".join(sentences[:max_sentences])

    scored.sort(key=lambda x: x[0], reverse=True)
    chosen = []
    acc_words = 0
    for score, idx, s, wcount in scored:
        if len(chosen) >= max_sentences:
            break
        if acc_words >= target_words and chosen:
            break
        chosen.append((idx, s, wcount))
        acc_words += wcount
    chosen.sort(key=lambda x: x[0])
    result = " ".join(s for _, s, _ in chosen)
    result_words = result.split()
    if len(result_words) > target_words * 1.25:
        result = " ".join(result_words[: int(target_words * 1.25)]) + "…"
    return result

def _looks_like_url(value: str) -> bool:
    try:
        u = urlparse(value)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False

def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text(separator=" ")
    return " ".join(text.split())

def fetch_text_from_url(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return extract_text_from_html(resp.text)

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = None
    last_url = ""
    last_text = ""
    last_length = "short"
    if request.method == "POST":
        last_url = (request.form.get("url") or "").strip()
        last_text = (request.form.get("text") or "").strip()
        last_length = (request.form.get("length") or "short").lower()
        preset = LENGTH_PRESETS.get(last_length, LENGTH_PRESETS["short"])
        target_words = preset["target_words"]
        max_sentences = preset["max_sentences"]
        try:
            if last_url:
                if not _looks_like_url(last_url):
                    raise ValueError("Please enter a valid URL starting with http:// or https://")
                page_text = fetch_text_from_url(last_url)
                page_text = page_text[:12000]
                if not page_text or len(page_text.split()) < 20:
                    raise ValueError("Couldn't extract enough text from the URL.")
                summary = summarize_text(page_text, target_words=target_words, max_sentences=max_sentences)
            else:
                if not last_text or len(last_text.split()) < 5:
                    raise ValueError("Please paste at least a few words of text or provide a URL.")
                summary = summarize_text(last_text, target_words=target_words, max_sentences=max_sentences)
        except Exception as e:
            error = str(e)
    return render_template("index.html", summary=summary, error=error, last_url=last_url, last_text=last_text, last_length=last_length)

if __name__ == "__main__":
    app.run(debug=True)
