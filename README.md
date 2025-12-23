# Project Documentation

## Table of Contents
1. [How the current scoring mechanism works](#how-the-current-scoring-mechanism-works)
2. [What changes you made and why](#what-changes-you-made-and-why)

---

## How the current scoring mechanism works

### Overview
The scoring system is designed to handle real-time score updates, match finalization, and automatic bracket progression. It uses a REST API for updates and WebSockets (Socket.IO) for real-time broadcasting to connected clients (scoreboards/displays).

### Architecture
The system follows a standard MVC pattern with an additional real-time layer:
1.  **Client Layer**: Sends score updates via HTTP POST and listens for updates via WebSocket.
2.  **API Layer (Flask)**: Processes the request, validates data, and updates the database.
3.  **Database Layer (SQLAlchemy)**: Persists match states and scores.
4.  **Real-time Layer (Socket.IO)**: Broadcasts the new state to all subscribers.

### Data Flow
1.  **Input**: Client sends `POST /update-score` with `match_id` and `score` (e.g., "11-9").
2.  **Validation**: Server checks if match exists and parses the score format.
3.  **Persistence**:
    *   Updates or Creates `Score` records for both teams.
    *   If `final=True`, determines the winner and updates `Match` status.
4.  **Progression**: If the match is part of a bracket (has a `successor`), the winner is automatically advanced to the next match.
5.  **Broadcast**: Server emits `score_update` event with the new state.

### Database Schema (Key Tables)
| Table | Key Fields | Description |
| :--- | :--- | :--- |
| **Match** | `id`, `team1_id`, `team2_id`, `winner_team_id`, `is_final`, `successor` | Represents a single match. Links to teams and the next match in the bracket. |
| **Score** | `match_id`, `team_id`, `score` | Stores the numeric score for a specific team in a specific match. |
| **Team** | `team_id`, `name`, `pool` | Represents a competing pair/team. |

### API Specification: Update Score
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

### Bracket Progression Logic
When a match is finalized:
1.  System checks `match.successor` (ID of the next match).
2.  It identifies if the current match is `predecessor_1` or `predecessor_2` of the successor.
3.  Updates the corresponding `team_id` slot in the successor match.
4.  Initializes 0-0 scores for the new matchup in the successor.

### Real-time Events
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

---

## What changes you made and why

### 1. Introduction of Enums in `models.py`
**Change**: Added `MatchOutcome`, `MatchType`, and `SkillType` as Python Enum classes.
**Why**: 
*   **Data Integrity**: Using Enums prevents invalid strings (like "WalkOver" vs "walkover") from entering the database.
*   **Code Readability**: It makes the code self-documenting. Instead of checking for magic strings like `'normal'`, we check `MatchOutcome.NORMAL`.
*   **Scalability**: It's easier to add new types (e.g., a new `SkillType`) in one central place.

### 2. Implementation of Walkover Logic
**Change**: Added specific handling for `outcome="walkover"` in the `update_score` function.
**Why**:
*   **Real-world Scenarios**: Tournaments often have no-shows. The system needed a way to advance a winner without requiring a played match score (e.g., 11-0 is not always accurate for a walkover).
*   **Mechanism**:
    *   When a walkover is reported, we bypass the score comparison logic.
    *   We explicitly trust the `winner_team_id` sent by the client.
    *   We mark the match as `completed` and `outcome='walkover'`.
    *   Crucially, we still trigger `update_successor_match`, ensuring the bracket doesn't break and the winner moves to the next round automatically.
