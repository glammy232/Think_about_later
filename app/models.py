from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

Money = Annotated[float, Field(ge=0)]
Name80 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]
Name120 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
Text200 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OperationType(StrEnum):
    expense = "expense"
    income = "income"


class SplitType(StrEnum):
    equal = "equal"
    custom = "custom"


class DebtStatus(StrEnum):
    active = "active"
    settled = "settled"


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class User(BaseModel):
    id: str
    name: Name80
    avatar_url: HttpUrl | None = None


class MemberCreate(BaseModel):
    name: Name80
    avatar_url: HttpUrl | None = None


class Group(BaseModel):
    id: str
    name: str
    member_ids: list[str]


class ShareInput(BaseModel):
    user_id: str
    amount: Money


class OperationCreate(BaseModel):
    type: OperationType
    title: Name120
    amount: Annotated[float, Field(gt=0)]
    category: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
    ]
    payer_id: str
    participant_ids: list[str] = Field(min_length=1)
    split_type: SplitType = SplitType.equal
    shares: list[ShareInput] | None = None
    operation_date: date = Field(default_factory=date.today)
    comment: str | None = Field(default=None, max_length=500)
    source: str = "manual"

    @field_validator("participant_ids")
    @classmethod
    def participants_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("participant_ids must not contain duplicates")
        return value

    @model_validator(mode="after")
    def validate_custom_shares(self):
        if self.type == OperationType.income:
            return self
        if self.split_type == SplitType.custom:
            if not self.shares:
                raise ValueError("shares are required for custom split")
            share_user_ids = [share.user_id for share in self.shares]
            if len(share_user_ids) != len(set(share_user_ids)):
                raise ValueError("shares must not contain duplicate users")
            if {s.user_id for s in self.shares} != set(self.participant_ids):
                raise ValueError("shares must match participant_ids")
            if abs(sum(s.amount for s in self.shares) - self.amount) > 0.01:
                raise ValueError("shares total must equal operation amount")
        return self


class Operation(BaseModel):
    id: str
    group_id: str
    type: OperationType
    title: str
    amount: float
    category: str
    payer_id: str
    participant_ids: list[str]
    split_type: SplitType
    shares: list[ShareInput]
    operation_date: date
    comment: str | None = None
    source: str = "manual"
    created_at: datetime = Field(default_factory=utc_now)


class DirectDebtCreate(BaseModel):
    debtor_id: str
    creditor_id: str
    amount: Annotated[float, Field(gt=0)]
    description: Text200
    due_date: date | None = None

    @model_validator(mode="after")
    def users_must_differ(self):
        if self.debtor_id == self.creditor_id:
            raise ValueError("debtor and creditor must be different users")
        return self


class Debt(BaseModel):
    id: str
    group_id: str
    debtor_id: str
    creditor_id: str
    amount: float
    description: str
    status: DebtStatus = DebtStatus.active
    due_date: date | None = None
    created_at: datetime = Field(default_factory=utc_now)
    settled_at: datetime | None = None


class PaymentCreate(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: Annotated[float, Field(gt=0)]
    comment: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def users_must_differ(self):
        if self.from_user_id == self.to_user_id:
            raise ValueError("payment users must be different")
        return self


class Payment(BaseModel):
    id: str
    group_id: str
    from_user_id: str
    to_user_id: str
    amount: float
    comment: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class BalanceItem(BaseModel):
    user_id: str
    user_name: str
    balance: float
    status: str


class Transfer(BaseModel):
    from_user_id: str
    from_user_name: str
    to_user_id: str
    to_user_name: str
    amount: float


class DashboardSummary(BaseModel):
    group_id: str
    current_user_id: str
    total_expenses: float
    user_expenses: float
    owed_to_user: float
    user_owes: float


class ReceiptParseRequest(BaseModel):
    qr_data: str = Field(min_length=3, description="Raw QR string from a receipt")


class ReceiptDraft(BaseModel):
    merchant: str
    amount: float
    purchased_at: datetime
    category: str
    fiscal_fields: dict[str, str]
    items: list[dict[str, str | float]]
    provider: str = "mock"


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class AssistantResponse(BaseModel):
    answer: str
    mode: str = "mock"


class SettingsUpdate(BaseModel):
    name: Name80 | None = None
    avatar_url: HttpUrl | None = None
    currency: Currency | None = None


class GroupSettingsUpdate(BaseModel):
    name: Name120
