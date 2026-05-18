import asyncio
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from playwright.sync_api import sync_playwright

from app.automation.navigator import (
    bulk_fetch_accounts,
    fill_installment_number,
    navigate_to_accounts_section,
    open_login_page,
    save_accounts,
    select_all_fetched_accounts,
    select_fetched_account_radio,
)
from app.models.account import Account
from app.services.installment_engine import decide_installment
from app.utils.config import settings


StatusCallback = Callable[[Account, int, int], None]
ProgressCallback = Callable[[int, int, "ProcessingSummary"], None]
WaitForLoginCallback = Callable[[], None]
ManualCompletionCallback = Callable[[], None]


class PlaywrightStartupError(RuntimeError):
    pass


@dataclass
class ProcessingSummary:
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[dict] = field(default_factory=list)

    def to_dict(self):
        return {
            "total_processed": self.total_processed,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "results": self.results,
        }


def wait_for_login_from_terminal():
    input("After login, press ENTER to continue...")


def wait_for_manual_pay_all_from_terminal():
    input("Click Pay All Saved Installments manually, then press ENTER to close browser...")


def configure_playwright_runtime():
    if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def build_playwright_startup_error(exc):
    return PlaywrightStartupError(
        "Playwright could not start its browser driver because Windows denied "
        "subprocess access. Close any old Streamlit/Python automation windows, "
        "then run `python -m playwright install chromium` inside the virtualenv. "
        "If Windows security still blocks it, start PowerShell as Administrator "
        "or allow this project folder in Windows Security."
    )


def build_bulk_account_input(accounts: Iterable[Account]):
    return "\n".join(
        f"{account.account_serial_no},"
        for account in accounts
    )


def resolve_automation_mode(accounts: Iterable[Account], automation_mode: str):
    mode = automation_mode.lower().strip()
    if mode not in {"auto", "bulk", "single"}:
        raise ValueError("automation_mode must be one of: auto, bulk, single")

    account_list = list(accounts)
    if mode == "auto":
        return "single" if any(account.no_of_installments > 1 for account in account_list) else "bulk"
    return mode


def record_result(summary, account, status, message):
    summary.total_processed += 1
    if status == "success":
        summary.successful += 1
    elif status == "failed":
        summary.failed += 1
    elif status == "skipped":
        summary.skipped += 1

    summary.results.append(
        {
            **account.to_dict(),
            "status": status,
            "message": message,
        }
    )


def run_bulk_mode(page, accounts, logger, summary):
    select_all_fetched_accounts(page, logger)
    save_accounts(page, logger)

    for account in accounts:
        record_result(
            summary,
            account,
            "success",
            "Saved through bulk checkbox mode",
        )


def run_single_mode(
    page,
    accounts,
    logger,
    summary,
    status_callback=None,
    progress_callback=None,
):
    total = len(accounts)
    select_all_fetched_accounts(page, logger)
    save_accounts(page, logger)

    for index, account in enumerate(accounts, start=1):
        if status_callback:
            status_callback(account, index, total)

        try:
            if account.no_of_installments <= 1:
                logger.info(
                    "Skipping %s (installments=%s)",
                    account.account_serial_no,
                    account.no_of_installments,
                )
                record_result(
                    summary,
                    account,
                    "skipped",
                    "Skipped because installments <= 1",
                )
            else:
                select_fetched_account_radio(page, index - 1, logger)
                decision = decide_installment(account, logger)
                fill_installment_number(page, account.no_of_installments, logger)
                save_accounts(page, logger)
                record_result(summary, account, decision.status, decision.message)
        except Exception as exc:
            logger.exception("Failed processing %s", account.account_serial_no)
            record_result(summary, account, "failed", str(exc))
        finally:
            if progress_callback:
                progress_callback(index, total, summary)


def run_pipeline(
    accounts: Iterable[Account],
    logger,
    status_callback: Optional[StatusCallback] = None,
    progress_callback: Optional[ProgressCallback] = None,
    wait_for_login_callback: Optional[WaitForLoginCallback] = None,
    manual_completion_callback: Optional[ManualCompletionCallback] = None,
    headless: Optional[bool] = None,
    automation_mode: str = "single",
):
    account_list = list(accounts)
    summary = ProcessingSummary()
    wait_for_login_callback = wait_for_login_callback or wait_for_login_from_terminal
    manual_completion_callback = (
        manual_completion_callback or wait_for_manual_pay_all_from_terminal
    )
    browser_headless = settings.headless if headless is None else headless
    configure_playwright_runtime()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=browser_headless)
            page = browser.new_page()
            page.set_default_timeout(settings.timeout * 1000)

            try:
                open_login_page(page, logger)
                wait_for_login_callback()
                navigate_to_accounts_section(page, logger)
                bulk_account_input = build_bulk_account_input(account_list)
                bulk_fetch_accounts(page, bulk_account_input, logger)
                resolved_mode = resolve_automation_mode(account_list, automation_mode)
                logger.info("Running automation in %s mode", resolved_mode)

                if resolved_mode == "bulk":
                    run_bulk_mode(page, account_list, logger, summary)
                    if progress_callback:
                        progress_callback(len(account_list), len(account_list), summary)
                else:
                    run_single_mode(
                        page,
                        account_list,
                        logger,
                        summary,
                        status_callback=status_callback,
                        progress_callback=progress_callback,
                    )

                logger.info(
                    "Process completed. Please click Pay All Saved Installments manually."
                )
                manual_completion_callback()
            finally:
                browser.close()
    except PermissionError as exc:
        raise build_playwright_startup_error(exc) from exc

    return summary
