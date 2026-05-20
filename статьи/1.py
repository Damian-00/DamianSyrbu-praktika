import re
import json
from pathlib import Path
from pypdf import PdfReader

ROOTS = ["компакт", "связн", "замкнут", "открыт"]

def natural_sort_key(path):
    numbers = re.findall(r'\d+', path.name)
    return int(numbers[0]) if numbers else 0

def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def split_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text)

def remove_unwanted_sections(text):
    text_lower = text.lower()
    stop_words = [
        "аннотация",
        "abstract",
        "ключевые слова",
        "keywords",
        "список литературы",
        "references",
        "для цитирования",
        "for citation"
    ]
    cut_positions = []
    for stop_word in stop_words:
        pos = text_lower.find(stop_word)
        if pos != -1:
            cut_positions.append(pos)
    if cut_positions:
        text = text[:min(cut_positions)]
    return text

def create_empty_stats():
    return {
        "компакт": 0,
        "связн": 0,
        "замкнут": 0,
        "открыт": 0
    }

def extract_text_without_headers(page):
    parts = []
    def visitor_body(text, cm, tm, font_dict, font_size):
        if not text.strip():
            return
        font_name = ""
        if font_dict:
            font_name = font_dict.get("/BaseFont", "")
        text_clean = text.strip()
        is_bold = "Bold" in str(font_name)
        is_upper = (
            len(text_clean) > 3 and
            text_clean.upper() == text_clean and
            re.search(r"[А-ЯЁ]", text_clean)
        )
        is_short_header = len(text_clean.split()) <= 8
        if (is_bold or is_upper) and is_short_header:
            return
        parts.append(text)
    page.extract_text(visitor_text=visitor_body)
    return " ".join(parts)

def process_folder(folder_name="статьи", output_file="result.json"):
    folder = Path(folder_name)
    pdf_files = sorted(
        [p for p in folder.iterdir() if p.suffix.lower() == ".pdf"],
        key=natural_sort_key
    )
    results = []
    total_statistics = create_empty_stats()
    files_statistics = {}

    print("Найдено PDF:", len(pdf_files))

    for pdf_file in pdf_files:
        print(f"Обработка: {pdf_file.name}")
        file_stats = create_empty_stats()
        try:
            reader = PdfReader(str(pdf_file))
            for page_num, page in enumerate(reader.pages, start=1):
                text = extract_text_without_headers(page)
                text = remove_unwanted_sections(text)
                text = clean_text(text)
                sentences = split_sentences(text)

                
                for i, sentence in enumerate(sentences):
                    sentence_lower = sentence.lower()
                    words = re.findall(r"[а-яё-]+", sentence_lower)
                    for word in words:
                        for root in ROOTS:
                            if root in word:
                                
                                start_idx = max(0, i - 1)
                                end_idx = min(len(sentences), i + 2)  # i+2 не включается
                                context_sentences = sentences[start_idx:end_idx]
                                context = " ".join(context_sentences).strip()

                                total_statistics[root] += 1
                                file_stats[root] += 1
                                results.append({
                                    "file": pdf_file.name,
                                    "page": page_num,
                                    "root": root,
                                    "word": word,
                                    "sentence": context  
                                })
                                break 
        except Exception as e:
            print(f"Ошибка в {pdf_file.name}: {e}")

        files_statistics[pdf_file.name] = file_stats

    final_data = {
        "total_statistics": total_statistics,
        "files_statistics": files_statistics,
        "results": results
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print("Готово.")
    print("Всего найдено:", len(results))

if __name__ == "__main__":
    process_folder("статьи")