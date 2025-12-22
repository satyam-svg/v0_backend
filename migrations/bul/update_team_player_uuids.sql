-- Migration to update team player UUIDs based on player_s data
-- For tournament_id = 15

-- Update player1_uuid
UPDATE team t
JOIN (
    SELECT ps.team_id, p.uuid
    FROM player_s ps
    JOIN player p ON p.first_name = ps.first_name 
        AND p.super_tournament_id = 73
    WHERE ps.tournament_id = 15
    AND ps.id = (
        SELECT MIN(id)
        FROM player_s
        WHERE team_id = ps.team_id
        AND tournament_id = 15
    )
) player1_data ON t.team_id = CONCAT(player1_data.team_id, '_15')
SET t.player1_uuid = player1_data.uuid
WHERE t.tournament_id = 15;

-- Update player2_uuid
UPDATE team t
JOIN (
    SELECT ps.team_id, p.uuid
    FROM player_s ps
    JOIN player p ON p.first_name = ps.first_name 
        AND p.super_tournament_id = 73
    WHERE ps.tournament_id = 15
    AND ps.id > (
        SELECT MIN(id)
        FROM player_s
        WHERE team_id = ps.team_id
        AND tournament_id = 15
    )
) player2_data ON t.team_id = CONCAT(player2_data.team_id, '_15')
SET t.player2_uuid = player2_data.uuid
WHERE t.tournament_id = 15; 