import os
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import pandas as pd
from evaluation_ner import parse_tsv_file, calculate_metrics

# --- Config ---
testsets_root_path = os.getenv("TESTSETS_PATH", "./testsets/")
db_path = f"sqlite:///{os.getenv('DB_PATH', 'submissions.db')}"
submission_save_path = os.getenv("SUBMISSION_SAVE_PATH", "./saved_submissions/")
os.makedirs(submission_save_path, exist_ok=True)

# --- Database Setup ---
Base = declarative_base()

class Submission(Base):
    __tablename__ = 'submissions'
    id = Column(Integer, primary_key=True)
    dataset_name = Column(String)
    submission_name = Column(String)
    model_link = Column(String)
    person_name = Column(String)
    precision = Column(Float)
    recall = Column(Float)
    f1 = Column(Float)
    submission_date = Column(DateTime, default=datetime.utcnow)

engine = create_engine(db_path)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# --- Load NER Testsets ---
def load_testsets(testsets_root_path: str) -> dict:
    datasets_dict = {}
    for ds in os.listdir(testsets_root_path):
        if ds.endswith(".tsv"):
            tsv_path = os.path.join(testsets_root_path, ds)
            df = parse_tsv_file(tsv_path, entities_to_evaluate=[])
            df = df.drop(columns=[col for col in ['note', 'mark', 'ann_id'] if col in df.columns], errors='ignore')
            df.reset_index(inplace=True, drop=True)
            datasets_dict[ds.replace(".tsv", "")] = df
    return datasets_dict

# --- Retrieve Submissions ---
def get_existing_submissions_with_ids(dataset_name):
    return session.query(Submission).filter_by(dataset_name=dataset_name).order_by(
        Submission.submission_date.desc()).all()

def exe_new_eval(df_gs: pd.DataFrame, pred: pd.DataFrame):
    print("🧪 Re-evaluating submission...")
    metrics = {}
    tags = df_gs.label.unique().tolist()
    for tag in tags:
        _, P, _, R, _, F1 = calculate_metrics(gs=df_gs[df_gs.label == tag],
                                              pred=pred[pred.label == tag])
        metrics[tag] = {
            "Precision": P,
            "Recall": R,
            "F1": F1
        }
    _, P, _, R, _, F1 = calculate_metrics(gs=df_gs, pred=pred)
    metrics['Total'] = {
        "Precision": P,
        "Recall": R,
        "F1": F1
    }
    return metrics


# --- Streamlit App ---
def main():
    st.set_page_config(page_title="NER Benchmarking Leaderboard", layout="wide")
    st.title("📊 Benchmarking Leaderboard for NER")

    dataset_dict = load_testsets(testsets_root_path)
    dataset_names = list(dataset_dict.keys())

    if not dataset_names:
        st.warning("No datasets found in the testsets directory.")
        return

    dataset_name = st.selectbox("Select Dataset", dataset_names)

    st.subheader("Leaderboard")

    submissions = get_existing_submissions_with_ids(dataset_name)

    if not submissions:
        st.info("No submissions yet.")
    else:
        # Table headers
        cols = st.columns([2, 2, 2, 1, 1, 1, 2, 1])
        cols[0].markdown("**Submission Name**")
        cols[1].markdown("**Model Link**")
        cols[2].markdown("**Person Name**")
        cols[3].markdown("**Precision**")
        cols[4].markdown("**Recall**")
        cols[5].markdown("**F1 Score**")
        cols[6].markdown("**Submission Date**")
        cols[7].markdown("**Actions**")

        for sub in submissions:
            cols = st.columns([2, 2, 2, 1, 1, 1, 2, 1])
            cols[0].markdown(f"**{sub.submission_name}**")
            cols[1].markdown(sub.model_link)
            cols[2].markdown(sub.person_name)
            cols[3].markdown(f"{sub.precision:.2f}")
            cols[4].markdown(f"{sub.recall:.2f}")
            cols[5].markdown(f"{sub.f1:.2f}")
            cols[6].markdown(sub.submission_date.strftime("%Y-%m-%d %H:%M:%S"))

            # Split the Actions column into two columns
            action_col1, action_col2 = cols[7].columns([1, 1])

            if action_col1.button("🗑️", key=f"delete_{sub.id}"):
                session.delete(sub)
                session.commit()
                st.success(f"Deleted submission: {sub.submission_name}")
                st.rerun()

            if action_col2.button("🔁", key=f"reeval_{sub.id}"):
                try:
                    file_path = os.path.join(submission_save_path, f"{sub.dataset_name}__{sub.submission_name}.tsv")
                    if not os.path.exists(file_path):
                        st.error("Saved submission file not found.")
                    else:
                        gs = dataset_dict.get(sub.dataset_name)
                        pred = parse_tsv_file(file_path, [])
                        eval_result = exe_new_eval(gs, pred)

                        # Show re-evaluation results
                        st.subheader("Re-evaluation Results")
                        st.json(eval_result)

                        st.success("Re-evaluation triggered.")
                except Exception as e:
                    st.error(f"Re-evaluation failed: {e}")

    st.subheader("Submit Your Model Prediction")

    with st.form("submission_form"):
        submission_file = st.file_uploader("Upload Submission TSV", type=["tsv"])
        submission_name = st.text_input("Submission Name")
        model_link = st.text_input("Model Link on HuggingFace")
        person_name = st.text_input("Person Name")
        submitted = st.form_submit_button("Submit")

        if submitted:
            if not all([submission_file, submission_name, model_link, person_name]):
                st.error("All fields are required.")
            else:
                try:
                    df_gs = dataset_dict.get(dataset_name)
                    if df_gs is None:
                        st.error("Dataset not found.")
                        return

                    # Save uploaded file
                    save_filename = f"{dataset_name}__{submission_name}.tsv"
                    save_path = os.path.join(submission_save_path, save_filename)
                    with open(save_path, "wb") as f:
                        f.write(submission_file.getbuffer())

                    submission_file.seek(0)
                    submission_df = parse_tsv_file(submission_file, [])

                    tags = df_gs.label.unique().tolist()
                    metrics = {}
                    for tag in tags:
                        _, P, _, R, _, F1 = calculate_metrics(gs=df_gs[df_gs.label == tag],
                                                              pred=submission_df[submission_df.label == tag])
                        metrics[tag] = {
                            "Precision": P,
                            "Recall": R,
                            "F1": F1
                        }
                    _, P, _, R, _, F1 = calculate_metrics(gs=df_gs, pred=submission_df)
                    metrics['Total']  = {
                            "Precision": P,
                            "Recall": R,
                            "F1": F1
                        }

                    # Remove previous submission with same name
                    existing = session.query(Submission).filter_by(
                        dataset_name=dataset_name,
                        submission_name=submission_name
                    ).first()
                    if existing:
                        session.delete(existing)
                        session.commit()

                    new_submission = Submission(
                        dataset_name=dataset_name,
                        submission_name=submission_name,
                        model_link=model_link,
                        person_name=person_name,
                        precision=P,
                        recall=R,
                        f1=F1
                    )
                    session.add(new_submission)
                    session.commit()

                    st.session_state["last_metrics"] = metrics
                    st.success("Submission evaluated and saved!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error processing submission: {e}")

    if "last_metrics" in st.session_state:
        st.subheader("Last Evaluation Results")
        st.json(st.session_state["last_metrics"])
        del st.session_state["last_metrics"]

if __name__ == "__main__":
    main()
