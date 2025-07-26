# Scoring Calculations Documentation

## Overview

The League of Legends Team Optimizer uses a sophisticated multi-layered scoring system to determine optimal team compositions. This document provides detailed explanations of all calculations involved in the scoring process.

## Table of Contents

1. [Individual Performance Scoring](#individual-performance-scoring)
2. [Champion Mastery Scoring](#champion-mastery-scoring)
3. [Champion Competency Assessment](#champion-competency-assessment)
4. [Synergy Scoring System](#synergy-scoring-system)
5. [Team Optimization Algorithm](#team-optimization-algorithm)
6. [Champion Recommendation Scoring](#champion-recommendation-scoring)
7. [Role Suitability Calculations](#role-suitability-calculations)

---

## Individual Performance Scoring

### Base Formula
```
Individual Score = Σ(metric_value × role_weight) / total_weight
```

### Performance Metrics

#### 1. Win Rate (0.0 - 1.0)
- **Input**: Raw win rate from match history
- **Processing**: Used directly (already normalized)
- **Weight**: 30% (default), varies by role

#### 2. KDA Score (0.0 - 1.0)
```
KDA Score = min(average_kda / 3.0, 1.0)
```
- **Cap**: 3.0 KDA = 1.0 score (perfect)
- **Weight**: 20% (default), varies by role

#### 3. CS per Minute (0.0 - 1.0)
```
CS Score = min(avg_cs_per_min / 8.0, 1.0)
```
- **Cap**: 8 CS/min = 1.0 score (perfect)
- **Weight**: 15% (default), higher for carry roles

#### 4. Vision Score (0.0 - 1.0)
```
Vision Score = min(avg_vision_score / 50.0, 1.0)
```
- **Cap**: 50 vision score = 1.0 score (perfect)
- **Weight**: 10% (default), much higher for support

#### 5. Recent Form (-1.0 to 1.0, normalized to 0.0 - 1.0)
```
Recent Form Score = (recent_form + 1) / 2.0
```
- **Weight**: 10% (default)

### Role-Specific Weights

#### Top Lane
```python
{
    "cs_per_min": 0.25,      # Farm important
    "kda": 0.25,             # Survival/impact
    "win_rate": 0.30,        # Overall success
    "champion_mastery": 0.20  # Champion pool depth
}
```

#### Jungle
```python
{
    "vision_score": 0.15,    # Map control
    "kda": 0.25,             # Impact on fights
    "win_rate": 0.35,        # Game influence
    "champion_mastery": 0.25  # Diverse champion needs
}
```

#### Middle Lane
```python
{
    "cs_per_min": 0.20,      # Farm efficiency
    "kda": 0.30,             # Carry potential
    "win_rate": 0.30,        # Game impact
    "champion_mastery": 0.20  # Champion versatility
}
```

#### Support
```python
{
    "vision_score": 0.30,    # Primary responsibility
    "kda": 0.15,             # Less focus on kills
    "win_rate": 0.35,        # Enabling team success
    "champion_mastery": 0.20  # Champion pool
}
```

#### Bottom Lane (ADC)
```python
{
    "cs_per_min": 0.25,      # Farm critical
    "kda": 0.25,             # Damage output
    "win_rate": 0.30,        # Late game impact
    "champion_mastery": 0.20  # Champion mastery
}
```

### Confidence Penalty
```
if matches_played < 10:
    confidence_penalty = matches_played / 10.0
    final_score *= confidence_penalty
```

---

## Champion Mastery Scoring

### Individual Champion Score
```
Champion Score = (level_score × 0.7) + (points_score × 0.3) + bonuses
```

#### Level Score
```
level_score = mastery_level / 7.0
```

#### Points Score
```
points_score = min(mastery_points / 100000.0, 1.0)
```

#### Mastery Bonuses
```
if mastery_level >= 6: bonus += 0.1
if mastery_level == 7: bonus += 0.1  # Additional bonus
```

### Role Champion Pool Score
```
Role Score = Σ(champion_score × weight) / total_weight

where weight = 1.0 / (rank + 1)  # 1.0, 0.5, 0.33, 0.25, 0.2...
```

### Overall Mastery Score
For players without role-specific champions:
```
Overall Score = Σ(champion_score × weight) / max_possible_weight

where weight decreases by rank: 1.0, 0.5, 0.33, 0.25, 0.2...
```

---

## Champion Competency Assessment

### Competency Scoring Algorithm
```
Total Score = mastery_points_factor + win_rate_factor + kda_factor + 
              games_played_factor + recency_factor
```

#### Mastery Points Factor (0-30 points)
```
if mastery_points >= 100000: score += 30
elif mastery_points >= 50000: score += 25
elif mastery_points >= 20000: score += 20
elif mastery_points >= 10000: score += 15
else: score += max(0, mastery_points // 1000)
```

#### Win Rate Factor (0-25 points)
```
if win_rate >= 0.65: score += 25
elif win_rate >= 0.55: score += 20
elif win_rate >= 0.45: score += 15
elif win_rate >= 0.35: score += 10
else: score += 5
```

#### KDA Factor (0-20 points)
```
if avg_kda >= 2.5: score += 20
elif avg_kda >= 2.0: score += 15
elif avg_kda >= 1.5: score += 10
elif avg_kda >= 1.0: score += 5
```

#### Games Played Factor (0-15 points)
```
if games_played >= 20: score += 15
elif games_played >= 10: score += 10
elif games_played >= 5: score += 5
```

#### Recency Factor (0-10 points)
```
if recent_games >= 5: score += 10
elif recent_games >= 3: score += 7
elif recent_games >= 1: score += 5
```

### Competency Levels
```
if total_score >= 80: "excellent"
elif total_score >= 60: "good"
elif total_score >= 40: "competent"
else: "played"
```

### Competency Score Mapping
```python
competency_scores = {
    "unknown": 0.0,
    "played": 0.2,
    "competent": 0.5,
    "good": 0.75,
    "excellent": 1.0
}
```

---

## Synergy Scoring System

### Historical Synergy Calculation
```
Overall Synergy = (base_synergy + performance_factor + recency_factor) × confidence
```

#### Base Synergy
```
base_synergy = (win_rate_together - 0.5) × 0.4  # Scale to -0.2 to 0.2
```

#### Performance Factor
```
if avg_combined_kda > 3.0: performance_factor += 0.05
elif avg_combined_kda < 1.5: performance_factor -= 0.05
```

#### Recency Factor
```
if recent_games_together >= 5: recency_factor = 0.05
elif recent_games_together >= 2: recency_factor = 0.02
```

#### Confidence Adjustment
```
confidence = min(games_together / 15.0, 1.0)
```

### Role-Specific Synergy
```
Role Synergy Score = (win_rate × confidence) + (0.5 × (1 - confidence))

where confidence = min(role_games / 10.0, 1.0)
```

### Champion-Specific Synergy
```
Champion Synergy Score = (win_rate × confidence) + (0.5 × (1 - confidence))

where confidence = min(champion_games / 5.0, 1.0)
```

### Fallback Role Compatibility Matrix
When no historical data is available:
```python
synergy_matrix = {
    ("top", "jungle"): 0.1,
    ("jungle", "middle"): 0.15,
    ("middle", "support"): 0.05,
    ("support", "bottom"): 0.2,
    ("bottom", "support"): 0.2,
    ("top", "support"): 0.05,
    ("jungle", "support"): 0.1,
    ("jungle", "bottom"): 0.05,
    ("top", "middle"): 0.05,
    ("middle", "bottom"): 0.05
}
```

---

## Team Optimization Algorithm

### Cost Matrix Construction
```
Cost[player][role] = -(individual_performance × 0.6 + role_preference × 0.25)
```

#### Individual Performance Weight: 60%
- Calculated using role-specific performance scoring

#### Role Preference Weight: 25%
```
preference_score = player.role_preferences[role] / 5.0  # Normalize 1-5 to 0.2-1.0
```

#### Team Synergy Weight: 15%
- Added after Hungarian algorithm assignment
- Calculated for all player pairs in the team

### Hungarian Algorithm
The system uses the Hungarian algorithm to solve the assignment problem:
1. Build cost matrix (negative scores since we minimize cost)
2. Apply Hungarian algorithm to find optimal assignment
3. Add synergy scores to total team score

### Total Team Score
```
Total Score = Σ(individual_scores) + Σ(synergy_scores)
```

---

## Champion Recommendation Scoring

### Recommendation Confidence
```
Final Confidence = (competency_confidence × 0.4) + (mastery_confidence × 0.3) + 
                   (role_suitability × 0.2) + performance_bonus + recency_bonus
```

#### Competency Confidence (0.0 - 1.0)
Uses the competency score from champion competency assessment.

#### Mastery Confidence (0.0 - 1.0)
```
level_confidence = mastery_level / 7.0
points_confidence = min(mastery_points / 50000.0, 1.0)
mastery_confidence = (level_confidence × 0.6) + (points_confidence × 0.4)
```

#### Performance Bonus
```
if games_played >= 5:
    if win_rate >= 0.6: performance_bonus += 0.1
    elif win_rate >= 0.5: performance_bonus += 0.05
    
    if avg_kda >= 2.0: performance_bonus += 0.05
```

#### Recency Bonus
```
if recent_games >= 3: recency_bonus = 0.1
elif recent_games >= 1: recency_bonus = 0.05
```

---

## Role Suitability Calculations

### Primary Role Suitability
```
if role in champion_primary_roles:
    if len(champion_roles) == 1: suitability = 0.95  # Specialized
    elif len(champion_roles) == 2: suitability = 0.85  # Dual role
    else: suitability = 0.75  # Flexible
```

### Flex Pick Compatibility
```python
flex_patterns = {
    ('middle', 'support'): 0.6,    # Mages can support
    ('support', 'middle'): 0.4,    # Some supports can mid
    ('bottom', 'middle'): 0.3,     # ADCs can sometimes mid
    ('middle', 'bottom'): 0.3,     # Some mids can ADC
    ('top', 'jungle'): 0.7,        # Tanks flex well
    ('jungle', 'top'): 0.7,        # Junglers can top
    ('jungle', 'support'): 0.4,    # Some junglers support
    ('top', 'support'): 0.5,       # Tank supports
}
```

### Off-Role Penalty
```
if role not in champion_primary_roles:
    if flex_compatibility > 0: suitability = flex_compatibility
    else: suitability = 0.2  # Poor fit
```

---

## Scoring Ranges and Interpretations

### Individual Performance Scores
- **0.8 - 1.0**: Excellent performance
- **0.6 - 0.8**: Good performance  
- **0.4 - 0.6**: Average performance
- **0.2 - 0.4**: Below average performance
- **0.0 - 0.2**: Poor performance

### Synergy Scores
- **+0.15 to +0.3**: Excellent synergy
- **+0.05 to +0.15**: Good synergy
- **-0.05 to +0.05**: Neutral synergy
- **-0.15 to -0.05**: Poor synergy
- **-0.3 to -0.15**: Very poor synergy

### Champion Competency Levels
- **Excellent (0.8-1.0)**: 80+ total points, high mastery + good performance
- **Good (0.6-0.8)**: 60-79 points, solid mastery + decent performance
- **Competent (0.4-0.6)**: 40-59 points, adequate mastery + some experience
- **Played (0.2-0.4)**: <40 points, limited experience or poor performance

### Role Suitability
- **0.9-1.0**: Perfect fit (primary role)
- **0.7-0.9**: Excellent fit (secondary role or strong flex)
- **0.5-0.7**: Good fit (viable flex pick)
- **0.3-0.5**: Fair fit (situational pick)
- **0.0-0.3**: Poor fit (off-role or weak champion)

---

## Algorithm Complexity and Performance

### Time Complexity
- **Hungarian Algorithm**: O(n³) where n = number of players
- **Synergy Calculation**: O(n²) for all player pairs
- **Champion Scoring**: O(m) where m = number of champions per player

### Space Complexity
- **Cost Matrix**: O(n²)
- **Synergy Database**: O(p²) where p = total players in database
- **Champion Data**: O(n × m) where n = players, m = champions

### Optimization Strategies
1. **Caching**: Performance data cached to avoid recalculation
2. **Lazy Loading**: Synergy data loaded only when needed
3. **Batch Processing**: Multiple optimizations reuse calculated data
4. **Confidence Thresholds**: Skip calculations for low-confidence data

---

## Configuration and Tuning

### Adjustable Parameters

#### Optimization Weights
```python
weights = {
    "individual_performance": 0.6,  # 60%
    "role_preference": 0.25,        # 25%
    "team_synergy": 0.15           # 15%
}
```

#### Performance Metric Weights
```python
performance_weights = {
    "win_rate": 0.3,
    "kda": 0.2,
    "cs_per_min": 0.15,
    "vision_score": 0.1,
    "recent_form": 0.1,
    "champion_mastery": 0.15
}
```

#### Confidence Thresholds
- **Minimum games for individual scoring**: 10
- **Minimum games for synergy scoring**: 3
- **Minimum games for role synergy**: 2
- **Minimum games for champion synergy**: 2

### Tuning Recommendations
1. **Increase synergy weight** for teams that play together frequently
2. **Increase preference weight** for casual/fun-focused teams
3. **Adjust role weights** based on meta changes or team strategy
4. **Modify confidence thresholds** based on available data volume

---

## Validation and Testing

### Score Validation
- All individual scores clamped to [0.0, 1.0]
- Synergy scores clamped to [-0.3, 0.3]
- Confidence scores clamped to [0.0, 1.0]
- Role suitability clamped to [0.0, 1.0]

### Edge Case Handling
- **No performance data**: Use preference-based scoring with penalty
- **No synergy data**: Fall back to role compatibility matrix
- **Insufficient games**: Apply confidence penalties
- **Missing champion data**: Use neutral suitability scores

### Testing Scenarios
1. **New players**: Minimal data, preference-driven recommendations
2. **Experienced players**: Full data utilization, confidence-weighted scoring
3. **Mixed experience teams**: Balanced scoring with appropriate confidence adjustments
4. **Edge cases**: Single-champion players, role-locked preferences, etc.

This scoring system provides a comprehensive, data-driven approach to team optimization that balances individual skill, role preferences, champion mastery, and team synergy to create optimal League of Legends team compositions.