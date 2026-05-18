from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Account:
    account_serial_no: str
    no_of_installments: int

    @classmethod
    def from_dict(cls, data):
        account_serial_no = str(data["account_serial_no"]).strip()
        no_of_installments = int(data["no_of_installments"])
        return cls(
            account_serial_no=account_serial_no,
            no_of_installments=no_of_installments,
        )

    def to_dict(self):
        return asdict(self)
