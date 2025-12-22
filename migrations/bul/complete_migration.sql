-- Step 6: Copy matches with collation fix
INSERT INTO kc_prod2.match (
    match_name, team1_id, team2_id, round_id, pool,
    winner_team_id, is_final, tournament_id, court_number,
    court_order, status
)
SELECT 
    m.match_name, 
    CASE WHEN EXISTS (
        SELECT 1 FROM kc_prod2.team t 
        WHERE t.team_id COLLATE utf8mb4_unicode_ci = m.team1_id COLLATE utf8mb4_unicode_ci
    ) THEN m.team1_id ELSE NULL END,
    CASE WHEN EXISTS (
        SELECT 1 FROM kc_prod2.team t 
        WHERE t.team_id COLLATE utf8mb4_unicode_ci = m.team2_id COLLATE utf8mb4_unicode_ci
    ) THEN m.team2_id ELSE NULL END,
    m.round_id, 
    m.pool,
    CASE WHEN EXISTS (
        SELECT 1 FROM kc_prod2.team t 
        WHERE t.team_id COLLATE utf8mb4_unicode_ci = m.winner_team_id COLLATE utf8mb4_unicode_ci
    ) THEN m.winner_team_id ELSE NULL END,
    m.is_final, 
    tm.new_id, 
    m.court_number,
    m.court_order, 
    m.status
FROM kc_dev_dump.match m
JOIN kc_prod2.id_map_tournament tm ON m.tournament_id = tm.old_id;

-- Store match mappings
INSERT INTO kc_prod2.id_map_match
SELECT m.id, LAST_INSERT_ID() + ROW_NUMBER() OVER () - 1
FROM kc_dev_dump.match m
JOIN kc_prod2.id_map_tournament tm ON m.tournament_id = tm.old_id;

-- Step 7: Copy scores with collation fix
INSERT INTO kc_prod2.score (
    match_id, team_id, score, points, tournament_id
)
SELECT 
    CAST(mm.new_id AS CHAR),
    CASE WHEN EXISTS (
        SELECT 1 FROM kc_prod2.team t 
        WHERE t.team_id COLLATE utf8mb4_unicode_ci = s.team_id COLLATE utf8mb4_unicode_ci
    ) THEN s.team_id ELSE NULL END,
    s.score, 
    s.points, 
    tm.new_id
FROM kc_dev_dump.score s
JOIN kc_prod2.id_map_match mm ON CAST(s.match_id AS SIGNED) = mm.old_id
JOIN kc_prod2.id_map_tournament tm ON s.tournament_id = tm.old_id;

-- Step 8: Copy rounds with collation fix
INSERT INTO kc_prod2.round (
    round_id, team_id, pool, tournament_id, name
)
SELECT 
    r.round_id,
    CASE WHEN EXISTS (
        SELECT 1 FROM kc_prod2.team t 
        WHERE t.team_id COLLATE utf8mb4_unicode_ci = r.team_id COLLATE utf8mb4_unicode_ci
    ) THEN r.team_id ELSE NULL END,
    r.pool, 
    m.new_id, 
    r.name
FROM kc_dev_dump.round r
JOIN kc_prod2.id_map_tournament m ON r.tournament_id = m.old_id;

-- Now add foreign key constraints to team table
ALTER TABLE kc_prod2.team
ADD CONSTRAINT team_tournament_fk FOREIGN KEY (tournament_id) REFERENCES tournament(id),
ADD CONSTRAINT team_player1_fk FOREIGN KEY (player1_uuid) REFERENCES player(uuid),
ADD CONSTRAINT team_player2_fk FOREIGN KEY (player2_uuid) REFERENCES player(uuid);

-- Clean up temporary mapping tables
DROP TABLE kc_prod2.id_map_super_tournament;
DROP TABLE kc_prod2.id_map_season;
DROP TABLE kc_prod2.id_map_tournament;
DROP TABLE kc_prod2.id_map_match; 