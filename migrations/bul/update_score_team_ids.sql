-- Migration to update team_ids in score table by appending '_3'
-- For match_ids between 56 and 79

UPDATE kc_dev_dump.score
SET team_id = CONCAT(team_id, '_3')
WHERE CAST(match_id AS SIGNED) BETWEEN 56 AND 79; 
