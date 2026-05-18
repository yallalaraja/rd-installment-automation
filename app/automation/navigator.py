import time

from app.utils.config import settings


class NavigationError(RuntimeError):
    pass


ACCOUNT_SEARCH_TEXTAREA = (
    "textarea#CustomAgentRDAccountFG\\.ACCOUNT_NUMBER_FOR_SEARCH"
)
FETCH_ACCOUNT_BUTTON = (
    "input[type='submit'][name='Action.FETCH_INPUT_ACCOUNT'], "
    "input[name='Action.FETCH_INPUT_ACCOUNT'], "
    "input[value='Fetch'], "
    "button:has-text('Fetch')"
)
INSTALLMENT_INPUT = "input#CustomAgentRDAccountFG\\.RD_INSTALLMENT_NO"
ADD_TO_LIST_BUTTON = "input[name='Action.ADD_TO_LIST']"
SAVE_ACCOUNTS_BUTTON = (
    "input[name='Action.SAVE_ACCOUNTS'], "
    "input[name*='SAVE_ACCOUNTS'], "
    "input[id*='SAVE_ACCOUNTS'], "
    "input[value='Save'], "
    "button:has-text('Save')"
)
PAY_ALL_BUTTON = (
    "input#PAY_ALL_SAVED_INSTALLMENTS, "
    "input[name='PAY_ALL_SAVED_INSTALLMENTS'], "
    "input[name*='PAY_ALL'], "
    "input[id*='PAY_ALL'], "
    "input[value='Pay All'], "
    "input[value*='Pay All'], "
    "button:has-text('Pay All Saved Installments'), "
    "button:has-text('Pay All')"
)
ACCOUNT_CHECKBOXES = (
    "input[type='checkbox'][name*='SELECT_INDEX_ARRAY'], "
    "input[type='checkbox'][id*='SELECT_INDEX_ARRAY']"
)
ACCOUNT_RADIOS = (
    "input[type='radio'][name*='SELECTED_INDEX'], "
    "input[type='radio'][id*='SELECTED_INDEX']"
)


def open_login_page(page, logger):
    logger.info("Open login page manually and login (CAPTCHA required)")
    page.goto(settings.base_url)


def _wait_for_page_ready(page):
    page.wait_for_load_state("domcontentloaded", timeout=settings.timeout * 1000)


def _click_text(page, text, logger, exact=True):
    timeout = settings.timeout * 1000
    logger.info("Looking for navigation item: %s", text)

    locator = page.get_by_text(text, exact=exact)
    if locator.count() > 0:
        try:
            locator.first.click(timeout=timeout)
            return
        except Exception:
            logger.info("Navigation item was not clickable on main page: %s", text)

    for frame in page.frames:
        frame_locator = frame.get_by_text(text, exact=exact)
        if frame_locator.count() == 0:
            continue
        try:
            frame_locator.first.click(timeout=timeout)
            return
        except Exception:
            logger.info(
                "Navigation item was present but not clickable in frame %s: %s",
                frame.name or frame.url,
                text,
            )

    raise NavigationError(f"Could not find clickable navigation item: {text}")


def _click_first_available_text(page, labels, logger):
    errors = []
    for label in labels:
        try:
            _click_text(page, label, logger, exact=True)
            return label
        except Exception as exc:
            errors.append(str(exc))

    raise NavigationError(
        "Could not navigate. Tried labels: " + ", ".join(labels)
    ) from RuntimeError(" | ".join(errors))


def _click_selector(page, selector, logger):
    logger.info("Looking for selector: %s", selector)
    locator = _wait_for_selector(page, selector)
    locator.click(timeout=settings.timeout * 1000)


def _wait_for_selector(page, selector, state="visible"):
    deadline = time.monotonic() + settings.timeout
    last_error = None

    while time.monotonic() < deadline:
        for locator_group in _all_locator_groups(page, selector):
            try:
                if locator_group.count() == 0:
                    continue

                locator = locator_group.first
                remaining_ms = max(int((deadline - time.monotonic()) * 1000), 1000)
                locator.wait_for(
                    state=state,
                    timeout=min(remaining_ms, settings.timeout * 1000),
                )
                return locator
            except Exception as exc:
                last_error = exc

        time.sleep(1)

    raise NavigationError(f"Timed out waiting for selector: {selector}") from last_error


def _wait_for_any_selector(page, selectors, state="visible"):
    deadline = time.monotonic() + settings.timeout
    last_error = None

    while time.monotonic() < deadline:
        for selector in selectors:
            for locator_group in _all_locator_groups(page, selector):
                try:
                    if locator_group.count() == 0:
                        continue

                    locator = locator_group.first
                    locator.wait_for(state=state, timeout=1000)
                    return locator
                except Exception as exc:
                    last_error = exc

        time.sleep(1)

    raise NavigationError(
        "Timed out waiting for selectors: " + ", ".join(selectors)
    ) from last_error


def _all_locator_groups(page, selector):
    groups = [page.locator(selector)]
    groups.extend(frame.locator(selector) for frame in page.frames)
    return groups


def _count_selector(page, selector):
    return sum(locator_group.count() for locator_group in _all_locator_groups(page, selector))


def _fill_selector(page, selector, value, logger):
    logger.info("Filling selector: %s", selector)
    locator = _wait_for_selector(page, selector)
    locator.fill(value, timeout=settings.timeout * 1000)


def _wait_after_action(page):
    try:
        page.wait_for_load_state("networkidle", timeout=settings.timeout * 1000)
    except Exception:
        _wait_for_page_ready(page)


def bulk_fetch_accounts(page, account_input, logger):
    logger.info("Submitting bulk account search")
    _fill_selector(page, ACCOUNT_SEARCH_TEXTAREA, account_input, logger)

    fetch_button = _wait_for_selector(page, FETCH_ACCOUNT_BUTTON)
    fetch_button.click(timeout=settings.timeout * 1000)
    _wait_after_action(page)
    _wait_for_any_selector(page, [ACCOUNT_CHECKBOXES, ACCOUNT_RADIOS, INSTALLMENT_INPUT])
    logger.info(
        "Fetched account controls found: checkboxes=%s, radios=%s",
        _count_selector(page, ACCOUNT_CHECKBOXES),
        _count_selector(page, ACCOUNT_RADIOS),
    )
    logger.info("Bulk account fetch completed")


def select_all_fetched_accounts(page, logger):
    logger.info("Selecting all fetched account checkboxes")
    selected_count = 0

    for checkbox_group in _all_locator_groups(page, ACCOUNT_CHECKBOXES):
        count = checkbox_group.count()
        for index in range(count):
            checkbox = checkbox_group.nth(index)
            checkbox.wait_for(state="attached", timeout=settings.timeout * 1000)
            if not checkbox.is_checked():
                try:
                    checkbox.check(timeout=settings.timeout * 1000)
                except Exception:
                    checkbox.check(timeout=settings.timeout * 1000, force=True)
            selected_count += 1

    if selected_count == 0:
        raise NavigationError("No account checkboxes were found after Fetch.")

    logger.info("Selected %s account checkbox(es)", selected_count)


def select_fetched_account_radio(page, row_index, logger):
    logger.info("Selecting fetched account radio index: %s", row_index)

    for radio_group in _all_locator_groups(page, ACCOUNT_RADIOS):
        count = radio_group.count()
        if row_index < count:
            radio = radio_group.nth(row_index)
            radio.wait_for(state="attached", timeout=settings.timeout * 1000)
            try:
                radio.check(timeout=settings.timeout * 1000)
            except Exception:
                radio.check(timeout=settings.timeout * 1000, force=True)
            return

    raise NavigationError(f"No account radio found at index {row_index}.")


def fill_installment_number(page, installment_count, logger):
    logger.info("Filling installment number: %s", installment_count)
    _fill_selector(page, INSTALLMENT_INPUT, str(installment_count), logger)


def add_selected_account_to_list(page, logger):
    logger.info("Adding selected account to list")
    _click_selector(page, ADD_TO_LIST_BUTTON, logger)
    _wait_after_action(page)


def save_accounts(page, logger):
    logger.info("Saving selected account(s)")
    _click_selector(page, SAVE_ACCOUNTS_BUTTON, logger)
    _wait_after_action(page)
    try:
        _wait_for_any_selector(
            page,
            [ACCOUNT_RADIOS, INSTALLMENT_INPUT, PAY_ALL_BUTTON],
            state="attached",
        )
    except Exception:
        logger.info("Save completed, but no follow-up controls were detected yet.")


def click_pay_all_saved_installments(page, logger):
    logger.info("Clicking Pay All saved installments")
    _click_selector(page, PAY_ALL_BUTTON, logger)
    _wait_after_action(page)


def apply_installment_to_fetched_account(page, account, logger):
    fill_installment_number(page, account.no_of_installments, logger)
    add_selected_account_to_list(page, logger)


def navigate_to_accounts_section(page, logger):
    logger.info("Navigating to Accounts section")
    _wait_for_page_ready(page)

    _click_first_available_text(page, ["Accounts", "Account"], logger)
    _wait_for_page_ready(page)

    selected_label = _click_first_available_text(
        page,
        [
            "Agent Enquire & Update Screen",
            "Agent Enquiry & Update Screen",
            "Agent Enquire and Update Screen",
        ],
        logger,
    )
    logger.info("Selected navigation item: %s", selected_label)

    _click_selector(page, "input[value='C']", logger)


def add_installment_to_list(page, account, logger):
    apply_installment_to_fetched_account(page, account, logger)
