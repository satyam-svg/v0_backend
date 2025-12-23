import csv
import uuid
from app import app, db
from models import SuperTournament, Season, Tournament, Team, Player, SkillType

def init_db():
    with app.app_context():
        # Create tables
        db.create_all()
        print("Tables created.")

        # Check if data already exists to avoid duplicates
        if SuperTournament.query.first():
            print("Database already initialized.")
            return

        # Create dummy hierarchy
        super_tournament = SuperTournament(name="Default Super Tournament", description="Main Super Tournament")
        db.session.add(super_tournament)
        db.session.flush()

        season = Season(name="Season 1", super_tournament_id=super_tournament.id)
        db.session.add(season)
        db.session.flush()

        tournament = Tournament(
            tournament_name="Default Tournament",
            type="doubles",
            season_id=season.id,
            num_courts=4
        )
        db.session.add(tournament)
        db.session.flush()
        
        print(f"Created hierarchy: ST={super_tournament.id}, Season={season.id}, Tournament={tournament.id}")

        # Read Pools
        pools = {}
        try:
            with open('sample_pools.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pools[row['Team ID']] = row['Pool']
            print(f"Loaded {len(pools)} pool assignments.")
        except FileNotFoundError:
            print("sample_pools.csv not found. Skipping pool assignments.")

        # Read Teams and Players
        try:
            with open('sample_teams.csv', 'r') as f:
                reader = csv.DictReader(f)
                
                teams_map = {} # team_id -> Team object

                for row in reader:
                    team_id = row['Team ID']
                    team_name = row['Team Name']
                    
                    # Create Player
                    player_uuid = str(uuid.uuid4())
                    
                    # Handle empty fields gracefully
                    skill = row.get('Skill Type', 'INTERMEDIATE').upper()
                    try:
                        SkillType(skill.lower()) # Validate
                    except ValueError:
                        skill = 'INTERMEDIATE'

                    player = Player(
                        uuid=player_uuid,
                        first_name=row['Name of Player'].split(' ')[0] if row['Name of Player'] else 'Unknown',
                        last_name=' '.join(row['Name of Player'].split(' ')[1:]) if row['Name of Player'] and ' ' in row['Name of Player'] else '',
                        gender=row.get('Gender', 'Unknown'),
                        age=int(row['Age']) if row.get('Age') and row['Age'].isdigit() else 0,
                        phone_number=row.get('Phone Number', '0000000000'),
                        email=row.get('Email', f'user_{player_uuid}@example.com'),
                        skill_type=skill.lower(),
                        dupr_id=row.get('DUPR ID'),
                        super_tournament_id=super_tournament.id
                    )
                    db.session.add(player)
                    db.session.flush()

                    # Create or Update Team
                    if team_id not in teams_map:
                        team = Team(
                            team_id=team_id,
                            name=team_name if team_name else f"Team {team_id}",
                            tournament_id=tournament.id,
                            pool=pools.get(team_id)
                        )
                        teams_map[team_id] = team
                        db.session.add(team)
                    
                    team = teams_map[team_id]
                    
                    # Assign player to team
                    if not team.player1_uuid:
                        team.player1_uuid = player.uuid
                    elif not team.player2_uuid:
                        team.player2_uuid = player.uuid
                    
            print(f"Processed teams and players.")
            db.session.commit()
            print("Database populated successfully!")

        except FileNotFoundError:
            print("sample_teams.csv not found. Skipping team import.")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {e}")

if __name__ == '__main__':
    init_db()
