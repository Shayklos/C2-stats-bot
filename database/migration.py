"""
Migration utilities to convert data from fullCultris.db to cultris2.db format.
Converts old Matches/Rounds data into the format expected by the new API endpoints.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def get_old_database_path() -> Path:
    """Get the path to the old fullCultris.db database."""
    return Path(__file__).parent.parent / "files" / "fullCultris.db"


def convert_rounds_to_api_format(db_path: Path = None) -> List[Dict[str, Any]]:
    """
    Convert Matches and Rounds from fullCultris.db into the API response format.
    
    This matches the format returned by Endpoint.rounds(id), combining match metadata
    with player data into a single nested structure.
    
    Args:
        db_path: Path to fullCultris.db. Defaults to files/fullCultris.db
        
    Returns:
        List of round dictionaries in API format:
        [
            {
                "roundId": int,
                "start": str (ISO format),
                "ruleset": int,
                "speedLimit": int,
                "isOfficial": bool,
                "players": [
                    {
                        "userId": int or None,
                        "guestName": str or None,
                        "linesGot": int,
                        "linesSent": int,
                        "linesBlocked": int,
                        "blocks": int,
                        "maxCombo": int,
                        "playDuration": float,
                        "team": int or None,
                        "cheeseRows": int
                    },
                    ...
                ]
            },
            ...
        ]
    """
    if db_path is None:
        db_path = get_old_database_path()
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all matches
        cursor.execute("SELECT * FROM Matches ORDER BY roundId")
        matches = cursor.fetchall()
        
        rounds_data = []
        
        for match in matches:
            round_id = match['roundId']
            
            # Get all players for this round
            cursor.execute(
                """
                SELECT userId, guestName, linesGot, linesSent, linesBlocked, 
                       blocks, maxCombo, playDuration, team, cheeseRows
                FROM Rounds
                WHERE roundId = ?
                ORDER BY place ASC
                """,
                (round_id,)
            )
            players = cursor.fetchall()
            
            # Convert start time to ISO format if it's a string, handle None
            start_time = match['start']
            if start_time:
                try:
                    # Try to parse if it's a datetime string
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    iso_start = dt.isoformat().replace('+00:00', 'Z')
                except (ValueError, AttributeError):
                    # If parsing fails, try parsing as different format
                    try:
                        dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                        iso_start = dt.isoformat() + 'Z'
                    except:
                        iso_start = start_time
            else:
                iso_start = None
            
            # Build the round dictionary
            round_dict = {
                "roundId": round_id,
                "start": iso_start,
                "ruleset": match['ruleset'],
                "speedLimit": match['speedLimit'],
                "isOfficial": bool(match['isOfficial']),
                "roomsize": len(players),
                "players": [
                    {
                        "userId": player['userId'],
                        "guestName": player['guestName'],
                        "linesGot": player['linesGot'],
                        "linesSent": player['linesSent'],
                        "linesBlocked": player['linesBlocked'],
                        "blocks": player['blocks'],
                        "maxCombo": player['maxCombo'],
                        "playDuration": player['playDuration'],
                        "team": player['team'],
                        "cheeseRows": player['cheeseRows']
                    }
                    for player in players
                ]
            }
            
            rounds_data.append(round_dict)
        
        conn.close()
        return rounds_data
        
    except sqlite3.Error as e:
        raise Exception(f"Database error while converting rounds: {e}")


def convert_single_round(round_id: int, db_path: Path = None) -> Dict[str, Any]:
    """
    Convert a single round from fullCultris.db into the API response format.
    
    Args:
        round_id: The roundId to convert
        db_path: Path to fullCultris.db. Defaults to files/fullCultris.db
        
    Returns:
        Single round dictionary in API format
    """
    if db_path is None:
        db_path = get_old_database_path()
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get the match
        cursor.execute("SELECT * FROM Matches WHERE roundId = ?", (round_id,))
        match = cursor.fetchone()
        
        if not match:
            conn.close()
            raise ValueError(f"Round {round_id} not found in database")
        
        # Get all players for this round
        cursor.execute(
            """
            SELECT userId, guestName, linesGot, linesSent, linesBlocked, 
                   blocks, maxCombo, playDuration, team, cheeseRows
            FROM Rounds
            WHERE roundId = ?
            ORDER BY place ASC
            """,
            (round_id,)
        )
        players = cursor.fetchall()
        
        # Convert start time to ISO format
        start_time = match['start']
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                iso_start = dt.isoformat().replace('+00:00', 'Z')
            except (ValueError, AttributeError):
                try:
                    dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    iso_start = dt.isoformat() + 'Z'
                except:
                    iso_start = start_time
        else:
            iso_start = None
        
        # Build the round dictionary
        round_dict = {
            "roundId": round_id,
            "start": iso_start,
            "ruleset": match['ruleset'],
            "speedLimit": match['speedLimit'],
            "isOfficial": bool(match['isOfficial']),
            "roomsize": len(players),
            "players": [
                {
                    "userId": player['userId'],
                    "guestName": player['guestName'],
                    "linesGot": player['linesGot'],
                    "linesSent": player['linesSent'],
                    "linesBlocked": player['linesBlocked'],
                    "blocks": player['blocks'],
                    "maxCombo": player['maxCombo'],
                    "playDuration": player['playDuration'],
                    "team": player['team'],
                    "cheeseRows": player['cheeseRows']
                }
                for player in players
            ]
        }
        
        conn.close()
        return round_dict
        
    except sqlite3.Error as e:
        raise Exception(f"Database error while converting single round: {e}")


def convert_rounds_range(start_round: int, end_round: int, db_path: Path = None) -> List[Dict[str, Any]]:
    """
    Convert a range of rounds from fullCultris.db into the API response format.
    
    This is more efficient than converting all rounds when dealing with large datasets.
    Rounds are fetched and converted in order by roundId.
    
    Args:
        start_round: The starting roundId (inclusive)
        end_round: The ending roundId (inclusive)
        db_path: Path to fullCultris.db. Defaults to files/fullCultris.db
        
    Returns:
        List of round dictionaries in API format (same format as convert_rounds_to_api_format)
    """
    if db_path is None:
        db_path = get_old_database_path()
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    if start_round > end_round:
        raise ValueError(f"start_round ({start_round}) cannot be greater than end_round ({end_round})")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get matches within the range
        cursor.execute(
            "SELECT * FROM Matches WHERE roundId BETWEEN ? AND ? ORDER BY roundId",
            (start_round, end_round)
        )
        matches = cursor.fetchall()
        
        rounds_data = []
        
        for match in matches:
            round_id = match['roundId']
            
            # Get all players for this round
            cursor.execute(
                """
                SELECT userId, guestName, linesGot, linesSent, linesBlocked, 
                       blocks, maxCombo, playDuration, team, cheeseRows
                FROM Rounds
                WHERE roundId = ?
                ORDER BY place ASC
                """,
                (round_id,)
            )
            players = cursor.fetchall()
            
            # Convert start time to ISO format if it's a string, handle None
            start_time = match['start']
            if start_time:
                try:
                    # Try to parse if it's a datetime string
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    iso_start = dt.isoformat().replace('+00:00', 'Z')
                except (ValueError, AttributeError):
                    # If parsing fails, try parsing as different format
                    try:
                        dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                        iso_start = dt.isoformat() + 'Z'
                    except:
                        iso_start = start_time
            else:
                iso_start = None
            
            # Build the round dictionary
            round_dict = {
                "roundId": round_id,
                "start": iso_start,
                "ruleset": match['ruleset'],
                "speedLimit": match['speedLimit'],
                "isOfficial": match['isOfficial'],
                "roomsize": len(players),
                "players": [
                    {
                        "userId": player['userId'],
                        "guestName": player['guestName'],
                        "linesGot": player['linesGot'],
                        "linesSent": player['linesSent'],
                        "linesBlocked": player['linesBlocked'],
                        "blocks": player['blocks'],
                        "maxCombo": player['maxCombo'],
                        "playDuration": player['playDuration'],
                        "team": player['team'],
                        "cheeseRows": player['cheeseRows']
                    }
                    for player in players
                ]
            }
            
            rounds_data.append(round_dict)
        
        conn.close()
        return rounds_data
        
    except sqlite3.Error as e:
        raise Exception(f"Database error while converting round range: {e}")


if __name__ == "__main__":
    # Test: Convert all rounds from old database
    try:
        print("Converting rounds from fullCultris.db...")
        # rounds = convert_rounds_to_api_format()
        print(convert_rounds_range(3237231, 3237231 + 100000))
        # print(f"Successfully converted {len(rounds)} rounds")
        
        # Show first round as example
        # if rounds:
        #     import json
        #     print("\nFirst round example:")
        #     print(json.dumps(rounds[0], indent=2))
            
    except Exception as e:
        print(f"Error: {e}")

