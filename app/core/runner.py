import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.account import Account
from app.services.excel_loader import accounts_from_dataframe, load_accounts
from app.core.engine import run_pipeline
from app.utils.config import settings
from app.utils.logger import get_logger


def _normalize_accounts(accounts):
    return [
        account if isinstance(account, Account) else Account.from_dict(account)
        for account in accounts
    ]


def start(
    csv_path=None,
    accounts=None,
    dataframe=None,
    logger=None,
    status_callback=None,
    progress_callback=None,
    wait_for_login_callback=None,
    manual_completion_callback=None,
    headless=None,
    automation_mode="single",
):
    logger = logger or get_logger()
    csv_path = csv_path or settings.default_accounts_file

    if dataframe is not None:
        account_list = accounts_from_dataframe(dataframe)
    elif accounts is not None:
        account_list = _normalize_accounts(accounts)
    else:
        account_list = load_accounts(csv_path)

    return run_pipeline(
        account_list,
        logger=logger,
        status_callback=status_callback,
        progress_callback=progress_callback,
        wait_for_login_callback=wait_for_login_callback,
        manual_completion_callback=manual_completion_callback,
        headless=headless,
        automation_mode=automation_mode,
    )


if __name__ == "__main__":
    start()
