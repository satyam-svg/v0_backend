-- Migration to reset player2_uuid to NULL for a specific tournament

UPDATE team
SET player2_uuid = NULL
WHERE tournament_id = 15;  -- Replace 15 with the desired tournament_id 