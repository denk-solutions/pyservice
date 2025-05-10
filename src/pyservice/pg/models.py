import datetime
import uuid

from sqlalchemy import CheckConstraint, Index, literal_column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.types import Enum as SQLAlchemyEnum
from sqlalchemy.types import Uuid

from pyservice.auth.token import RefreshTokenStatus
from pyservice.pg.utils import PasswordHashType, UserIdentity, UserIdentityType, utcnow


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    created_at: Mapped[datetime.datetime] = mapped_column(server_default=utcnow())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=utcnow(), onupdate=utcnow()
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id!r})"


class PGUser(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "identity ~ '^[^:]+:[^:]+$'", name="valid_user_identity_format"
        ),
    )

    email: Mapped[str] = mapped_column(unique=True)
    identity: Mapped[UserIdentity] = mapped_column(UserIdentityType(), unique=True)


class PGRefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index(
            "ix_one_active_token_per_user",
            "user_id",
            unique=True,
            postgresql_where=(
                literal_column("status") == RefreshTokenStatus.ACTIVE.value
            ),
        ),
    )

    token_hash: Mapped[str] = mapped_column(PasswordHashType, unique=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    user: Mapped[PGUser] = relationship()

    status: Mapped[RefreshTokenStatus] = mapped_column(
        SQLAlchemyEnum(RefreshTokenStatus, name="refresh_token_status")
    )
