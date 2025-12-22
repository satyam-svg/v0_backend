-- Migration to copy matches from kc_prod to kc_dev_dump with modified team IDs
-- Copy matches with IDs 56-79 and append '_3' to team IDs

INSERT INTO kc_dev_dump.match (
    id,
    match_name,
    team1_id,
    team2_id,
    round_id,
    pool,
    winner_team_id,
    is_final,
    tournament_id,
    court_number,
    court_order,
    status
)
SELECT 
    m.id,
    m.match_name,
    CONCAT(m.team1_id, '_3') as team1_id,
    CONCAT(m.team2_id, '_3') as team2_id,
    m.round_id,
    m.pool,
    CASE 
        WHEN m.winner_team_id IS NOT NULL THEN CONCAT(m.winner_team_id, '_3')
        ELSE NULL
    END as winner_team_id,
    m.is_final,
    m.tournament_id,
    NULL as court_number,
    NULL as court_order,
    'pending' as status
FROM kc_prod.match m
WHERE m.id BETWEEN 56 AND 79
AND m.tournament_id = 3;
