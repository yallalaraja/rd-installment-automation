import pandas as pd

from app.models.account import Account


REQUIRED_COLUMNS = ["account_serial_no", "no_of_installments"]


def load_accounts(path):
    dataframe = pd.read_csv(path, dtype={"account_serial_no": str})
    return accounts_from_dataframe(dataframe)


def accounts_from_dataframe(dataframe):
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in dataframe.columns
    ]
    if missing_columns:
        raise ValueError(
            "Missing required column(s): " + ", ".join(missing_columns)
        )

    cleaned = dataframe[REQUIRED_COLUMNS].copy()
    cleaned["account_serial_no"] = cleaned["account_serial_no"].astype("string").str.strip()
    installment_text = cleaned["no_of_installments"].astype("string").str.strip()
    cleaned["no_of_installments"] = pd.to_numeric(
        installment_text, errors="coerce"
    )

    invalid_installments = installment_text.notna() & installment_text.ne("") & cleaned[
        "no_of_installments"
    ].isna()
    invalid_rows = cleaned[
        cleaned["account_serial_no"].isna()
        | cleaned["account_serial_no"].eq("")
        | invalid_installments
    ]
    if not invalid_rows.empty:
        raise ValueError(
            "CSV contains blank account numbers or non-numeric installment values."
        )

    cleaned["no_of_installments"] = cleaned["no_of_installments"].fillna(0)
    cleaned["no_of_installments"] = cleaned["no_of_installments"].astype(int)
    return [
        Account.from_dict(row)
        for row in cleaned.to_dict(orient="records")
    ]
