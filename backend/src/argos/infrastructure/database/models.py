"""Modelos ORM exclusivos da infraestrutura de persistência."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, MetaData, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base dos modelos, com nomes estáveis para constraints."""

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


class TelegramUserRecord(Base):
    """Identidade proprietária e destino atual de mensagens."""

    __tablename__ = "telegram_users"
    __table_args__ = (
        CheckConstraint("telegram_user_id > 0", name="positive_user_id"),
        CheckConstraint("chat_id > 0", name="positive_chat_id"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class TelegramUpdateInbox(Base):
    """Update persistido antes de qualquer efeito externo."""

    __tablename__ = "telegram_update_inbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'dead_letter')",
            name="valid_status",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        CheckConstraint(
            "(status = 'processing' AND lease_token IS NOT NULL "
            "AND lease_expires_at IS NOT NULL AND completed_at IS NULL) "
            "OR (status = 'completed' AND lease_token IS NULL "
            "AND lease_expires_at IS NULL AND completed_at IS NOT NULL) "
            "OR (status IN ('pending', 'dead_letter') "
            "AND lease_token IS NULL AND lease_expires_at IS NULL "
            "AND completed_at IS NULL)",
            name="valid_lifecycle",
        ),
        Index(
            "ix_telegram_update_inbox_available",
            "next_attempt_at",
            "received_at",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_telegram_update_inbox_expired_lease",
            "lease_expires_at",
            postgresql_where=text("status = 'processing'"),
        ),
    )

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lease_token: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class TelegramConversationDraftRecord(Base):
    """Um único rascunho conversacional por proprietário."""

    __tablename__ = "telegram_conversation_drafts"
    __table_args__ = (
        CheckConstraint(
            "state IN ('awaiting_url', 'awaiting_alias', 'awaiting_target_price', "
            "'awaiting_interval', 'awaiting_confirmation', "
            "'awaiting_product_to_remove', 'awaiting_removal_confirmation')",
            name="valid_state",
        ),
        CheckConstraint("expires_at > created_at", name="valid_expiry"),
        Index("ix_telegram_conversation_drafts_expires_at", "expires_at"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("telegram_users.telegram_user_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TelegramAdmissionOwner(Base):
    """Bloqueio e horário monotônico, inclusive antes de /start."""

    __tablename__ = "telegram_admission_owners"
    __table_args__ = (CheckConstraint("telegram_user_id > 0", name="positive_user_id"),)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TelegramAdmissionRecord(Base):
    """Decisão mínima durável; rejeições não armazenam o payload."""

    __tablename__ = "telegram_admissions"
    __table_args__ = (
        CheckConstraint("decision IN ('admitted', 'rate_limited')", name="valid_decision"),
        Index("ix_telegram_admissions_owner_window", "telegram_user_id", "decided_at",
              postgresql_where=text("decision = 'admitted'")),
    )
    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger,
        ForeignKey("telegram_admission_owners.telegram_user_id"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
