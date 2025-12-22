-- Migration script to move data from kc_dev_dump to kc_prod2
-- For super_tournament_id = 73 and all related data

-- First create all required tables in kc_prod2
CREATE TABLE kc_prod2.super_tournament (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE kc_prod2.season (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    super_tournament_id INT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (super_tournament_id) REFERENCES super_tournament(id)
);

CREATE TABLE kc_prod2.tournament (
    id INT NOT NULL AUTO_INCREMENT,
    tournament_name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    num_courts INT DEFAULT 1,
    divisions JSON,
    season_id INT,
    PRIMARY KEY (id),
    FOREIGN KEY (season_id) REFERENCES season(id)
);

CREATE TABLE kc_prod2.player (
    id INT NOT NULL AUTO_INCREMENT,
    uuid VARCHAR(36) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50),
    gender VARCHAR(10) NOT NULL,
    age INT NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    email VARCHAR(120) NOT NULL,
    skill_type VARCHAR(20) NOT NULL,
    dupr_id VARCHAR(50),
    checked_in TINYINT(1) DEFAULT 0,
    super_tournament_id INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY (uuid),
    INDEX (phone_number),
    FOREIGN KEY (super_tournament_id) REFERENCES super_tournament(id)
);

-- Create team table without foreign key constraints initially
CREATE TABLE kc_prod2.team (
    team_id VARCHAR(50) NOT NULL,
    name VARCHAR(100),
    points INT NOT NULL,
    tournament_id INT NOT NULL,
    checked_in TINYINT(1) NOT NULL,
    player1_uuid VARCHAR(36),
    player2_uuid VARCHAR(36),
    PRIMARY KEY (team_id)
);

CREATE TABLE kc_prod2.match (
    id INT NOT NULL AUTO_INCREMENT,
    match_name VARCHAR(50) NOT NULL,
    team1_id VARCHAR(50),
    team2_id VARCHAR(50),
    round_id VARCHAR(50) NOT NULL,
    pool VARCHAR(50),
    winner_team_id VARCHAR(50),
    is_final TINYINT(1) NOT NULL,
    tournament_id INT NOT NULL,
    court_number INT,
    court_order INT,
    status VARCHAR(20) DEFAULT 'pending',
    PRIMARY KEY (id),
    FOREIGN KEY (tournament_id) REFERENCES tournament(id),
    INDEX (court_number)
);

CREATE TABLE kc_prod2.score (
    id INT NOT NULL AUTO_INCREMENT,
    match_id VARCHAR(50) NOT NULL,
    team_id VARCHAR(50),
    score INT NOT NULL,
    points INT NOT NULL,
    tournament_id INT NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE kc_prod2.round (
    id INT NOT NULL AUTO_INCREMENT,
    round_id INT NOT NULL,
    team_id VARCHAR(50),
    pool VARCHAR(20),
    tournament_id INT NOT NULL,
    name VARCHAR(250),
    PRIMARY KEY (id)
);

-- Create temporary tables to store ID mappings
CREATE TABLE kc_prod2.id_map_super_tournament (old_id INT, new_id INT);
CREATE TABLE kc_prod2.id_map_season (old_id INT, new_id INT);
CREATE TABLE kc_prod2.id_map_tournament (old_id INT, new_id INT);
CREATE TABLE kc_prod2.id_map_match (old_id INT, new_id INT);

-- Step 1: Copy super_tournament
INSERT INTO kc_prod2.super_tournament (name, description)
SELECT name, description
FROM kc_dev_dump.super_tournament
WHERE id = 73;

-- Store the mapping
INSERT INTO kc_prod2.id_map_super_tournament 
SELECT 73, LAST_INSERT_ID();

-- Step 2: Copy players (keeping existing UUIDs)
INSERT INTO kc_prod2.player (
    uuid, first_name, last_name, gender, age, phone_number, 
    email, skill_type, dupr_id, checked_in, super_tournament_id
)
SELECT 
    p.uuid, p.first_name, p.last_name, p.gender, p.age, p.phone_number,
    p.email, p.skill_type, p.dupr_id, p.checked_in, m.new_id
FROM kc_dev_dump.player p
JOIN kc_prod2.id_map_super_tournament m
WHERE p.super_tournament_id = 73;

-- Step 3: Copy seasons
INSERT INTO kc_prod2.season (name, super_tournament_id)
SELECT s.name, m.new_id
FROM kc_dev_dump.season s
JOIN kc_prod2.id_map_super_tournament m
WHERE s.super_tournament_id = 73;

-- Store season mappings
INSERT INTO kc_prod2.id_map_season
SELECT s.id, LAST_INSERT_ID() + ROW_NUMBER() OVER () - 1
FROM kc_dev_dump.season s
WHERE s.super_tournament_id = 73;

-- Step 4: Copy tournaments
INSERT INTO kc_prod2.tournament (tournament_name, type, num_courts, divisions, season_id)
SELECT 
    t.tournament_name, t.type, t.num_courts, t.divisions, m.new_id
FROM kc_dev_dump.tournament t
JOIN kc_dev_dump.season s ON t.season_id = s.id
JOIN kc_prod2.id_map_season m ON s.id = m.old_id
WHERE s.super_tournament_id = 73;

-- Store tournament mappings
INSERT INTO kc_prod2.id_map_tournament
SELECT t.id, LAST_INSERT_ID() + ROW_NUMBER() OVER () - 1
FROM kc_dev_dump.tournament t
JOIN kc_dev_dump.season s ON t.season_id = s.id
WHERE s.super_tournament_id = 73;

-- Step 5: Copy teams (keeping existing team_ids)
INSERT INTO kc_prod2.team (
    team_id, name, points, tournament_id, checked_in, 
    player1_uuid, player2_uuid
)
SELECT 
    t.team_id, t.name, t.points, m.new_id, t.checked_in,
    CASE WHEN EXISTS (SELECT 1 FROM kc_prod2.player p WHERE p.uuid = t.player1_uuid) THEN t.player1_uuid ELSE NULL END,
    CASE WHEN EXISTS (SELECT 1 FROM kc_prod2.player p WHERE p.uuid = t.player2_uuid) THEN t.player2_uuid ELSE NULL END
FROM kc_dev_dump.team t
JOIN kc_prod2.id_map_tournament m ON t.tournament_id = m.old_id;

-- Step 6: Copy matches
INSERT INTO kc_prod2.match (
    match_name, team1_id, team2_id, round_id, pool,
    winner_team_id, is_final, tournament_id, court_number,
    court_order, status
)
SELECT 
    m.match_name, m.team1_id, m.team2_id, m.round_id, m.pool,
    m.winner_team_id, m.is_final, tm.new_id, m.court_number,
    m.court_order, m.status
FROM kc_dev_dump.match m
JOIN kc_prod2.id_map_tournament tm ON m.tournament_id = tm.old_id;

-- Store match mappings
INSERT INTO kc_prod2.id_map_match
SELECT m.id, LAST_INSERT_ID() + ROW_NUMBER() OVER () - 1
FROM kc_dev_dump.match m
JOIN kc_prod2.id_map_tournament tm ON m.tournament_id = tm.old_id;

-- Step 7: Copy scores
INSERT INTO kc_prod2.score (
    match_id, team_id, score, points, tournament_id
)
SELECT 
    CAST(mm.new_id AS CHAR), s.team_id, s.score, s.points, tm.new_id
FROM kc_dev_dump.score s
JOIN kc_prod2.id_map_match mm ON CAST(s.match_id AS SIGNED) = mm.old_id
JOIN kc_prod2.id_map_tournament tm ON s.tournament_id = tm.old_id;

-- Step 8: Copy rounds
INSERT INTO kc_prod2.round (
    round_id, team_id, pool, tournament_id, name
)
SELECT 
    r.round_id, r.team_id, r.pool, m.new_id, r.name
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
