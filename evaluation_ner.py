import pandas as pd
import logging
from typing import Tuple
import csv

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Constants
START_SPAN_TAG = "start_span"
END_SPAN_TAG = "end_span"
ENTITY_NAME_TAG = "text"
LABEL_TAG = "label"

# START_SPAN_TAG = "off0"
# END_SPAN_TAG = "off1"
# ENTITY_NAME_TAG = "span"
# LABEL_TAG = "label"


def parse_tsv_file(datapath: str, entities_to_evaluate: list) -> pd.DataFrame:
    """
    Parse a TSV file into a DataFrame and perform basic formatting and deduplication.

    Parameters:
    -----------
    datapath : str
        Path to the TSV file.
    entities_to_evaluate: list
        List of entities to evaluate. If none, take all entities

    Returns:
    --------
    pd.DataFrame
        Formatted and deduplicated DataFrame.
    """
    try:
        # Load the TSV file
        df = pd.read_csv(datapath, sep='\t', header=0, quoting=csv.QUOTE_NONE, keep_default_na=False, dtype=str)

        if entities_to_evaluate:
            df = df.loc[df['label'].isin(entities_to_evaluate), :].copy()

        # Format DataFrame
        df['offset'] = df[START_SPAN_TAG].astype(str) + ' ' + df[END_SPAN_TAG].astype(str)

        # Check for duplicated entries
        if df.duplicated(subset=['filename', 'label', 'offset']).any():
            df = df.drop_duplicates(subset=['filename', 'label', 'offset']).copy()
            logger.warning("Duplicated entries found and removed.")

        return df

    except Exception as e:
        logger.error(f"Error parsing TSV file: {e}")
        raise


def calculate_metrics(gs: pd.DataFrame, pred: pd.DataFrame) -> Tuple[
    pd.Series, float, pd.Series, float, pd.Series, float]:
    """
    Calculate Precision, Recall, and F1 score per clinical case and micro-average.

    Parameters:
    -----------
    gs : pd.DataFrame
        Gold Standard DataFrame.
    pred : pd.DataFrame
        Predictions DataFrame.

    Returns:
    --------
    Tuple[pd.Series, float, pd.Series, float, pd.Series, float]
        Precision per clinical case, Micro-average Precision,
        Recall per clinical case, Micro-average Recall,
        F1 score per clinical case, Micro-average F1 score.
    """
    # Calculate True Positives (TP), Predicted Positives (Pred_Pos), and Gold Standard Positives (GS_Pos)
    TP_per_cc, TP, Pred_Pos_per_cc, Pred_Pos, GS_Pos_per_cc, GS_Pos = calculate_positives(gs, pred)

    # Calculate Precision, Recall, and F1 per clinical case
    P_per_cc = TP_per_cc / Pred_Pos_per_cc
    R_per_cc = TP_per_cc / GS_Pos_per_cc
    F1_per_cc = (2 * P_per_cc * R_per_cc) / (P_per_cc + R_per_cc)

    # Calculate Micro-average Precision, Recall, and F1
    P = TP / Pred_Pos if Pred_Pos > 0 else 0
    R = TP / GS_Pos if GS_Pos > 0 else 0
    F1 = (2 * P * R) / (P + R) if (P + R) > 0 else 0

    return P_per_cc, round(P,4), R_per_cc, round(R,4), F1_per_cc, round(F1,4)


def calculate_positives(gs: pd.DataFrame, pred: pd.DataFrame) -> Tuple[pd.Series, int, pd.Series, int, pd.Series, int]:
    """
    Calculate True Positives, Predicted Positives, and Gold Standard Positives.

    Parameters:
    -----------
    gs : pd.DataFrame
        Gold Standard DataFrame.
    pred : pd.DataFrame
        Predictions DataFrame.

    Returns:
    --------
    Tuple[pd.Series, int, pd.Series, int, pd.Series, int]
        True Positives per clinical case, Total True Positives,
        Predicted Positives per clinical case, Total Predicted Positives,
        Gold Standard Positives per clinical case, Total Gold Standard Positives.
    """
    # Predicted Positives
    Pred_Pos_per_cc = pred.drop_duplicates(subset=['filename', "offset"]).groupby("filename")["offset"].count()
    Pred_Pos = pred.drop_duplicates(subset=['filename', "offset"]).shape[0]

    # Gold Standard Positives
    GS_Pos_per_cc = gs.drop_duplicates(subset=['filename', "offset"]).groupby("filename")["offset"].count()
    GS_Pos = gs.drop_duplicates(subset=['filename', "offset"]).shape[0]

    # True Positives
    df_sel = pd.merge(pred, gs, how="right", on=["filename", "offset", "label"])
    is_valid = ~df_sel.isnull().any(axis=1)
    df_sel['is_valid'] = is_valid
    TP_per_cc = df_sel[df_sel["is_valid"]].groupby("filename")["is_valid"].count()
    TP = df_sel[df_sel["is_valid"]].shape[0]

    # Handle clinical cases not predicted or not in GS
    handle_missing_cases(TP_per_cc, Pred_Pos_per_cc, gs, pred)

    return TP_per_cc, TP, Pred_Pos_per_cc, Pred_Pos, GS_Pos_per_cc, GS_Pos


def handle_missing_cases(TP_per_cc: pd.Series, Pred_Pos_per_cc: pd.Series, gs: pd.DataFrame,
                         pred: pd.DataFrame) -> None:
    """
    Handle clinical cases that are missing in predictions or Gold Standard.

    Parameters:
    -----------
    TP_per_cc : pd.Series
        True Positives per clinical case.
    Pred_Pos_per_cc : pd.Series
        Predicted Positives per clinical case.
    gs : pd.DataFrame
        Gold Standard DataFrame.
    pred : pd.DataFrame
        Predictions DataFrame.
    """
    # Add entries for clinical cases not predicted but present in GS
    cc_not_predicted = (pred.drop_duplicates(subset=["filename"])
                        .merge(gs.drop_duplicates(subset=["filename"]),
                               on='filename',
                               how='right', indicator=True)
                        .query('_merge == "right_only"')
                        .drop(columns=['_merge']))['filename'].to_list()
    for cc in cc_not_predicted:
        TP_per_cc[cc] = 0

    # Remove entries for clinical cases not in GS but present in predictions
    cc_not_GS = (gs.drop_duplicates(subset=["filename"])
                 .merge(pred.drop_duplicates(subset=["filename"]),
                        on='filename',
                        how='right', indicator=True)
                 .query('_merge == "right_only"')
                 .drop(columns=['_merge']))['filename'].to_list()
    Pred_Pos_per_cc = Pred_Pos_per_cc.drop(cc_not_GS)
