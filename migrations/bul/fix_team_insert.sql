-- Fix team insertion with proper collation handling

INSERT INTO kc_prod2.team (
    team_id, name, points, tournament_id, checked_in, 
    player1_uuid, player2_uuid
)
SELECT 
    t.team_id, t.name, t.points, m.new_id, t.checked_in,
    CASE WHEN EXISTS (
        SELECT 1 FROM kc_prod2.player p 
        WHERE p.uuid COLLATE utf8mb4_unicode_ci = t.player1_uuid COLLATE utf8mb4_unicode_ci
    ) THEN t.player1_uuid ELSE NULL END,
    CASE WHEN EXISTS (
        SELECT 1 FROM kc_prod2.player p 
        WHERE p.uuid COLLATE utf8mb4_unicode_ci = t.player2_uuid COLLATE utf8mb4_unicode_ci
    ) THEN t.player2_uuid ELSE NULL END
FROM kc_dev_dump.team t
JOIN kc_prod2.id_map_tournament m ON t.tournament_id = m.old_id; 