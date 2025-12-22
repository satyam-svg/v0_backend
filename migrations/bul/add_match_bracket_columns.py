#!/usr/bin/env python3
"""
Migration script to add bracket-related columns to the match table.
Run this script to add: predecessor_1, predecessor_2, successor, bracket_position, round_number
"""

import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import Config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

def run_migration():
    """Add missing bracket columns to match table"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = :db_name 
                AND TABLE_NAME = 'match' 
                AND COLUMN_NAME IN ('predecessor_1', 'predecessor_2', 'successor', 'bracket_position', 'round_number')
            """), {'db_name': Config.DB_NAME})
            
            existing_columns = {row[0] for row in result.fetchall()}
            columns_to_add = []
            
            if 'predecessor_1' not in existing_columns:
                columns_to_add.append("ADD COLUMN `predecessor_1` INT NULL")
            if 'predecessor_2' not in existing_columns:
                columns_to_add.append("ADD COLUMN `predecessor_2` INT NULL")
            if 'successor' not in existing_columns:
                columns_to_add.append("ADD COLUMN `successor` INT NULL")
            if 'bracket_position' not in existing_columns:
                columns_to_add.append("ADD COLUMN `bracket_position` INT NULL")
            if 'round_number' not in existing_columns:
                columns_to_add.append("ADD COLUMN `round_number` INT NULL")
            
            if not columns_to_add:
                print("All columns already exist. Migration not needed.")
                return
            
            # Add columns
            alter_sql = f"ALTER TABLE `match` {', '.join(columns_to_add)}"
            print(f"Executing: {alter_sql}")
            db.session.execute(text(alter_sql))
            db.session.commit()
            
            # Add foreign key constraints if they don't exist
            result = db.session.execute(text("""
                SELECT CONSTRAINT_NAME 
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
                WHERE TABLE_SCHEMA = :db_name 
                AND TABLE_NAME = 'match' 
                AND CONSTRAINT_NAME IN ('match_predecessor_1_fk', 'match_predecessor_2_fk', 'match_successor_fk')
            """), {'db_name': Config.DB_NAME})
            
            existing_fks = {row[0] for row in result.fetchall()}
            
            if 'predecessor_1' not in existing_columns and 'match_predecessor_1_fk' not in existing_fks:
                print("Adding foreign key constraint: match_predecessor_1_fk")
                db.session.execute(text("""
                    ALTER TABLE `match`
                    ADD CONSTRAINT `match_predecessor_1_fk` 
                    FOREIGN KEY (`predecessor_1`) REFERENCES `match`(`id`) ON DELETE SET NULL
                """))
                db.session.commit()
            
            if 'predecessor_2' not in existing_columns and 'match_predecessor_2_fk' not in existing_fks:
                print("Adding foreign key constraint: match_predecessor_2_fk")
                db.session.execute(text("""
                    ALTER TABLE `match`
                    ADD CONSTRAINT `match_predecessor_2_fk` 
                    FOREIGN KEY (`predecessor_2`) REFERENCES `match`(`id`) ON DELETE SET NULL
                """))
                db.session.commit()
            
            if 'successor' not in existing_columns and 'match_successor_fk' not in existing_fks:
                print("Adding foreign key constraint: match_successor_fk")
                db.session.execute(text("""
                    ALTER TABLE `match`
                    ADD CONSTRAINT `match_successor_fk` 
                    FOREIGN KEY (`successor`) REFERENCES `match`(`id`) ON DELETE SET NULL
                """))
                db.session.commit()
            
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"Error running migration: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    run_migration()

