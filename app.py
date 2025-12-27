from flask import Flask, render_template, request
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize


required_nltk = [
    ("punkt", "tokenizers/punkt"),
    ("punkt_tab", "tokenizers/punkt_tab"),
    ("stopwords", "corpora/stopwords")
]
for res, path in required_nltk:
    try:
        nltk.data.find(path)
    except LookupError:
        print(f"Downloading {res}...")
        nltk.download(res, quiet=True)

app = Flask(__name__)

LENGTH_PRESETS = {
    "short":  {"target_words": 100, "min_sentences": 2, "max_sentences": 6},
    "medium": {"target_words": 200, "min_sentences": 4, "max_sentences": 10},
    "long":   {"target_words": 350, "min_sentences": 7, "max_sentences": 16},
}

def clean_text(text):
    """Basic cleanup of raw text."""
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def summarize_text(text: str, preset_name: str = "short") -> str:
    if not text:
        return ""

    text = clean_text(text)
    sentences = sent_tokenize(text)
    
    if len(sentences) <= LENGTH_PRESETS["short"]["max_sentences"]:
        return text

    settings = LENGTH_PRESETS.get(preset_name, LENGTH_PRESETS["short"])
    max_sents = settings["max_sentences"]
    
    try:
        stop_words = set(stopwords.words("english"))
    except:
        stop_words = set()

    words = word_tokenize(text.lower())
    freq_table = {}
    for word in words:
        if word.isalnum() and word not in stop_words:
            freq_table[word] = freq_table.get(word, 0) + 1

    if freq_table:
        max_freq = max(freq_table.values())
        for word in freq_table:
            freq_table[word] = freq_table[word] / max_freq
    else:
        return " ".join(sentences[:max_sents])

    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        sentence_word_count = 0
        score = 0
        for word in word_tokenize(sentence.lower()):
            if word in freq_table:
                score += freq_table[word]
                sentence_word_count += 1
        

        if sentence_word_count > 4:
            sentence_scores[i] = score / sentence_word_count 

    sorted_indices = sorted(sentence_scores, key=sentence_scores.get, reverse=True)
    
    selected_indices = sorted_indices[:max_sents]
    
    selected_indices.sort()
    
    final_summary = " ".join([sentences[i] for i in selected_indices])
    return final_summary

def extract_text_from_html(html: str) -> str:

    soup = BeautifulSoup(html, "html.parser")
    
    for script in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        script.extract()    

    paragraphs = soup.find_all('p')
    if len(paragraphs) > 5:
        text = ' '.join([p.get_text() for p in paragraphs])
    else:
        text = soup.get_text(separator=' ')

    return clean_text(text)

def fetch_text_from_url(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return extract_text_from_html(resp.text)
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Could not fetch URL: {str(e)}")

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

        try:
            input_text = ""
            
            if last_url:
                u = urlparse(last_url)
                if not (u.scheme and u.netloc):
                    raise ValueError("Invalid URL format.")
                input_text = fetch_text_from_url(last_url)
            else:
                input_text = last_text

            if len(input_text.split()) < 100:
                raise ValueError("Not enough text to summarize. Please provide at least 100 words.")

            summary = summarize_text(input_text, preset_name=last_length)
            
        except Exception as e:
            error = str(e)

    return render_template(
        "index.html", 
        summary=summary, 
        error=error, 
        last_url=last_url, 
        last_text=last_text, 
        last_length=last_length
    )

if __name__ == "__main__":
    app.run(debug=True)
