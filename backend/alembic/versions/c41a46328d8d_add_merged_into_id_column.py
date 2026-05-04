"""add merged_into_id column

Revision ID: c41a46328d8d
Revises: 4bb4acc2c8d3
Create Date: 2026-05-02 18:40:27.163153

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c41a46328d8d"
down_revision: Union[str, Sequence[str], None] = "4bb4acc2c8d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "taxonomy",
        sa.Column("merged_into_id", sa.Text(), nullable=True),
    )
    op.create_index("idx_merged_into_id", "taxonomy", ["merged_into_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_merged_into_id", "taxonomy")
    op.drop_column("taxonomy", "merged_into_id")
