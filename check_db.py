from app import app, db
from models import Team, Player, Match, Tournament

def check_data():
    with app.app_context():
        team_count = Team.query.count()
        player_count = Player.query.count()
        match_count = Match.query.count()
        tournament = Tournament.query.first()
        
        print(f"Teams: {team_count}")
        print(f"Players: {player_count}")
        print(f"Matches: {match_count}")
        if tournament:
            print(f"Tournament: {tournament.tournament_name} (ID: {tournament.id})")
        else:
            print("No tournament found.")

if __name__ == "__main__":
    check_data()
