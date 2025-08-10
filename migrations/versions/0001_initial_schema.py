"""Initial schema for Reflex Executive Assistant.

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversations table
    op.create_table('conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('channel_id', sa.String(length=255), nullable=True),
        sa.Column('team_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('workflow_id', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)
    op.create_index(op.f('ix_conversations_platform'), 'conversations', ['platform'], unique=False)

    # Create messages table
    op.create_table('messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sender', sa.String(length=255), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_sender'), 'messages', ['sender'], unique=False)

    # Create workflow_executions table
    op.create_table('workflow_executions',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('workflow_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('trigger_user', sa.String(length=255), nullable=True),
        sa.Column('trigger_channel', sa.String(length=255), nullable=True),
        sa.Column('trigger_content', sa.Text(), nullable=True),
        sa.Column('team_id', sa.String(length=255), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_executions_status'), 'workflow_executions', ['status'], unique=False)
    op.create_index(op.f('ix_workflow_executions_workflow_type'), 'workflow_executions', ['workflow_type'], unique=False)

    # Create slack_channels table
    op.create_table('slack_channels',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('team_id', sa.String(length=255), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('member_count', sa.Integer(), nullable=True),
        sa.Column('topic', sa.String(length=500), nullable=True),
        sa.Column('purpose', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slack_channels_team_id'), 'slack_channels', ['team_id'], unique=False)

    # Create slack_users table
    op.create_table('slack_users',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('team_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('real_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=100), nullable=True),
        sa.Column('status_text', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slack_users_team_id'), 'slack_users', ['team_id'], unique=False)
    op.create_index(op.f('ix_slack_users_email'), 'slack_users', ['email'], unique=False)

    # Create slack_messages table
    op.create_table('slack_messages',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('channel_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('thread_ts', sa.String(length=255), nullable=True),
        sa.Column('ts', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('subtype', sa.String(length=50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['slack_channels.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['slack_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slack_messages_channel_id'), 'slack_messages', ['channel_id'], unique=False)
    op.create_index(op.f('ix_slack_messages_user_id'), 'slack_messages', ['user_id'], unique=False)
    op.create_index(op.f('ix_slack_messages_timestamp'), 'slack_messages', ['timestamp'], unique=False)

    # Create emails table
    op.create_table('emails',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('from_email', sa.String(length=255), nullable=False),
        sa.Column('to_emails', sa.Text(), nullable=False),
        sa.Column('cc_emails', sa.Text(), nullable=True),
        sa.Column('bcc_emails', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('body_plain', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('labels', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('is_important', sa.Boolean(), nullable=False),
        sa.Column('has_attachments', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_emails_thread_id'), 'emails', ['thread_id'], unique=False)
    op.create_index(op.f('ix_emails_from_email'), 'emails', ['from_email'], unique=False)
    op.create_index(op.f('ix_emails_received_at'), 'emails', ['received_at'], unique=False)

    # Create asana_projects table
    op.create_table('asana_projects',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('team_id', sa.String(length=255), nullable=True),
        sa.Column('owner_id', sa.String(length=255), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('default_view', sa.String(length=50), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('start_on', sa.Date(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asana_projects_workspace_id'), 'asana_projects', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_asana_projects_team_id'), 'asana_projects', ['team_id'], unique=False)

    # Create asana_tasks table
    op.create_table('asana_tasks',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('section_id', sa.String(length=255), nullable=True),
        sa.Column('assignee_id', sa.String(length=255), nullable=True),
        sa.Column('created_by_id', sa.String(length=255), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('due_time', sa.Time(), nullable=True),
        sa.Column('start_on', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['asana_projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asana_tasks_project_id'), 'asana_tasks', ['project_id'], unique=False)
    op.create_index(op.f('ix_asana_tasks_assignee_id'), 'asana_tasks', ['assignee_id'], unique=False)
    op.create_index(op.f('ix_asana_tasks_due_date'), 'asana_tasks', ['due_date'], unique=False)
    op.create_index(op.f('ix_asana_tasks_is_completed'), 'asana_tasks', ['is_completed'], unique=False)

    # Create asana_stories table
    op.create_table('asana_stories',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_by_id', sa.String(length=255), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_subtype', sa.String(length=50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['asana_tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asana_stories_task_id'), 'asana_stories', ['task_id'], unique=False)
    op.create_index(op.f('ix_asana_stories_type'), 'asana_stories', ['type'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_asana_stories_type'), table_name='asana_stories')
    op.drop_index(op.f('ix_asana_stories_task_id'), table_name='asana_stories')
    op.drop_table('asana_stories')

    op.drop_index(op.f('ix_asana_tasks_is_completed'), table_name='asana_tasks')
    op.drop_index(op.f('ix_asana_tasks_due_date'), table_name='asana_tasks')
    op.drop_index(op.f('ix_asana_tasks_assignee_id'), table_name='asana_tasks')
    op.drop_index(op.f('ix_asana_tasks_project_id'), table_name='asana_tasks')
    op.drop_table('asana_tasks')

    op.drop_index(op.f('ix_asana_projects_team_id'), table_name='asana_projects')
    op.drop_index(op.f('ix_asana_projects_workspace_id'), table_name='asana_projects')
    op.drop_table('asana_projects')

    op.drop_index(op.f('ix_emails_received_at'), table_name='emails')
    op.drop_index(op.f('ix_emails_from_email'), table_name='emails')
    op.drop_index(op.f('ix_emails_thread_id'), table_name='emails')
    op.drop_table('emails')

    op.drop_index(op.f('ix_slack_messages_timestamp'), table_name='slack_messages')
    op.drop_index(op.f('ix_slack_messages_user_id'), table_name='slack_messages')
    op.drop_index(op.f('ix_slack_messages_channel_id'), table_name='slack_messages')
    op.drop_table('slack_messages')

    op.drop_index(op.f('ix_slack_users_email'), table_name='slack_users')
    op.drop_index(op.f('ix_slack_users_team_id'), table_name='slack_users')
    op.drop_table('slack_users')

    op.drop_index(op.f('ix_slack_channels_team_id'), table_name='slack_channels')
    op.drop_table('slack_channels')

    op.drop_index(op.f('ix_workflow_executions_workflow_type'), table_name='workflow_executions')
    op.drop_index(op.f('ix_workflow_executions_status'), table_name='workflow_executions')
    op.drop_table('workflow_executions')

    op.drop_index(op.f('ix_messages_sender'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')

    op.drop_index(op.f('ix_conversations_platform'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_table('conversations') 