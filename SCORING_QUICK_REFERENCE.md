# Scoring System Quick Reference

## Overview
This is a quick reference guide for understanding the League of Legends Team Optimizer scoring system. For detailed calculations, see [SCORING_CALCULATIONS.md](SCORING_CALCULATIONS.md).

## Score Ranges & Meanings

### Individual Performance Scores (0.0 - 1.0)
| Score Range | Performance Level | Description |
|-------------|------------------|-------------|
| 0.8 - 1.0   | Excellent        | Top-tier performance, consistently strong |
| 0.6 - 0.8   | Good             | Above average, reliable performance |
| 0.4 - 0.6   | Average          | Typical performance level |
| 0.2 - 0.4   | Below Average    | Needs improvement |
| 0.0 - 0.2   | Poor             | Significant performance issues |

### Synergy Scores (-0.3 to +0.3)
| Score Range | Synergy Level | Description |
|-------------|---------------|-------------|
| +0.15 to +0.3 | Excellent   | Outstanding teamwork, high win rate together |
| +0.05 to +0.15 | Good       | Solid synergy, work well together |
| -0.05 to +0.05 | Neutral    | Average compatibility |
| -0.15 to -0.05 | Poor       | Some conflicts, below average success |
| -0.3 to -0.15 | Very Poor   | Significant synergy issues |

### Champion Competency Levels
| Level | Score Range | Requirements | Description |
|-------|-------------|--------------|-------------|
| Excellent | 0.8-1.0 | 80+ points | High mastery + great performance |
| Good | 0.6-0.8 | 60-79 points | Solid mastery + good performance |
| Competent | 0.4-0.6 | 40-59 points | Adequate mastery + some experience |
| Played | 0.2-0.4 | <40 points | Limited experience or poor performance |

### Role Suitability (0.0 - 1.0)
| Score Range | Suitability | Description |
|-------------|-------------|-------------|
| 0.9-1.0 | Perfect | Primary role for champion |
| 0.7-0.9 | Excellent | Secondary role or strong flex pick |
| 0.5-0.7 | Good | Viable flex pick |
| 0.3-0.5 | Fair | Situational pick |
| 0.0-0.3 | Poor | Off-role or weak champion |

## Key Scoring Components

### Team Optimization Weights
- **Individual Performance**: 60%
- **Role Preferences**: 25%
- **Team Synergy**: 15%

### Performance Metrics (Role-Dependent Weights)
- **Win Rate**: 30-35% (varies by role)
- **KDA**: 15-30% (higher for carries)
- **CS per Minute**: 20-25% (higher for farm-dependent roles)
- **Vision Score**: 10-30% (much higher for support)
- **Champion Mastery**: 15-25% (varies by role)
- **Recent Form**: 10%

### Champion Competency Factors
- **Mastery Points**: 0-30 points (100k+ = max)
- **Win Rate**: 0-25 points (65%+ = max)
- **KDA**: 0-20 points (2.5+ = max)
- **Games Played**: 0-15 points (20+ = max)
- **Recency**: 0-10 points (5+ recent = max)

## Confidence & Reliability

### Minimum Data Requirements
- **Individual Performance**: 10+ games for full confidence
- **Synergy Analysis**: 3+ games together for basic reliability
- **Role Synergy**: 2+ games in role combination
- **Champion Synergy**: 2+ games with champion combination

### Confidence Penalties
- **<10 games**: Individual score × (games/10)
- **<3 games together**: Synergy falls back to role compatibility
- **<5 games with champion**: Reduced champion recommendation confidence

## Interpretation Examples

### High-Performing Player
```
Individual Score: 0.85 (Excellent)
- Win Rate: 72% → Strong contributor
- KDA: 2.8 → Good combat performance  
- CS/min: 7.2 → Efficient farming
- Vision: 35 → Solid map awareness
```

### Strong Synergy Pair
```
Synergy Score: +0.18 (Excellent)
- 15 games together, 80% win rate
- Strong role combination (jungle + mid)
- Recent activity (8 games last month)
- High combined performance metrics
```

### Champion Recommendation
```
Champion: Yasuo (Middle Lane)
Confidence: 85% (High)
- Competency: Good (0.75)
- Mastery: Level 7, 150k points
- Performance: 68% WR, 2.4 KDA (12 games)
- Role Suitability: 0.95 (Primary role)
```

## Quick Diagnostic Guide

### Low Team Score?
1. Check individual performance scores
2. Look for role preference mismatches
3. Examine synergy between key players
4. Consider champion pool limitations

### Poor Synergy?
1. Verify sufficient games together (3+ minimum)
2. Check role combination effectiveness
3. Look at recent vs. historical performance
4. Consider champion compatibility

### Unreliable Recommendations?
1. Ensure adequate match history (10+ games)
2. Check API data freshness
3. Verify champion mastery data
4. Consider confidence penalties

## Tips for Better Scores

### Improve Individual Performance
- Focus on role-specific metrics (CS for carries, vision for support)
- Maintain consistent performance across games
- Play more games in preferred roles

### Build Team Synergy
- Play more games together as a team
- Focus on successful role combinations
- Practice with champion combinations that work well

### Optimize Champion Pool
- Develop competency with 3-5 champions per role
- Focus on champions that suit your playstyle
- Keep champion pool current with recent games

For complete technical details and formulas, see [SCORING_CALCULATIONS.md](SCORING_CALCULATIONS.md).
##
 CLI Output Interpretation

### Team Optimization Results
```
OPTIMIZATION RESULTS
====================
Total Score: 4.25 (out of ~5.0)
Optimization Time: 0.15 seconds

Role Assignments:
  TOP: PlayerName (Score: 0.78)
  JUNGLE: PlayerName (Score: 0.82)
  ...
```

**What this means:**
- **Total Score**: Sum of individual + synergy scores (higher = better team)
- **Individual Scores**: Performance in assigned role (0.0-1.0 scale)
- **Optimization Time**: How long the algorithm took to find the best assignment

### Synergy Analysis Output
```
🏆 Best Teammates:
   1. PlayerName: +0.12 (Good synergy)
      └─ 12 games together, 75.0% win rate

⚠️ Challenging Teammates:
   1. PlayerName: -0.08 (Poor synergy)
      └─ 6 games together, 33.3% win rate
```

**What this means:**
- **Synergy Score**: How well players perform together (-0.3 to +0.3)
- **Games Together**: Sample size for reliability (more = better)
- **Win Rate**: Success rate when playing on same team

### Champion Recommendations
```
TOP Lane Recommendations:
  1. Malphite 🟢
     Level 7 | 89,432 pts | 68% WR, 2.1 KDA (15 games)
     Role Suitability: Excellent (95%)
     Confidence: High (87%)
```

**What this means:**
- **🟢 Icon**: Competency level (🔴 excellent, 🟡 good, 🟢 competent, 🔵 played)
- **Level & Points**: Champion mastery progression
- **Performance Stats**: Win rate and KDA with this champion
- **Role Suitability**: How well champion fits the assigned role
- **Confidence**: How reliable this recommendation is

### Performance Trends
```
Performance Trends for PlayerName:
  TOP: Improving (↗) - 0.72 score, 68% WR over 15 games
  JUNGLE: Declining (↘) - 0.45 score, 42% WR over 8 games
```

**What this means:**
- **Trend Direction**: Recent performance trajectory
- **Score**: Current performance level in that role
- **Win Rate & Games**: Supporting statistics for the trend

### Champion Pool Analysis
```
Top (Pool: 73 champions, Score: 1,234,567):
     Competent: 8/73 | Recent: 8 | Excellent: 0
     Top Competent Champions:
       1. Poppy 🟢
          Level 66 | 749,142 pts | 67% WR, 1.5 KDA (3 games)
```

**What this means:**
- **Pool Size**: Total champions played in this role
- **Competent/Recent/Excellent**: Breakdown of champion competency levels
- **Performance Data**: Actual game statistics with each champion

This output helps you understand not just what the system recommends, but why it makes those recommendations based on actual performance data.