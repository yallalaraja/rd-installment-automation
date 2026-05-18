from dataclasses import dataclass

from app.models.account import Account


@dataclass(frozen=True)
class InstallmentDecision:
    status: str
    message: str
    should_apply: bool


def decide_installment(account: Account, logger=None):
    if account.no_of_installments <= 1:
        message = (
            f"Skipping {account.account_serial_no} "
            f"(installments={account.no_of_installments})"
        )
        if logger:
            logger.info(message)
        return InstallmentDecision(
            status="skipped",
            message="Skipped because installments <= 1",
            should_apply=False,
        )

    message = (
        f"Applying {account.no_of_installments} installments "
        f"for {account.account_serial_no}"
    )
    if logger:
        logger.info(message)
    return InstallmentDecision(
        status="success",
        message="Processed successfully",
        should_apply=True,
    )
