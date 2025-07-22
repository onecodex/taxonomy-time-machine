"""add performance indexes

Revision ID: 4bb4acc2c8d3
Revises: 119d8f99f4dc
Create Date: 2025-07-16 22:22:44.380181

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4bb4acc2c8d3"
down_revision: Union[str, Sequence[str], None] = "119d8f99f4dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create performance indexes matching the original schema
    op.create_index("idx_tax_id", "taxonomy", ["tax_id"])
    op.create_index("idx_parent_id", "taxonomy", ["parent_id"])
    op.create_index("idx_name", "taxonomy", [sa.text("lower(name)")])
    op.create_index("idx_tax_id_version_date", "taxonomy", ["tax_id", "version_date"])
    op.create_index("idx_name_version_date", "taxonomy", ["name", "version_date"])

    # Create FTS virtual table
    op.execute("CREATE VIRTUAL TABLE name_fts USING fts5(name)")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes and FTS table
    op.drop_index("idx_name_version_date", "taxonomy")
    op.drop_index("idx_tax_id_version_date", "taxonomy")
    op.drop_index("idx_name", "taxonomy")
    op.drop_index("idx_parent_id", "taxonomy")
    op.drop_index("idx_tax_id", "taxonomy")
    op.execute("DROP TABLE IF EXISTS name_fts")
