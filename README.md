# Scoring System Architecture & Mechanism

## Overview
The scoring system is designed to handle real-time score updates, match finalization, and automatic bracket progression. It uses a REST API for updates and WebSockets (Socket.IO) for real-time broadcasting to connected clients (scoreboards/displays).

## Architecture

The system follows a standard MVC pattern with an additional real-time layer:

1.  **Client Layer**: Sends score updates via HTTP POST and listens for updates via WebSocket.
2.  **API Layer (Flask)**: Processes the request, validates data, and updates the database.
3.  **Database Layer (SQLAlchemy)**: Persists match states and scores.
4.  **Real-time Layer (Socket.IO)**: Broadcasts the new state to all subscribers.

## Data Flow

1.  **Input**: Client sends `POST /update-score` with `match_id` and `score` (e.g., "11-9").
2.  **Validation**: Server checks if match exists and parses the score format.
3.  **Persistence**:
    *   Updates or Creates `Score` records for both teams.
    *   If `final=True`, determines the winner and updates `Match` status.
4.  **Progression**: If the match is part of a bracket (has a `successor`), the winner is automatically advanced to the next match.
5.  **Broadcast**: Server emits `score_update` event with the new state.

## Database Schema (Key Tables)

| Table | Key Fields | Description |
| :--- | :--- | :--- |
| **Match** | `id`, `team1_id`, `team2_id`, `winner_team_id`, `is_final`, `successor` | Represents a single match. Links to teams and the next match in the bracket. |
| **Score** | `match_id`, `team_id`, `score` | Stores the numeric score for a specific team in a specific match. |
| **Team** | `team_id`, `name`, `pool` | Represents a competing pair/team. |

## API Specification

### Update Score
**Endpoint**: `POST /score/update-score`

**Payload**:
```json
{
  "match_id": "1",
  "score": "11-9",
  "tournament_id": "1",
  "final": true,
  "outcome": "normal" // Optional: "normal", "walkover"
}
```

**Logic**:
1.  **Parsing**: Splits score string ("11-9") -> Team 1: 11, Team 2: 9.
2.  **Recording**: Updates `Score` table for both teams.
3.  **Finalization** (if `final: true`):
    *   Compares scores to set `winner_team_id`.
    *   Sets `match.is_final = True`.
    *   **Walkover Handling**: If `outcome` is "walkover", explicitly sets winner from `winner_team_id` in payload.
    *   **Progression**: Triggers `update_successor_match` to propagate winner.

## Bracket Progression Logic
When a match is finalized:
1.  System checks `match.successor` (ID of the next match).
2.  It identifies if the current match is `predecessor_1` or `predecessor_2` of the successor.
3.  Updates the corresponding `team_id` slot in the successor match.
4.  Initializes 0-0 scores for the new matchup in the successor.

## Real-time Events
**Event**: `score_update`
**Namespace**: `/scores`
**Payload**:
```json
{
  "match_id": "1",
  "team1_score": 11,
  "team2_score": 9,
  "is_final": true,
  ...
}
```
