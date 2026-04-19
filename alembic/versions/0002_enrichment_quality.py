"""enrichment quality columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-19

Adds:
  - examples.when_to_use, examples.difficulty_level
  - exercises.exercise_type, exercises.options, exercises.correct_answer,
    exercises.buggy_code, exercises.bug_explanation
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("examples", sa.Column("when_to_use", sa.String(500), nullable=True))
    op.add_column("examples", sa.Column("difficulty_level", sa.Integer(), nullable=True))

    op.add_column("exercises", sa.Column("exercise_type", sa.String(30), nullable=False, server_default="build_from_spec"))
    op.add_column("exercises", sa.Column("options", sa.JSON(), nullable=True))
    op.add_column("exercises", sa.Column("correct_answer", sa.Text(), nullable=True))
    op.add_column("exercises", sa.Column("buggy_code", sa.Text(), nullable=True))
    op.add_column("exercises", sa.Column("bug_explanation", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("examples", "when_to_use")
    op.drop_column("examples", "difficulty_level")
    op.drop_column("exercises", "bug_explanation")
    op.drop_column("exercises", "buggy_code")
    op.drop_column("exercises", "correct_answer")
    op.drop_column("exercises", "options")
    op.drop_column("exercises", "exercise_type")
