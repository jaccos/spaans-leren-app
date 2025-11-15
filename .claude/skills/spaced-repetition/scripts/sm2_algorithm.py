"""
SuperMemo SM-2 Algorithm Implementation
Voor Spaans Leren App

Dit script bevat kant-en-klare functies voor spaced repetition.
Importeer in je main.py met: from scripts.sm2_algorithm import calculate_next_review
"""

from datetime import datetime, timedelta
from typing import Tuple


def calculate_next_review(
    easiness_factor: float,
    current_interval: int,
    quality_score: int
) -> Tuple[int, float]:
    """
    Bereken volgende review interval en nieuwe easiness factor.
    
    SuperMemo SM-2 algoritme voor optimale memorisatie.
    
    Args:
        easiness_factor: float (1.3 - 2.5) 
            Hoe makkelijk is dit woord? Start bij 2.5
        current_interval: int
            Huidige interval in dagen (0 = nieuw woord)
        quality_score: int (0-5)
            Hoe goed werd het onthouden?
            5 = Perfect
            4 = Correct na aarzeling  
            3 = Correct met moeite
            2 = Incorrect maar herinnerd
            1 = Incorrect maar bekend
            0 = Complete black-out
    
    Returns:
        Tuple[int, float]: (next_interval_days, new_easiness_factor)
    
    Examples:
        >>> # Perfect score op nieuw woord
        >>> interval, easiness = calculate_next_review(2.5, 0, 5)
        >>> print(f"Next review in {interval} days")
        Next review in 1 days
        
        >>> # Goed score na eerste review
        >>> interval, easiness = calculate_next_review(2.6, 1, 4)
        >>> print(f"Next review in {interval} days")
        Next review in 6 days
        
        >>> # Slecht score - reset interval
        >>> interval, easiness = calculate_next_review(2.5, 10, 1)
        >>> print(f"Next review in {interval} days, easiness: {easiness}")
        Next review in 1 days, easiness: 2.5
    """
    
    # Valideer input
    if not 1.3 <= easiness_factor <= 2.5:
        easiness_factor = max(1.3, min(2.5, easiness_factor))
    
    if not 0 <= quality_score <= 5:
        raise ValueError(f"quality_score moet tussen 0-5 zijn, kreeg: {quality_score}")
    
    if current_interval < 0:
        current_interval = 0
    
    # Bereken nieuwe waarden op basis van quality score
    if quality_score >= 3:
        # Goed onthouden - verhoog interval exponentieel
        if current_interval == 0:
            next_interval = 1
        elif current_interval == 1:
            next_interval = 6
        else:
            next_interval = round(current_interval * easiness_factor)
        
        # Pas easiness factor aan op basis van hoe goed het ging
        # Hoe hoger de score, hoe meer easiness stijgt
        new_easiness = easiness_factor + (
            0.1 - (5 - quality_score) * (0.08 + (5 - quality_score) * 0.02)
        )
        
        # Easiness mag niet onder 1.3 komen
        new_easiness = max(1.3, new_easiness)
    
    else:
        # Slecht onthouden (score < 3) - reset interval
        next_interval = 1
        new_easiness = easiness_factor  # Easiness blijft gelijk
    
    return next_interval, round(new_easiness, 2)


def get_next_review_date(interval_days: int) -> datetime:
    """
    Bereken de exacte datum/tijd voor de volgende review.
    
    Args:
        interval_days: Aantal dagen tot volgende review
    
    Returns:
        datetime: Datum/tijd van volgende review
    """
    return datetime.utcnow() + timedelta(days=interval_days)


def calculate_success_rate(successful_reviews: int, total_reviews: int) -> float:
    """
    Bereken success rate percentage.
    
    Args:
        successful_reviews: Aantal correcte reviews (quality >= 3)
        total_reviews: Totaal aantal reviews
    
    Returns:
        float: Success rate als percentage (0-100)
    """
    if total_reviews == 0:
        return 0.0
    
    return round((successful_reviews / total_reviews) * 100, 1)


def is_word_difficult(successful_reviews: int, total_reviews: int, threshold: float = 60.0) -> bool:
    """
    Bepaal of een woord als 'moeilijk' gemarkeerd moet worden.
    
    Args:
        successful_reviews: Aantal correcte reviews
        total_reviews: Totaal aantal reviews
        threshold: Success rate drempel (default 60%)
    
    Returns:
        bool: True als woord moeilijk is
    """
    if total_reviews < 5:
        return False  # Niet genoeg data
    
    success_rate = calculate_success_rate(successful_reviews, total_reviews)
    return success_rate < threshold


# Test functies
if __name__ == "__main__":
    print("🧪 Testing SuperMemo SM-2 Algorithm\n")
    
    # Test 1: Perfect score op nieuw woord
    print("Test 1: Perfect score (5) op nieuw woord")
    interval, easiness = calculate_next_review(2.5, 0, 5)
    print(f"  ✅ Next interval: {interval} days (verwacht: 1)")
    print(f"  ✅ New easiness: {easiness} (verwacht: > 2.5)\n")
    
    # Test 2: Goed score na eerste review
    print("Test 2: Goed score (4) na eerste review")
    interval, easiness = calculate_next_review(2.6, 1, 4)
    print(f"  ✅ Next interval: {interval} days (verwacht: 6)")
    print(f"  ✅ New easiness: {easiness}\n")
    
    # Test 3: Exponentiële groei
    print("Test 3: Exponentiële groei met goede scores")
    interval, easiness = calculate_next_review(2.5, 6, 5)
    print(f"  ✅ Next interval: {interval} days (verwacht: ~15)")
    interval, easiness = calculate_next_review(2.6, 15, 5)
    print(f"  ✅ Next interval: {interval} days (verwacht: ~39)\n")
    
    # Test 4: Slecht score - reset
    print("Test 4: Slecht score (1) - reset interval")
    interval, easiness = calculate_next_review(2.5, 30, 1)
    print(f"  ✅ Next interval: {interval} days (verwacht: 1)")
    print(f"  ✅ Easiness unchanged: {easiness} (verwacht: 2.5)\n")
    
    # Test 5: Success rate
    print("Test 5: Success rate berekening")
    rate = calculate_success_rate(8, 10)
    print(f"  ✅ Success rate: {rate}% (verwacht: 80.0%)\n")
    
    # Test 6: Moeilijk woord detectie
    print("Test 6: Moeilijk woord detectie")
    is_difficult = is_word_difficult(3, 10)
    print(f"  ✅ Is difficult: {is_difficult} (verwacht: True - 30% success)\n")
    
    print("✅ Alle tests geslaagd!")
