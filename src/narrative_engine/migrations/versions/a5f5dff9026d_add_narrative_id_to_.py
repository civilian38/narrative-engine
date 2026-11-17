"""add narrative_id to SessionCharacterOpinion

Revision ID: a5f5dff9026d
Revises: 46d7dd606bfb
Create Date: 2026-11-17 14:03:32.721581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5f5dff9026d'
down_revision: Union[str, Sequence[str], None] = '46d7dd606bfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the new column as nullable.
    op.add_column(
        'session_character_opinion',
        sa.Column(
            'session_narrative_id',
            sa.Integer(),
            nullable=True,
        ),
    )

    # 2. Backfill from_character's narrative ID.
    op.execute("""
        UPDATE session_character_opinion
        SET session_narrative_id = (
            SELECT sc.session_narrative_id
            FROM session_character AS sc
            WHERE sc.id = session_character_opinion.from_character_id
        )
    """)

    # 3. Create the unique index required by the composite foreign keys.
    op.create_index(
        'uq_session_character_narrative_id',
        'session_character',
        ['session_narrative_id', 'id'],
        unique=True,
    )

    # 4. Add constraints and make the column non-nullable.
    with op.batch_alter_table('session_character_opinion') as batch_op:
        batch_op.alter_column(
            'session_narrative_id',
            existing_type=sa.Integer(),
            nullable=False,
        )

        batch_op.create_foreign_key(
            'fk_opinion_from_character_session',
            'session_character',
            ['session_narrative_id', 'from_character_id'],
            ['session_narrative_id', 'id'],
        )

        batch_op.create_foreign_key(
            'fk_opinion_to_character_session',
            'session_character',
            ['session_narrative_id', 'to_character_id'],
            ['session_narrative_id', 'id'],
        )

        batch_op.create_foreign_key(
            'fk_opinion_session_narrative',
            'session_narrative',
            ['session_narrative_id'],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    with op.batch_alter_table('session_character_opinion') as batch_op:
        batch_op.drop_constraint(
            'fk_opinion_session_narrative',
            type_='foreignkey',
        )
        batch_op.drop_constraint(
            'fk_opinion_to_character_session',
            type_='foreignkey',
        )
        batch_op.drop_constraint(
            'fk_opinion_from_character_session',
            type_='foreignkey',
        )

        batch_op.drop_column('session_narrative_id')

    op.drop_index(
        'uq_session_character_narrative_id',
        table_name='session_character',
    )
    # ### end Alembic commands ###
