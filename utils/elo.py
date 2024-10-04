# utils/elo.py

def calculate_new_ratings(player_rating, opponent_rating, player_score, opponent_score):
    """
    Implements a simplified Glicko-2 rating calculation.
    For full Glicko-2, consider using an existing library or implementing the full algorithm.
    """
    # Placeholder implementation using basic ELO formula
    k_factor = 32  # Adjust as needed
    expected_score = 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))
    new_player_rating = player_rating + k_factor * (player_score - expected_score)

    expected_score_opponent = 1 - expected_score
    new_opponent_rating = opponent_rating + k_factor * (opponent_score - expected_score_opponent)

    return int(new_player_rating), int(new_opponent_rating)
