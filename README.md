# 🧠 NER Benchmarking Leaderboard (Streamlit App)

This is a secure, interactive Streamlit application for benchmarking Named Entity Recognition (NER) models. Users can upload prediction files, view performance metrics, and track submissions on a leaderboard for multiple test datasets. Authentication is handled using `streamlit-authenticator`.

---

## 🚀 Features

- 🔒 **User Login & Registration** (via YAML config)
- 📊 **Leaderboard** for each dataset
- 📂 **Upload TSV** prediction files
- 📈 **Automatic Evaluation** with Precision, Recall, and F1 score
- 🔁 **Re-evaluate** past submissions
- ⬇️ **Download** submitted files
- 🗑️ **Delete** entries
- 🧪 **Dataset selection** for comparison

---

## 📁 Project Structure

```
.
├── app.py                         # Main Streamlit app
├── evaluation_ner.py             # Evaluation logic
├── .env                          # Environment variables
├── testsets/                     # Ground truth datasets (TSV)
├── saved_submissions/           # Uploaded user predictions
├── submissions.db                # SQLite DB storing metadata
├── users_config.yaml             # User credentials config
├── Dockerfile                    # Docker build instructions
└── docker-compose.yml            # Compose setup
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/nlp4bia-bsc/ner-leaderboard.git
cd ner-leaderboard
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

<details>
<summary>Sample <code>requirements.txt</code></summary>

```txt
streamlit
streamlit-authenticator
PyYAML
SQLAlchemy
python-dotenv
pandas
```

</details>

### 3. Prepare `.env` File

Create a `.env` file in the root directory with:

```env
USER_CONFIG_PATH=./users_config.yaml
TESTSETS_PATH=./testsets/
DB_PATH=./submissions.db
SUBMISSION_SAVE_PATH=./saved_submissions/
```

### 4. Prepare Testsets

Place your ground truth `.tsv` files in the `testsets/` folder. Each file should be in a tab-separated format and include a `label` column.

### 5. User Authentication

Edit `users_config.yaml` with your desired users and cookie settings. [Refer to `streamlit-authenticator` docs](https://github.com/mkhorasani/Streamlit-Authenticator) for formatting help.

---

## 📦 Running with Docker Compose

### 1. Build and Start the App

```bash
docker-compose up --build
```

### 2. Access the App

Open your browser and go to: [http://localhost:8501](http://localhost:8501)

Make sure to mount your `.env`, `testsets/`, and `users_config.yaml` into the container if you're customizing outside the image.

---

## ▶️ Running the App (Locally)

```bash
streamlit run app.py
```

---

## 📄 Submitting a Prediction

1. Select a dataset.
2. Upload your `.tsv` file with predictions.
3. Provide a submission name, model link, and your name.
4. View evaluation metrics and see your score on the leaderboard.

---

## 📌 Notes

- TSV files must match the format of the ground truth testsets.
- Submissions with the same name will overwrite previous ones.
- The leaderboard supports actions like delete, re-evaluate, and download.

---

## 🛡️ Authentication Tips

- Passwords are hashed in the `users_config.yaml`.
- Users must log in before viewing or submitting.
- Registration logic can be extended to include user signup.

---

## 📬 Feedback

Found a bug or have a feature request? Open an issue or reach out!

