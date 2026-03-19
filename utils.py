def estimate_latency(distance_m: float, medium: str = 'copper') -> float:
    speed_of_light = 3.00e8  # m/s

    medium_speed = {
        'vacuum': speed_of_light,
        'air': speed_of_light,
        'optical_fiber': speed_of_light * 0.68,
        'fiber': speed_of_light * 0.68,
        'copper': speed_of_light * 0.64,
    }

    if medium.lower() not in medium_speed:
        valid = ', '.join(medium_speed.keys())
        raise ValueError(f"Unsupported medium: {medium}. Choose from: {valid}")

    propagation_speed = medium_speed[medium.lower()]
    latency = distance_m / propagation_speed

    return latency
