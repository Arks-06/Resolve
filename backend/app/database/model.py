"""
Defines the SQLAlchemy declarative ORM classes for your Tenant, Prompt, and dead-letter queue entities.
Establishes the strict relational constraints and indexing rules for the underlying PostgreSQL database.
"""

import datetime
from sqlalchemy import String, ForeignKey, LargeBinary, Integer, Text, Boolean, DateTime, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.database.session import Base

class Tenant(Base):
    """
    Represents an isolated enterprise corporate entity.
    Acts as the primary logical root for multi-tenant mapping.
    """
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    credentials: Mapped[list["TenantCredential"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    knowledge_base: Mapped[list["TenantKnowledge"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    prompts: Mapped[list["TenantPrompt"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    cost_logs: Mapped[list["TenantCostLog"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    dlq_records: Mapped[list["DeadLetterQueue"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class TenantCredential(Base):
    __tablename__ = "tenant_credentials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_name: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    tenant: Mapped["Tenant"] = relationship(back_populates="credentials")


class TenantKnowledge(Base):
    __tablename__ = "tenant_knowledge"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(1536), nullable=False)
    tenant: Mapped["Tenant"] = relationship(back_populates="knowledge_base")


class TenantPrompt(Base):
    __tablename__ = "tenant_prompts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    prompt_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    tenant: Mapped["Tenant"] = relationship(back_populates="prompts")
    __table_args__ = (UniqueConstraint("tenant_id", "prompt_key", "version", name="uq_tenant_prompt_version"),)


class TenantCostLog(Base):
    __tablename__ = "tenant_cost_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    tenant: Mapped["Tenant"] = relationship(back_populates="cost_logs")


class DeadLetterQueue(Base):
    """
    Immutable ledger for permanently failed background tasks.
    Captures exact state parameters for manual engineering audit.
    """
    __tablename__ = "dead_letter_queue"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    failed_payload: Mapped[str] = mapped_column(Text, nullable=False)
    error_reason: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    tenant: Mapped["Tenant"] = relationship(back_populates="dlq_records")