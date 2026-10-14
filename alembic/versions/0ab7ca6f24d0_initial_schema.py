"""Initial schema

Revision ID: 0ab7ca6f24d0
Revises: 
Create Date: 2026-10-08 01:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0ab7ca6f24d0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('scenarios',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('scenario_id', sa.String(), nullable=False),
        sa.Column('agent_version', sa.String(), nullable=False),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('replay_of_run_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metrics_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['replay_of_run_id'], ['runs.id'], ),
        sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_runs_replay_of_run_id'), 'runs', ['replay_of_run_id'], unique=False)
    op.create_index(op.f('ix_runs_scenario_id'), 'runs', ['scenario_id'], unique=False)
    
    op.create_table('decision_traces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('step_name', sa.String(), nullable=False),
        sa.Column('trace_data_json', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_decision_traces_run_id'), 'decision_traces', ['run_id'], unique=False)
    
    op.create_table('memories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('context_id', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('previous_version_id', sa.String(), nullable=True),
        sa.Column('simulated_time_iso', sa.String(), nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('contradictions_json', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('confirmation_event_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memories_context_id'), 'memories', ['context_id'], unique=False)
    
    op.create_table('llm_recordings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('call_index', sa.Integer(), nullable=False),
        sa.Column('prompt_hash', sa.String(), nullable=False),
        sa.Column('prompt_json', sa.JSON(), nullable=False),
        sa.Column('response_json', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'call_index', name='uq_llm_recording_run_call')
    )
    op.create_index(op.f('ix_llm_recordings_run_id'), 'llm_recordings', ['run_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_llm_recordings_run_id'), table_name='llm_recordings')
    op.drop_table('llm_recordings')
    op.drop_index(op.f('ix_memories_context_id'), table_name='memories')
    op.drop_table('memories')
    op.drop_index(op.f('ix_decision_traces_run_id'), table_name='decision_traces')
    op.drop_table('decision_traces')
    op.drop_index(op.f('ix_runs_scenario_id'), table_name='runs')
    op.drop_index(op.f('ix_runs_replay_of_run_id'), table_name='runs')
    op.drop_table('runs')
    op.drop_table('scenarios')

