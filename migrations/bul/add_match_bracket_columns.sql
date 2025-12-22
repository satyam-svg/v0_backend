-- Add missing bracket-related columns to match table
-- These columns are used for knockout tournament bracket tracking

ALTER TABLE `match`
ADD COLUMN `predecessor_1` INT NULL,
ADD COLUMN `predecessor_2` INT NULL,
ADD COLUMN `successor` INT NULL,
ADD COLUMN `bracket_position` INT NULL,
ADD COLUMN `round_number` INT NULL;

-- Add foreign key constraints for predecessor and successor matches
ALTER TABLE `match`
ADD CONSTRAINT `match_predecessor_1_fk` FOREIGN KEY (`predecessor_1`) REFERENCES `match`(`id`) ON DELETE SET NULL,
ADD CONSTRAINT `match_predecessor_2_fk` FOREIGN KEY (`predecessor_2`) REFERENCES `match`(`id`) ON DELETE SET NULL,
ADD CONSTRAINT `match_successor_fk` FOREIGN KEY (`successor`) REFERENCES `match`(`id`) ON DELETE SET NULL;

