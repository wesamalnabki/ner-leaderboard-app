import hashlib
import os
from datetime import datetime

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from sqlalchemy import and_, create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from yaml.loader import SafeLoader

from evaluation_ner import parse_tsv_file, calculate_metrics_strict, calculate_metrics_relaxed


def get_submission_hash(dataset_name, submission_name, model_link):
    """Generate a consistent hash based on dataset name, submission name, and model link."""
    to_hash = f"{dataset_name}:{submission_name}:{model_link}"
    return hashlib.sha256(to_hash.encode()).hexdigest()


# --- Set Page Config (must be first Streamlit call) ---
st.set_page_config(page_title="NER Benchmarking Leaderboard", layout="wide")

# --- Load Config for Authentication ---
config_path = os.getenv("USER_CONFIG_PATH", "DATA/users_config.yaml")
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
    testsets_root_path = os.getenv("TESTSETS_PATH", "DATA/testsets/")
    db_path = f"sqlite:///{os.getenv('DB_PATH', 'DATA/submissions.db')}"
    submission_save_path = os.getenv("SUBMISSION_SAVE_PATH", "DATA/saved_submissions/")
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
                df.drop(columns=[col for col in ['note', 'mark', 'ann_id'] if col in df.columns], inplace=True,
                        errors='ignore')
                df.reset_index(drop=True, inplace=True)
                datasets[ds.replace(".tsv", "")] = df
        return datasets


    def get_submissions(dataset):
        return session.query(Submission).filter_by(dataset_name=dataset).order_by(
            Submission.submission_date.desc()).all()


    def exe_new_eval(df_gs, df_pred, metric_type="micro_strict"):

        if "strict" in metric_type:
            _result_by_cat_strict, _micro_strict, _macro_strict = calculate_metrics_strict(df_gs, df_pred)
            if "macro" in metric_type:
                return {**_result_by_cat_strict, 'Total': _macro_strict}
            if "micro" in metric_type:
                return {**_result_by_cat_strict, 'Total': _micro_strict}

        if "relaxed" in metric_type:
            _result_by_cat_relaxed, _micro_relaxed, _macro_relaxed = calculate_metrics_relaxed(df_gs, df_pred)
            if "macro" in metric_type:
                return {**_result_by_cat_relaxed, 'Total': _macro_relaxed}
            if "micro" in metric_type:
                return {**_result_by_cat_relaxed, 'Total': _micro_relaxed}


    def display_leaderboard(dataset_name, dataset_dict):
        st.subheader("Leaderboard")
        st.text("**👉👉👀The default metric is: Micro strict👀**")
        submissions = get_submissions(dataset_name)

        if not submissions:
            st.info("No submissions yet.")
            return

        cols = st.columns([2, 2, 2, 1, 1, 1, 2, 2])
        headers = ["Submission Name/ HF Revision", "Model Link", "Person Name", "Precision", "Recall", "F1 Score",
                   "Date", "Actions"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")

        for sub in submissions:
            cols = st.columns([2, 2, 2, 1, 1, 1, 2, 2])

            # Display submission info
            cols[0].markdown(f"**{sub.submission_name}**")
            cols[1].markdown(sub.model_link)
            cols[2].markdown(sub.person_name)
            cols[3].markdown(f"{sub.precision:.2f}")
            cols[4].markdown(f"{sub.recall:.2f}")
            cols[5].markdown(f"{sub.f1:.2f}")
            cols[6].markdown(sub.submission_date.strftime("%Y-%m-%d %H:%M:%S"))

            # New hash-based filename
            file_hash = get_submission_hash(sub.dataset_name, sub.submission_name, sub.model_link)
            file_path = os.path.join(submission_save_path, f"{file_hash}.tsv")

            # Action buttons
            delete_col, reeval_col, download_col = cols[7].columns([1, 1, 1])

            # Delete
            if delete_col.button("🗑️", key=f"delete_{sub.id}"):
                session.delete(sub)
                session.commit()
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        st.warning(f"Could not delete TSV file: {e}")
                st.success(f"Deleted: {sub.submission_name}")
                st.rerun()

            # Re-evaluate
            # if reeval_col.button("🔁", key=f"reeval_{sub.id}"):
            #     if not os.path.exists(file_path):
            #         st.error("Submission file not found.")
            #     else:
            #         gold = dataset_dict.get(sub.dataset_name)
            #         pred = parse_tsv_file(file_path, [])
            #         result = exe_new_eval(gold, pred, metric_type="micro_strict")
            #         st.subheader("Re-evaluation Results")
            #         st.json(result)
            #         st.success("Re-evaluated.")

            # Track re-evaluation state in session
            if reeval_col.button("🔁", key=f"reeval_{sub.id}"):
                st.session_state['reeval_id'] = sub.id
                st.session_state['reeval_metric'] = 'micro_strict'  # default metric

            # If this submission is selected for re-evaluation
            if st.session_state.get("reeval_id") == sub.id:
                if not os.path.exists(file_path):
                    st.error("Submission file not found.")
                else:
                    gold = dataset_dict.get(sub.dataset_name)
                    pred = parse_tsv_file(file_path, [])

                    # Show dropdown and trigger re-eval on change
                    selected_metric = st.selectbox(
                        "Select Evaluation Metric",
                        ["micro_strict", "macro_strict", "micro_relaxed", "macro_relaxed"],
                        index=["micro_strict", "macro_strict", "micro_relaxed", "macro_relaxed"].index(
                            st.session_state.get('reeval_metric', 'micro_strict')),
                        key=f"metric_select_{sub.id}",
                        on_change=lambda: st.session_state.update(
                            {'reeval_metric': st.session_state[f"metric_select_{sub.id}"]})
                    )

                    result = exe_new_eval(gold, pred, metric_type=selected_metric)
                    st.subheader("Re-evaluation Results")
                    st.json(result)

            # Download
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    download_col.download_button("⬇️", f, file_name=os.path.basename(file_path))


    def submit_section(dataset_name, dataset_dict):
        st.subheader("Submit Your Model Prediction")
        with st.form("submission_form"):
            file = st.file_uploader("Upload TSV", type=["tsv"])
            name = st.text_input("Submission Name/ HF Revision")
            link = st.text_input("Model Link")
            person = st.text_input("Your Name")
            submit = st.form_submit_button("Submit")

            if submit:
                if not all([file, name, link, person]):
                    st.error("All fields required.")
                    return
                try:
                    gs_df = dataset_dict.get(dataset_name)
                    file_hash = get_submission_hash(dataset_name, name, link)
                    save_path = os.path.join(submission_save_path, f"{file_hash}.tsv")
                    with open(save_path, "wb") as f:
                        f.write(file.getbuffer())
                    file.seek(0)
                    pred_df = parse_tsv_file(file, [])
                    total = exe_new_eval(gs_df, pred_df, metric_type="micro_strict")

                    # Check for existing submission name or model link
                    existing = session.query(Submission).filter(
                        and_(
                            Submission.dataset_name == dataset_name,
                            Submission.submission_name == name,
                            Submission.model_link == link
                        )
                    ).first()

                    if existing:
                        st.error(
                            "A submission with this name or model link already exists. Please use a different name or link.")
                        return

                    # Proceed to save the new submission
                    new_sub = Submission(
                        dataset_name=dataset_name,
                        submission_name=name,
                        model_link=link,
                        person_name=person,
                        precision=total['Total']["Precision"],
                        recall=total['Total']["Recall"],
                        f1=total["Total"]["F1"]
                    )
                    session.add(new_sub)
                    session.commit()
                    st.session_state['last_metrics'] = total
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
