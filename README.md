# 🧠 NER Benchmarking Leaderboard

This project is a web-based leaderboard application built with **Gradio** for evaluating and comparing Named Entity Recognition (NER) model outputs against gold-standard test sets. It allows users to upload model predictions (in TSV format), computes standard metrics (Precision, Recall, F1), and stores the results in a local database with a historical view.

---

## 🚀 Features

- 📁 Upload model prediction TSV files
- 📊 Evaluate predictions against preloaded testsets
- 🧪 Computes Precision, Recall, and F1 Score
- 🏆 View and compare submissions on a per-dataset basis
- 💃 Stores submissions in an SQLite database
- ⚡ Clean, interactive interface using Gradio

---

## 📂 Project Structure

```
🔹 evaluation_ner.py           # Functions for parsing TSV and calculating metrics
🔹 main.py                     # Main app logic and Gradio UI
🔹 testsets/                   # Folder containing ground truth TSV testsets
🔹 submissions.db              # SQLite database for tracking submissions
🔹 README.md                   # This file
```

---

## 📊 Example Submission TSV Format

Each submission must be in TSV format, matching the structure expected by `evaluation_ner.parse_tsv_file()`. Typically, these include columns like:

- `token`
- `label_gold`
- `label_pred`
- (optional columns like `note`, `mark`, `ann_id` are automatically dropped)

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ner-benchmark-leaderboard.git
cd ner-benchmark-leaderboard
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> Required packages include: `gradio`, `sqlalchemy`, `pandas`, etc.

### 3. Add Testsets

Place your gold-standard `.tsv` files in the `testsets/` directory. Each file will be automatically detected and used as a benchmark dataset.

### 4. Run the App

```bash
python main.py
```

The app will launch in your browser via Gradio.

---

## 📈 Database

All submissions are stored in a local SQLite database named `submissions.db`. This enables persistent tracking and ranking of different model runs.

---

## 🔧 Evaluation Logic

Evaluation is handled in two steps:
1. Ground truth and predictions are parsed using `parse_tsv_file()` from `evaluation_ner.py`
2. Metrics (Precision, Recall, F1) are computed with `calculate_metrics()`

---

## 🙋 Contributing

Feel free to fork the repo, suggest improvements, or submit pull requests. All contributions are welcome!

---

## 📁 License

MIT License. See `LICENSE` file for details.

---

## 🙏 Acknowledgments

Thanks to the Hugging Face community and open-source contributors who inspired the benchmarking and evaluation tools in this project.

