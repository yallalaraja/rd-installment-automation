# RD Installment Automation

A Python automation project for RD installment processing using Playwright, with a Streamlit UI for uploading account data, running the automation, tracking progress, and exporting results.

The project is designed around a modular backend:

- `app/core` - orchestration and runner entrypoint
- `app/services` - CSV loading and installment decision logic
- `app/automation` - Playwright browser actions only
- `app/models` - dataclass models
- `app/utils` - config and logging
- `ui` - Streamlit interface

## Features

- Upload RD account CSV files from the Streamlit UI
- Bulk account input into the portal textarea
- Manual login support for CAPTCHA-based login
- Select fetched accounts and save them
- Apply installment counts only where required
- Skip accounts with installment count `0` or `1`
- Live status and logs in the UI
- Final success, failed, and skipped summary
- Download automation results as CSV
- Keeps browser open after saving so the user can manually click **Pay All Saved Installments**

## Project Structure

```text
rd-installment-automation/
|-- app/
|   |-- automation/
|   |   `-- navigator.py
|   |-- core/
|   |   |-- engine.py
|   |   `-- runner.py
|   |-- models/
|   |   `-- account.py
|   |-- services/
|   |   |-- excel_loader.py
|   |   `-- installment_engine.py
|   `-- utils/
|       |-- config.py
|       `-- logger.py
|-- data/
|   `-- accounts.csv
|-- logs/
|-- ui/
|   `-- streamlit_app.py
|-- .env.example
|-- .gitignore
|-- main.py
|-- requirements.txt
|-- streamlit_app.py
`-- README.md
```

## Requirements

- Python 3.10+
- Playwright Chromium browser
- Streamlit

Install dependencies:

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## Environment Variables

Create a `.env` file in the project root.

Use `.env.example` as the template:

```env
AGENT_ID=
PASSWORD=
BASE_URL=https://dopagent.indiapost.gov.in
HEADLESS=false
TIMEOUT=60
```

Notes:

- `.env` is ignored by Git.
- `HEADLESS=false` is recommended because login requires CAPTCHA.
- Increase `TIMEOUT` if the portal is slow.

## CSV Format

Input CSV must contain:

```csv
account_serial_no,no_of_installments
020006507610,1
020013589971,3
020015306678,2
```

Rules:

- `no_of_installments <= 1` is skipped.
- `no_of_installments > 1` is applied.
- Blank installment values are treated as `0` and skipped.

## Run With Streamlit

From the project root:

```powershell
.\venv\Scripts\activate
streamlit run streamlit_app.py
```

If port `8501` is busy:

```powershell
streamlit run streamlit_app.py --server.port 8505
```

The root `streamlit_app.py` is a wrapper for:

```text
ui/streamlit_app.py
```

## Run From CLI

```powershell
.\venv\Scripts\activate
python main.py
```

The CLI flow waits for manual login and then waits again before closing the browser so the user can manually click Pay All.

## Automation Flow

1. User starts automation.
2. Browser opens login page.
3. User logs in manually because CAPTCHA is required.
4. Automation navigates to **Agent Enquire & Update Screen**.
5. All account numbers are entered in bulk:

   ```text
   020006507610,
   020013589971,
   020015306678,
   ```

6. Automation clicks Fetch.
7. Automation selects fetched account checkboxes and clicks Save.
8. For accounts where installments are greater than `1`:
   - Selects account radio
   - Fills installment count
   - Clicks Save
9. Automation stops before final payment.
10. User manually clicks **Pay All Saved Installments**.

## Streamlit Options

- **Login wait time**: Time given for manual login and CAPTCHA completion.
- **Run browser headless**: Keep disabled for CAPTCHA login.
- **Automation mode**:
  - `single`: Applies per-account installment counts.
  - `bulk`: Selects all fetched accounts and saves together.
  - `auto`: Uses single mode if any account has installments greater than `1`.
- **Keep browser open after save**: Time allowed for manual Pay All action.

## Troubleshooting

### Playwright Windows Permission Error

If you see:

```text
Playwright could not start its browser driver because Windows denied subprocess access
```

Run from your own PowerShell terminal:

```powershell
.\venv\Scripts\activate
python -m playwright install chromium
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print('Playwright OK'); p.stop()"
```

If it still fails, start PowerShell as Administrator and retry.

### Browser Closes Too Early

Use the Streamlit sidebar option:

```text
Keep browser open after save
```

Set it high enough to manually click **Pay All Saved Installments**.

### Portal Timeout

Increase timeout in `.env`:

```env
TIMEOUT=90
```

Restart Streamlit after changing `.env`.

## Important Safety Note

The final **Pay All Saved Installments** action is intentionally manual. The automation prepares and saves the installment entries, but the user must review and click Pay All themselves.
