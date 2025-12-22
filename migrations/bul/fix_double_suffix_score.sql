-- Migration to fix double '_3_3' suffix in team_ids
-- For match_ids between 56 and 79

UPDATE kc_dev_dump.score
SET team_id = SUBSTRING(team_id, 1, LENGTH(team_id) - 2)
WHERE CAST(match_id AS SIGNED) BETWEEN 56 AND 79
AND team_id LIKE '%_3_3'; 