"""add phase 6 nutrition tables

Revision ID: 20260705_0002
Revises: 20260705_0001
Create Date: 2026-07-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260705_0002"
down_revision: Union[str, None] = "20260705_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


nutrition_foods = sa.table(
    "nutrition_foods",
    sa.column("name", sa.String),
    sa.column("aliases", sa.Text),
    sa.column("calories_per_100g", sa.Float),
    sa.column("protein_g_per_100g", sa.Float),
    sa.column("carbs_g_per_100g", sa.Float),
    sa.column("fat_g_per_100g", sa.Float),
    sa.column("default_serving_grams", sa.Float),
    sa.column("default_serving_description", sa.String),
)


def upgrade() -> None:
    op.add_column(
        "meals",
        sa.Column("estimated_protein_g", sa.Float(), nullable=True),
    )
    op.add_column(
        "meals",
        sa.Column("estimated_carbs_g", sa.Float(), nullable=True),
    )
    op.add_column(
        "meals",
        sa.Column("estimated_fat_g", sa.Float(), nullable=True),
    )
    op.add_column(
        "meals",
        sa.Column("nutrition_confidence", sa.String(length=50), nullable=True),
    )

    op.create_table(
        "nutrition_foods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("aliases", sa.Text(), nullable=True),
        sa.Column("calories_per_100g", sa.Float(), nullable=False),
        sa.Column(
            "protein_g_per_100g",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "carbs_g_per_100g",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "fat_g_per_100g",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("default_serving_grams", sa.Float(), nullable=True),
        sa.Column(
            "default_serving_description",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_nutrition_foods_name"),
        "nutrition_foods",
        ["name"],
        unique=True,
    )

    op.create_table(
        "meal_food_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meal_id", sa.Integer(), nullable=False),
        sa.Column("nutrition_food_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("estimated_portion", sa.String(length=150), nullable=True),
        sa.Column("estimated_grams", sa.Float(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("protein_g", sa.Float(), nullable=True),
        sa.Column("carbs_g", sa.Float(), nullable=True),
        sa.Column("fat_g", sa.Float(), nullable=True),
        sa.Column("confidence", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["nutrition_food_id"],
            ["nutrition_foods.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_meal_food_items_meal_id"),
        "meal_food_items",
        ["meal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_meal_food_items_nutrition_food_id"),
        "meal_food_items",
        ["nutrition_food_id"],
        unique=False,
    )

    op.bulk_insert(
        nutrition_foods,
        [
            {
                "name": "egg",
                "aliases": "eggs,boiled egg,fried egg",
                "calories_per_100g": 155,
                "protein_g_per_100g": 13,
                "carbs_g_per_100g": 1.1,
                "fat_g_per_100g": 11,
                "default_serving_grams": 50,
                "default_serving_description": "1 large egg",
            },
            {
                "name": "paratha",
                "aliases": "plain paratha,roti paratha",
                "calories_per_100g": 326,
                "protein_g_per_100g": 6.4,
                "carbs_g_per_100g": 45,
                "fat_g_per_100g": 13,
                "default_serving_grams": 80,
                "default_serving_description": "1 medium paratha",
            },
            {
                "name": "chai",
                "aliases": "tea,milk tea,cup chai",
                "calories_per_100g": 45,
                "protein_g_per_100g": 1.5,
                "carbs_g_per_100g": 7,
                "fat_g_per_100g": 1.2,
                "default_serving_grams": 240,
                "default_serving_description": "1 cup",
            },
            {
                "name": "white rice",
                "aliases": "rice,cooked rice,boiled rice",
                "calories_per_100g": 130,
                "protein_g_per_100g": 2.7,
                "carbs_g_per_100g": 28,
                "fat_g_per_100g": 0.3,
                "default_serving_grams": 180,
                "default_serving_description": "1 cooked cup",
            },
            {
                "name": "chicken breast",
                "aliases": "chicken,grilled chicken,chicken pieces",
                "calories_per_100g": 165,
                "protein_g_per_100g": 31,
                "carbs_g_per_100g": 0,
                "fat_g_per_100g": 3.6,
                "default_serving_grams": 100,
                "default_serving_description": "1 palm-sized cooked portion",
            },
            {
                "name": "chicken biryani",
                "aliases": "biryani,chicken rice",
                "calories_per_100g": 170,
                "protein_g_per_100g": 7,
                "carbs_g_per_100g": 23,
                "fat_g_per_100g": 5,
                "default_serving_grams": 250,
                "default_serving_description": "1 serving",
            },
            {
                "name": "raita",
                "aliases": "yogurt sauce,yoghurt sauce",
                "calories_per_100g": 60,
                "protein_g_per_100g": 3.5,
                "carbs_g_per_100g": 5,
                "fat_g_per_100g": 3,
                "default_serving_grams": 45,
                "default_serving_description": "3 tablespoons",
            },
            {
                "name": "banana",
                "aliases": "bananas",
                "calories_per_100g": 89,
                "protein_g_per_100g": 1.1,
                "carbs_g_per_100g": 23,
                "fat_g_per_100g": 0.3,
                "default_serving_grams": 118,
                "default_serving_description": "1 medium banana",
            },
            {
                "name": "apple",
                "aliases": "apples",
                "calories_per_100g": 52,
                "protein_g_per_100g": 0.3,
                "carbs_g_per_100g": 14,
                "fat_g_per_100g": 0.2,
                "default_serving_grams": 180,
                "default_serving_description": "1 medium apple",
            },
            {
                "name": "whole milk",
                "aliases": "milk",
                "calories_per_100g": 61,
                "protein_g_per_100g": 3.2,
                "carbs_g_per_100g": 4.8,
                "fat_g_per_100g": 3.3,
                "default_serving_grams": 240,
                "default_serving_description": "1 cup",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_meal_food_items_nutrition_food_id"),
        table_name="meal_food_items",
    )
    op.drop_index(op.f("ix_meal_food_items_meal_id"), table_name="meal_food_items")
    op.drop_table("meal_food_items")
    op.drop_index(op.f("ix_nutrition_foods_name"), table_name="nutrition_foods")
    op.drop_table("nutrition_foods")
    op.drop_column("meals", "nutrition_confidence")
    op.drop_column("meals", "estimated_fat_g")
    op.drop_column("meals", "estimated_carbs_g")
    op.drop_column("meals", "estimated_protein_g")
