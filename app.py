import os
import gradio as gr
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pandas as pd
from evaluation_ner import parse_tsv_file, calculate_metrics

testsets_root_path = "./testsets/"

# Load NER testsets (TSV format)
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

engine = create_engine('sqlite:///submissions.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Fetch previous submissions
def get_existing_submissions(dataset_name):
    existing_submissions = session.query(Submission).filter_by(dataset_name=dataset_name).order_by(
        Submission.submission_date.desc()).all()

    submissions_list = [{
        "Submission Name": sub.submission_name,
        "Model Link": sub.model_link,
        "Person Name": sub.person_name,
        "Precision": sub.precision,
        "Recall": sub.recall,
        "F1": sub.f1,
        "Submission Date": sub.submission_date.strftime("%Y-%m-%d %H:%M:%S")
    } for sub in existing_submissions]

    return pd.DataFrame(submissions_list) if submissions_list else pd.DataFrame(columns=[
        "Submission Name", "Model Link", "Person Name", "Precision", "Recall", "F1", "Submission Date"
    ])

# Benchmark and evaluate uploaded NER result
def benchmark_interface(dataset_name, submission_file, submission_name, model_link, person_name):
    if not all([dataset_name, submission_file, submission_name, model_link, person_name]):
        return {"error": "All fields are required."}, pd.DataFrame()

    dataset_dict = load_testsets(testsets_root_path)
    df_gs = dataset_dict.get(dataset_name)
    if df_gs is None:
        return {"error": "Dataset not found."}, pd.DataFrame()

    # Parse submitted prediction TSV
    submission_df = parse_tsv_file(submission_file.name, [])

    # Calculate metrics
    _, P, _, R, _, F1 = calculate_metrics(gs=df_gs, pred=submission_df)
    metrics = {'Precision': P, 'Recall': R, 'F1': F1}

    if F1 is not None:
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

    updated_submissions = get_existing_submissions(dataset_name)
    return metrics, updated_submissions

# Gradio interface
def create_gradio_app():
    dataset_dict = load_testsets(testsets_root_path)
    dataset_names = list(dataset_dict.keys())

    with gr.Blocks() as demo:
        gr.Markdown("## Benchmarking Leaderboard for NER")
        dataset_radio = gr.Radio(choices=dataset_names, label="Select Dataset")

        submission_file = gr.File(label="Upload Submission TSV")
        submission_name = gr.Textbox(label="Submission Name")
        model_link = gr.Textbox(label="Model Link on HuggingFace")
        person_name = gr.Textbox(label="Person Name")
        submit_button = gr.Button("Submit")

        metrics_output = gr.JSON(label="Evaluation Metrics")
        existing_submissions_output = gr.Dataframe(label="Existing Submissions")

        # Auto update table when dataset is selected
        dataset_radio.change(
            fn=get_existing_submissions,
            inputs=[dataset_radio],
            outputs=[existing_submissions_output]
        )

        # Submit and evaluate a new prediction
        submit_button.click(
            fn=benchmark_interface,
            inputs=[dataset_radio, submission_file, submission_name, model_link, person_name],
            outputs=[metrics_output, existing_submissions_output]
        )

    return demo

def main():
    app = create_gradio_app()
    app.launch()

if __name__ == "__main__":
    main()