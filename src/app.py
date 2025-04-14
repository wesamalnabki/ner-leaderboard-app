import os
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from evaluation_ner import parse_tsv_file, calculate_metrics
from dotenv import find_dotenv, load_dotenv

print(load_dotenv(find_dotenv()))

# --- Set Page Config (must be first Streamlit call) ---
st.set_page_config(page_title="NER Benchmarking Leaderboard", layout="wide")

# --- Load Config for Authentication ---
config_path = os.getenv("USER_CONFIG_PATH", "/mounted/users_config.yaml")
with open(config_path) as file:
    config = yaml.load(file, Loader=SafeLoader)

# --- Initialize Authenticator ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- Login Widget ---
try:
    authenticator.login()
except Exception as e:
    st.error(e)

if st.session_state.get("authentication_status"):
    authenticator.logout("Logout", "sidebar")
    st.sidebar.write(f"Welcome *{st.session_state['name']}*")

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
    def load_testsets(path):
        datasets = {}
        for ds in os.listdir(path):
            if ds.endswith(".tsv"):
                df = parse_tsv_file(os.path.join(path, ds), entities_to_evaluate=[])
                df.drop(columns=[col for col in ['note', 'mark', 'ann_id'] if col in df.columns], inplace=True, errors='ignore')
                df.reset_index(drop=True, inplace=True)
                datasets[ds.replace(".tsv", "")] = df
        return datasets

    def get_submissions(dataset):
        return session.query(Submission).filter_by(dataset_name=dataset).order_by(Submission.submission_date.desc()).all()

    def exe_new_eval(df_gs, pred):
        tags = df_gs.label.unique().tolist()
        metrics = {tag: calculate_metrics(df_gs[df_gs.label == tag], pred[pred.label == tag])[1:6:2] for tag in tags}
        total_metrics = calculate_metrics(df_gs, pred)[1:6:2]
        metrics['Total'] = total_metrics
        return {k: {"Precision": v[0], "Recall": v[1], "F1": v[2]} for k, v in metrics.items()}

    def display_leaderboard(dataset_name, dataset_dict):
        st.subheader("Leaderboard")
        submissions = get_submissions(dataset_name)
        if not submissions:
            st.info("No submissions yet.")
            return

        cols = st.columns([2, 2, 2, 1, 1, 1, 2, 2])
        headers = ["Submission Name", "Model Link", "Person Name", "Precision", "Recall", "F1 Score", "Date", "Actions"]
        for col, header in zip(cols, headers): col.markdown(f"**{header}**")

        for sub in submissions:
            cols = st.columns([2, 2, 2, 1, 1, 1, 2, 2])
            cols[0].markdown(f"**{sub.submission_name}**")
            cols[1].markdown(sub.model_link)
            cols[2].markdown(sub.person_name)
            cols[3].markdown(f"{sub.precision:.2f}")
            cols[4].markdown(f"{sub.recall:.2f}")
            cols[5].markdown(f"{sub.f1:.2f}")
            cols[6].markdown(sub.submission_date.strftime("%Y-%m-%d %H:%M:%S"))

            delete_col, reeval_col, download_col = cols[7].columns([1, 1, 1])

            if delete_col.button("🗑️", key=f"del_{sub.id}"):
                session.delete(sub)
                session.commit()
                st.success(f"Deleted: {sub.submission_name}")
                st.rerun()

            if reeval_col.button("🔁", key=f"reeval_{sub.id}"):
                path = os.path.join(submission_save_path, f"{sub.dataset_name}__{sub.submission_name}.tsv")
                if not os.path.exists(path):
                    st.error("File not found.")
                else:
                    gs = dataset_dict.get(sub.dataset_name)
                    pred = parse_tsv_file(path, [])
                    result = exe_new_eval(gs, pred)
                    st.subheader("Re-evaluation Results")
                    st.json(result)
                    st.success("Re-evaluated.")

            file_path = os.path.join(submission_save_path, f"{sub.dataset_name}__{sub.submission_name}.tsv")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    download_col.download_button("⬇️", f, file_name=os.path.basename(file_path))

    def submit_section(dataset_name, dataset_dict):
        st.subheader("Submit Your Model Prediction")
        with st.form("submission_form"):
            file = st.file_uploader("Upload TSV", type=["tsv"])
            name = st.text_input("Submission Name")
            link = st.text_input("Model Link")
            person = st.text_input("Your Name")
            submit = st.form_submit_button("Submit")

            if submit:
                if not all([file, name, link, person]):
                    st.error("All fields required.")
                    return
                try:
                    gs_df = dataset_dict.get(dataset_name)
                    save_name = f"{dataset_name}__{name}.tsv"
                    save_path = os.path.join(submission_save_path, save_name)
                    with open(save_path, "wb") as f:
                        f.write(file.getbuffer())
                    file.seek(0)
                    pred_df = parse_tsv_file(file, [])
                    tags = gs_df.label.unique().tolist()
                    metrics = {tag: calculate_metrics(gs_df[gs_df.label == tag], pred_df[pred_df.label == tag])[1:6:2] for tag in tags}
                    total = calculate_metrics(gs_df, pred_df)[1:6:2]
                    metrics['Total'] = total

                    session.query(Submission).filter_by(dataset_name=dataset_name, submission_name=name).delete()
                    new_sub = Submission(dataset_name=dataset_name, submission_name=name, model_link=link,
                                         person_name=person, precision=total[0], recall=total[1], f1=total[2])
                    session.add(new_sub)
                    session.commit()
                    st.session_state['last_metrics'] = {k: {"Precision": v[0], "Recall": v[1], "F1": v[2]} for k, v in metrics.items()}
                    st.success("Submitted and evaluated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Submission failed: {e}")

    def main():
        dataset_dict = load_testsets(testsets_root_path)
        if not dataset_dict:
            st.warning("No testsets found.")
            return

        dataset_name = st.selectbox("Choose Dataset", list(dataset_dict.keys()))
        display_leaderboard(dataset_name, dataset_dict)
        submit_section(dataset_name, dataset_dict)

        if 'last_metrics' in st.session_state:
            st.subheader("Last Evaluation")
            st.json(st.session_state.pop('last_metrics'))

    if __name__ == '__main__':
        main()

elif st.session_state.get("authentication_status") is False:
    st.error("Username/password is incorrect")
elif st.session_state.get("authentication_status") is None:
    st.warning("Please enter your username and password")