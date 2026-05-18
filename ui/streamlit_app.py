import io
import logging
import time
from html import escape

import pandas as pd
import streamlit as st

from app.core.engine import PlaywrightStartupError
from app.core.runner import start
from app.services.excel_loader import REQUIRED_COLUMNS, accounts_from_dataframe
from app.utils.config import settings


class StreamlitLogHandler(logging.Handler):
    def __init__(self, render_callback):
        super().__init__()
        self.render_callback = render_callback

    def emit(self, record):
        st.session_state.logs.append(self.format(record))
        self.render_callback()


def initialize_state():
    defaults = {
        "logs": [],
        "results": None,
        "summary": None,
        "is_running": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def read_uploaded_csv(uploaded_file):
    dataframe = pd.read_csv(uploaded_file, dtype={"account_serial_no": str})
    accounts_from_dataframe(dataframe)
    return dataframe[REQUIRED_COLUMNS].copy()


def build_logger(render_logs):
    logger = logging.getLogger("RD-AUTO-STREAMLIT")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    handler = StreamlitLogHandler(render_logs)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    return logger


def results_to_csv(results):
    buffer = io.StringIO()
    pd.DataFrame(results).to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def main():
    st.set_page_config(page_title="RD Installment Automation", layout="wide")
    initialize_state()

    st.title("RD Installment Automation")
    st.caption("Upload a CSV and run the RD installment pipeline.")

    with st.sidebar:
        st.header("Run Settings")
        login_wait_seconds = st.number_input(
            "Login wait time",
            min_value=10,
            max_value=300,
            value=60,
            step=10,
            help="Complete manual login and CAPTCHA in the opened browser.",
        )
        headless = st.toggle(
            "Run browser headless",
            value=settings.headless,
            help="Keep this off when CAPTCHA login is required.",
        )
        automation_mode = st.selectbox(
            "Automation mode",
            options=["single", "bulk", "auto"],
            index=0,
            help=(
                "Single mode fills installment counts per account. "
                "Bulk mode selects all fetched accounts and saves once."
            ),
        )
        manual_pay_all_minutes = st.number_input(
            "Keep browser open after save",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
            help="Time allowed for you to manually click Pay All Saved Installments.",
        )

    uploaded_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        help="Expected columns: account_serial_no,no_of_installments",
    )

    dataframe = None
    if uploaded_file:
        try:
            dataframe = read_uploaded_csv(uploaded_file)
            st.success(f"Loaded {len(dataframe)} account(s).")
            st.dataframe(dataframe, use_container_width=True, height=260)
        except Exception as exc:
            st.error(str(exc))

    current_status = st.empty()
    progress_bar = st.progress(0)
    metric_columns = st.columns(4)
    total_metric = metric_columns[0].empty()
    success_metric = metric_columns[1].empty()
    failed_metric = metric_columns[2].empty()
    skipped_metric = metric_columns[3].empty()

    st.subheader("Logs")
    logs_container = st.empty()

    def render_summary(summary=None):
        summary = summary or st.session_state.summary or {}
        total_metric.metric("Total Processed", summary.get("total_processed", 0))
        success_metric.metric("Successful", summary.get("successful", 0))
        failed_metric.metric("Failed", summary.get("failed", 0))
        skipped_metric.metric("Skipped", summary.get("skipped", 0))

    def render_logs():
        logs_text = "\n".join(st.session_state.logs[-300:]) or "No logs yet."
        logs_container.markdown(
            (
                "<div style='height: 280px; overflow-y: auto; "
                "border: 1px solid rgba(49, 51, 63, 0.2); "
                "border-radius: 6px; padding: 0.75rem; "
                "background: rgba(250, 250, 250, 0.04);'>"
                f"<pre style='white-space: pre-wrap; margin: 0;'>{escape(logs_text)}</pre>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    render_summary()
    render_logs()

    start_disabled = (
        dataframe is None
        or dataframe.empty
        or st.session_state.is_running
    )

    if st.button("Start Automation", type="primary", disabled=start_disabled):
        st.session_state.logs = []
        st.session_state.results = None
        st.session_state.summary = None
        st.session_state.is_running = True

        logger = build_logger(render_logs)

        def wait_for_login():
            logger.info(
                "Waiting %s second(s) for manual login and CAPTCHA completion.",
                login_wait_seconds,
            )
            for remaining in range(int(login_wait_seconds), 0, -1):
                current_status.info(
                    f"Complete login in the opened browser. Continuing in {remaining}s."
                )
                time.sleep(1)

        def on_status(account, index, total):
            current_status.info(
                f"Processing {index}/{total}: {account.account_serial_no}"
            )

        def on_progress(index, total, summary):
            percent = int(index / total * 100) if total else 0
            progress_bar.progress(percent)
            render_summary(summary.to_dict())

        def wait_for_manual_pay_all():
            total_seconds = int(manual_pay_all_minutes) * 60
            logger.info(
                "Browser will remain open for %s minute(s). Click Pay All Saved Installments manually.",
                manual_pay_all_minutes,
            )
            for remaining in range(total_seconds, 0, -1):
                minutes, seconds = divmod(remaining, 60)
                current_status.warning(
                    "Click Pay All Saved Installments manually. "
                    f"Browser closes in {minutes:02d}:{seconds:02d}."
                )
                time.sleep(1)

        try:
            with st.spinner("Automation is running..."):
                summary = start(
                    dataframe=dataframe,
                    logger=logger,
                    status_callback=on_status,
                    progress_callback=on_progress,
                    wait_for_login_callback=wait_for_login,
                    manual_completion_callback=wait_for_manual_pay_all,
                    headless=headless,
                    automation_mode=automation_mode,
                ).to_dict()

            st.session_state.summary = summary
            st.session_state.results = summary["results"]
            progress_bar.progress(100)
            render_summary(summary)
            current_status.success("Automation completed. Browser closed after manual Pay All window.")
        except PlaywrightStartupError as exc:
            logger.error(str(exc))
            current_status.error(str(exc))
        except Exception as exc:
            logger.exception("Automation stopped unexpectedly.")
            current_status.error(f"Automation stopped: {exc}")
        finally:
            st.session_state.is_running = False
            render_logs()

    if st.session_state.results:
        st.subheader("Results")
        st.dataframe(
            pd.DataFrame(st.session_state.results),
            use_container_width=True,
            height=260,
        )
        st.download_button(
            "Download Results CSV",
            data=results_to_csv(st.session_state.results),
            file_name="rd_installment_results.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
