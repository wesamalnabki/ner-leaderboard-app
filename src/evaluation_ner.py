import csv
import logging
from typing import Tuple

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Constants
START_SPAN_TAG = "start_span"
END_SPAN_TAG = "end_span"
ENTITY_NAME_TAG = "text"
LABEL_TAG = "label"
FILE_NAME = "filename"


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
            df = df.loc[df[LABEL_TAG].isin(entities_to_evaluate), :].copy()

        # Format DataFrame
        df['offset'] = df[START_SPAN_TAG].astype(str) + ' ' + df[END_SPAN_TAG].astype(str)

        # Check for duplicated entries
        if df.duplicated(subset=[FILE_NAME, LABEL_TAG, 'offset']).any():
            df = df.drop_duplicates(subset=[FILE_NAME, LABEL_TAG, 'offset']).copy()
            logger.warning("Duplicated entries found and removed.")

        return df

    except Exception as e:
        logger.error(f"Error parsing TSV file: {e}")
        raise


def calculate_metrics_strict(gs: pd.DataFrame, pred: pd.DataFrame) -> Tuple[float, float, float]:
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
    Tuple[float,float, float]
    Micro-average Precision,
    Micro-average Recall,
    Micro-average F1 score.
    """

    Pred_Pos = pred.drop_duplicates(subset=[FILE_NAME, "offset"]).shape[0]

    # Gold Standard Positives
    GS_Pos = gs.drop_duplicates(subset=[FILE_NAME, "offset"]).shape[0]

    # True Positives
    df_sel = pd.merge(pred, gs, how="right", on=[FILE_NAME, "offset", LABEL_TAG])
    is_valid = ~df_sel.isnull().any(axis=1)
    df_sel['is_valid'] = is_valid
    TP = df_sel[df_sel["is_valid"]].shape[0]

    # Calculate Micro-average Precision, Recall, and F1
    P = TP / Pred_Pos if Pred_Pos > 0 else 0
    R = TP / GS_Pos if GS_Pos > 0 else 0
    F1 = (2 * P * R) / (P + R) if (P + R) > 0 else 0

    return round(P, 4), round(R, 4), round(F1, 4)
