from app import app, db
from models import Team, Match, Tournament, Round
import itertools

def generate_matches():
    with app.app_context():
        tournament = Tournament.query.first()
        if not tournament:
            print("No tournament found.")
            return

        teams = Team.query.filter_by(tournament_id=tournament.id).all()
        
        # Group teams by pool
        pools = {}
        for team in teams:
            if team.pool:
                if team.pool not in pools:
                    pools[team.pool] = []
                pools[team.pool].append(team)
        
        print(f"Found {len(pools)} pools: {list(pools.keys())}")

        match_count = 0
        for pool_name, pool_teams in pools.items():
            # Generate Round Robin matches
            # Combinations of 2 teams
            matchups = list(itertools.combinations(pool_teams, 2))
            
            for i, (team1, team2) in enumerate(matchups):
                match = Match(
                    match_name=f"{pool_name} Match {i+1}",
                    team1_id=team1.team_id,
                    team2_id=team2.team_id,
                    round_id=f"RR-{pool_name}", # Round Robin
                    pool=pool_name,
                    tournament_id=tournament.id,
                    status='pending',
                    court_number=1, # Dummy
                    court_order=i+1
                )
                db.session.add(match)
                match_count += 1
        
        db.session.commit()
        print(f"Generated {match_count} matches.")

if __name__ == "__main__":
    generate_matches()
