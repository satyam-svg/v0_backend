from typing import List, Tuple, Dict
from itertools import chain

def get_pool_pairs(num_pools: int, pairing_type: str) -> List[Tuple[str, str]]:
    """
    Generate pool pairs based on the number of pools and pairing type.
    
    Args:
        num_pools (int): Number of pools (2, 4, or 8)
        pairing_type (str): Type of pairing ('same', 'near', 'half', 'far')
    
    Returns:
        List[Tuple[str, str]]: List of pool pairs (e.g., [('A1', 'A2'), ('B1', 'B2')])
    
    Raises:
        ValueError: If invalid num_pools or pairing_type is provided
    """
    if num_pools not in [2, 4, 8]:
        raise ValueError("Number of pools must be 2, 4, or 8")
    
    if pairing_type not in ['same', 'near', 'half', 'far']:
        raise ValueError("Pairing type must be 'same', 'near', 'half', or 'far'")
    
    # Generate pool names (A, B, C, etc.)
    pool_names = [chr(65 + i) for i in range(num_pools)]
    
    pairs = []
    
    if pairing_type == 'same':
        # Same pool pairing: A1 vs A2, B1 vs B2, etc.
        pairs = [(f"{pool}1", f"{pool}2") for pool in pool_names]
    
    elif pairing_type == 'near':
        # Near pool pairing: Adjacent pools (A with B, C with D, etc.)
        for i in range(0, num_pools, 2):
            pool1, pool2 = pool_names[i], pool_names[i + 1]
            pairs.extend([(f"{pool1}1", f"{pool2}2"), (f"{pool1}2", f"{pool2}1")])
    
    elif pairing_type == 'half':
        if num_pools == 2:
            # For 2 pools, half-pool is same as same-pool
            pairs = [(f"{pool}1", f"{pool}2") for pool in pool_names]
        else:
            # Half pool pairing: Pair pools with ones halfway across
            half = num_pools // 2
            for i in range(half):
                pool1, pool2 = pool_names[i], pool_names[i + half]
                pairs.extend([(f"{pool1}1", f"{pool2}2"), (f"{pool1}2", f"{pool2}1")])
    
    elif pairing_type == 'far':
        if num_pools == 2:
            # For 2 pools, far-pool is same as near-pool
            pairs = [('A1', 'B2'), ('A2', 'B1')]
        elif num_pools == 4:
            # For 4 pools: A vs D, B vs C
            pairs = [
                ('A1', 'D2'), ('A2', 'D1'),
                ('B1', 'C2'), ('B2', 'C1')
            ]
        else:  # 8 pools
            # For 8 pools: A vs H, B vs G, C vs F, D vs E
            pairs = [
                ('A1', 'H2'), ('A2', 'H1'),
                ('B1', 'G2'), ('B2', 'G1'),
                ('C1', 'F2'), ('C2', 'F1'),
                ('D1', 'E2'), ('D2', 'E1')
            ]
    
    return pairs

def assign_teams_to_pools(teams: List[str], num_pools: int) -> Dict[str, List[str]]:
    """
    Assign teams to pools evenly.
    
    Args:
        teams (List[str]): List of team names
        num_pools (int): Number of pools (2, 4, or 8)
    
    Returns:
        Dict[str, List[str]]: Dictionary mapping pool names to lists of teams
    
    Raises:
        ValueError: If number of teams cannot be evenly distributed
    """
    if num_pools not in [2, 4, 8]:
        raise ValueError("Number of pools must be 2, 4, or 8")
    
    if len(teams) % 2 != 0:
        raise ValueError("Number of teams must be even")
    
    if len(teams) < num_pools * 2:
        raise ValueError(f"Need at least {num_pools * 2} teams for {num_pools} pools")
    
    teams_per_pool = len(teams) // num_pools
    pool_names = [chr(65 + i) for i in range(num_pools)]
    
    pools = {}
    team_idx = 0
    
    for pool_name in pool_names:
        pools[pool_name] = teams[team_idx:team_idx + teams_per_pool]
        team_idx += teams_per_pool
    
    return pools
