"""Add cascade delete to all user relationships

Revision ID: add_cascade_delete
Revises: add_class_id_to_inquiry_theme_and_activity_log
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_cascade_delete'
down_revision = 'add_class_id_to_inquiry_theme_and_activity_log'
branch_labels = None
depends_on = None

def upgrade():
    """
    Add ON DELETE CASCADE to all foreign keys referencing users table.
    Note: This migration only updates the database constraints.
    The SQLAlchemy model cascade settings have been updated separately.
    """
    
    # Drop existing foreign keys and recreate with CASCADE
    with op.batch_alter_table('class_groups') as batch_op:
        batch_op.drop_constraint('class_groups_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('class_groups_ibfk_2', 'users', ['teacher_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('student_enrollments') as batch_op:
        batch_op.drop_constraint('student_enrollments_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('student_enrollments_ibfk_1', 'users', ['student_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('class_enrollments') as batch_op:
        batch_op.drop_constraint('class_enrollments_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('class_enrollments_ibfk_2', 'users', ['student_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('main_themes') as batch_op:
        batch_op.drop_constraint('main_themes_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('main_themes_ibfk_1', 'users', ['teacher_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('curriculums') as batch_op:
        batch_op.drop_constraint('curriculums_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('curriculums_ibfk_2', 'users', ['teacher_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('rubric_templates') as batch_op:
        batch_op.drop_constraint('rubric_templates_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('rubric_templates_ibfk_2', 'users', ['teacher_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('groups') as batch_op:
        batch_op.drop_constraint('groups_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('groups_ibfk_2', 'users', ['created_by'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('group_memberships') as batch_op:
        batch_op.drop_constraint('group_memberships_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('group_memberships_ibfk_2', 'users', ['student_id'], ['id'], ondelete='CASCADE')
    
    # BaseBuilder module tables
    with op.batch_alter_table('problem_categories') as batch_op:
        batch_op.drop_constraint('problem_categories_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('problem_categories_ibfk_2', 'users', ['created_by'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('text_deliveries') as batch_op:
        batch_op.drop_constraint('text_deliveries_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('text_deliveries_ibfk_3', 'users', ['delivered_by'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('basic_knowledge_items') as batch_op:
        batch_op.drop_constraint('basic_knowledge_items_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('basic_knowledge_items_ibfk_3', 'users', ['created_by'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('knowledge_theme_relations') as batch_op:
        batch_op.drop_constraint('knowledge_theme_relations_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('knowledge_theme_relations_ibfk_3', 'users', ['created_by'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('answer_records') as batch_op:
        batch_op.drop_constraint('answer_records_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('answer_records_ibfk_1', 'users', ['student_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('proficiency_records') as batch_op:
        batch_op.drop_constraint('proficiency_records_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('proficiency_records_ibfk_1', 'users', ['student_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('text_proficiency_records') as batch_op:
        batch_op.drop_constraint('text_proficiency_records_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('text_proficiency_records_ibfk_1', 'users', ['student_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('learning_paths') as batch_op:
        batch_op.drop_constraint('learning_paths_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('learning_paths_ibfk_2', 'users', ['created_by'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('path_assignments') as batch_op:
        batch_op.drop_constraint('path_assignments_ibfk_2', type_='foreignkey')
        batch_op.drop_constraint('path_assignments_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('path_assignments_ibfk_2', 'users', ['student_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('path_assignments_ibfk_3', 'users', ['assigned_by'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('word_proficiency_records') as batch_op:
        batch_op.drop_constraint('word_proficiency_records_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('word_proficiency_records_ibfk_1', 'users', ['student_id'], ['id'], ondelete='CASCADE')
    
    with op.batch_alter_table('text_sets') as batch_op:
        batch_op.drop_constraint('text_sets_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('text_sets_ibfk_3', 'users', ['created_by'], ['id'], ondelete='CASCADE')

def downgrade():
    """
    Remove ON DELETE CASCADE from all foreign keys referencing users table.
    """
    
    # Revert foreign keys to their original state (without CASCADE)
    with op.batch_alter_table('class_groups') as batch_op:
        batch_op.drop_constraint('class_groups_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('class_groups_ibfk_2', 'users', ['teacher_id'], ['id'])
    
    with op.batch_alter_table('student_enrollments') as batch_op:
        batch_op.drop_constraint('student_enrollments_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('student_enrollments_ibfk_1', 'users', ['student_id'], ['id'])
    
    with op.batch_alter_table('class_enrollments') as batch_op:
        batch_op.drop_constraint('class_enrollments_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('class_enrollments_ibfk_2', 'users', ['student_id'], ['id'])
    
    with op.batch_alter_table('main_themes') as batch_op:
        batch_op.drop_constraint('main_themes_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('main_themes_ibfk_1', 'users', ['teacher_id'], ['id'])
    
    with op.batch_alter_table('curriculums') as batch_op:
        batch_op.drop_constraint('curriculums_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('curriculums_ibfk_2', 'users', ['teacher_id'], ['id'])
    
    with op.batch_alter_table('rubric_templates') as batch_op:
        batch_op.drop_constraint('rubric_templates_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('rubric_templates_ibfk_2', 'users', ['teacher_id'], ['id'])
    
    with op.batch_alter_table('groups') as batch_op:
        batch_op.drop_constraint('groups_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('groups_ibfk_2', 'users', ['created_by'], ['id'])
    
    with op.batch_alter_table('group_memberships') as batch_op:
        batch_op.drop_constraint('group_memberships_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('group_memberships_ibfk_2', 'users', ['student_id'], ['id'])
    
    # BaseBuilder module tables
    with op.batch_alter_table('problem_categories') as batch_op:
        batch_op.drop_constraint('problem_categories_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('problem_categories_ibfk_2', 'users', ['created_by'], ['id'])
    
    with op.batch_alter_table('text_deliveries') as batch_op:
        batch_op.drop_constraint('text_deliveries_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('text_deliveries_ibfk_3', 'users', ['delivered_by'], ['id'])
    
    with op.batch_alter_table('basic_knowledge_items') as batch_op:
        batch_op.drop_constraint('basic_knowledge_items_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('basic_knowledge_items_ibfk_3', 'users', ['created_by'], ['id'])
    
    with op.batch_alter_table('knowledge_theme_relations') as batch_op:
        batch_op.drop_constraint('knowledge_theme_relations_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('knowledge_theme_relations_ibfk_3', 'users', ['created_by'], ['id'])
    
    with op.batch_alter_table('answer_records') as batch_op:
        batch_op.drop_constraint('answer_records_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('answer_records_ibfk_1', 'users', ['student_id'], ['id'])
    
    with op.batch_alter_table('proficiency_records') as batch_op:
        batch_op.drop_constraint('proficiency_records_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('proficiency_records_ibfk_1', 'users', ['student_id'], ['id'])
    
    with op.batch_alter_table('text_proficiency_records') as batch_op:
        batch_op.drop_constraint('text_proficiency_records_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('text_proficiency_records_ibfk_1', 'users', ['student_id'], ['id'])
    
    with op.batch_alter_table('learning_paths') as batch_op:
        batch_op.drop_constraint('learning_paths_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key('learning_paths_ibfk_2', 'users', ['created_by'], ['id'])
    
    with op.batch_alter_table('path_assignments') as batch_op:
        batch_op.drop_constraint('path_assignments_ibfk_2', type_='foreignkey')
        batch_op.drop_constraint('path_assignments_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('path_assignments_ibfk_2', 'users', ['student_id'], ['id'])
        batch_op.create_foreign_key('path_assignments_ibfk_3', 'users', ['assigned_by'], ['id'])
    
    with op.batch_alter_table('word_proficiency_records') as batch_op:
        batch_op.drop_constraint('word_proficiency_records_ibfk_1', type_='foreignkey')
        batch_op.create_foreign_key('word_proficiency_records_ibfk_1', 'users', ['student_id'], ['id'])
    
    with op.batch_alter_table('text_sets') as batch_op:
        batch_op.drop_constraint('text_sets_ibfk_3', type_='foreignkey')
        batch_op.create_foreign_key('text_sets_ibfk_3', 'users', ['created_by'], ['id'])