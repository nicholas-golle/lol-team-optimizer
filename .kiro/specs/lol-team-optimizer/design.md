# Design Document

## Overview

The League of Legends Team Optimizer is a Python application that uses mathematical optimization to determine the best role assignments for a team of 5 players. The system combines data from the Riot Games API with user-provided preferences to solve a constrained assignment problem, maximizing overall team performance while ensuring each role is filled exactly once.

## Architecture

The application follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Data Manager   │    │ Riot API Client │
│                 │    │                 │    │                 │
│ - User Input    │◄──►│ - Player Data   │◄──►│ - API Calls     │
│ - Results       │    │ - Preferences   │    │ - Rate Limiting │
│ - Validation    │    │ - Caching       │    │ - Data Parsing  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │ Performance     │              │
         │              │ Calculator      │              │
         │              │                 │              │
         │              │ - Individual    │              │
         │              │ - Synergy       │              │
         │              │ - Scoring       │              │
         │              └─────────────────┘              │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 Optimization Engine                         │
│                                                             │
│ - Constraint Solver (Hungarian Algorithm / Linear Programming) │
│ - Objective Function (Performance + Preference + Synergy)   │
│ - Result Ranking and Explanation                            │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. CLI Interface (`cli.py`)
- **Purpose**: Handle user interaction and command-line interface
- **Key Methods**:
  - `main()`: Entry point and main menu
  - `get_player_input()`: Collect available players
  - `display_results()`: Show optimization results with explanations
  - `manage_preferences()`: Interface for setting player preferences

### 2. Riot API Client (`riot_client.py`)
- **Purpose**: Interface with Riot Games API for player data
- **Key Methods**:
  - `get_summoner_data(summoner_name)`: Fetch basic summoner information
  - `get_match_history(puuid, count)`: Retrieve recent match data
  - `get_ranked_stats(summoner_id)`: Get current season ranked statistics
  - `get_champion_mastery(puuid, champion_id)`: Fetch champion mastery data
  - `calculate_role_performance(matches, role)`: Analyze performance by role
- **Features**:
  - Rate limiting compliance (120 requests per 2 minutes)
  - Automatic retry with exponential backoff
  - Response caching to minimize API calls

### 2.1. Champion Data Manager (`champion_data.py`)
- **Purpose**: Manage champion information and role mappings
- **Key Methods**:
  - `fetch_champion_list()`: Retrieve champion data from Data Dragon API
  - `get_champion_roles(champion_id)`: Determine primary/secondary roles for champions
  - `get_champion_name(champion_id)`: Convert champion ID to name
  - `update_champion_cache()`: Refresh champion data periodically
- **Data Source**: https://ddragon.leagueoflegends.com/cdn/15.14.1/data/en_US/champion.json

### 3. Data Manager (`data_manager.py`)
- **Purpose**: Handle data persistence and player information management
- **Key Methods**:
  - `save_player_data(player_data)`: Persist player information
  - `load_player_data()`: Retrieve stored player data
  - `update_preferences(player_name, preferences)`: Update role preferences
  - `cache_api_data(data, cache_key)`: Cache API responses
- **Storage**: JSON files for simplicity and portability

### 4. Performance Calculator (`performance_calculator.py`)
- **Purpose**: Calculate individual and synergy performance metrics
- **Key Methods**:
  - `calculate_individual_score(player, role, matches)`: Individual role performance
  - `calculate_synergy_score(player1, role1, player2, role2, shared_matches)`: Team synergy
  - `calculate_champion_mastery_score(player, role, champion_masteries)`: Champion proficiency for role
  - `get_role_champion_pool(player, role)`: Get top champions for a specific role
  - `normalize_scores(scores)`: Normalize different metrics to comparable scales
- **Metrics**:
  - KDA ratio, CS per minute, vision score, objective participation
  - Win rate in specific roles
  - Champion mastery levels and points
  - Champion pool depth per role
  - Performance trends over recent matches

### 5. Optimization Engine (`optimizer.py`)
- **Purpose**: Solve the role assignment optimization problem
- **Key Methods**:
  - `optimize_team(available_players)`: Main optimization function
  - `build_cost_matrix(players, roles)`: Create optimization matrix
  - `explain_assignment(assignment, scores)`: Generate assignment explanations
- **Algorithm**: Hungarian algorithm for optimal assignment with custom objective function

## Data Models

### Player Model
```python
@dataclass
class Player:
    name: str
    summoner_name: str
    puuid: str
    role_preferences: Dict[str, int]  # role -> preference score (1-5)
    performance_cache: Dict[str, Dict]  # role -> cached performance data
    champion_masteries: Dict[int, ChampionMastery]  # champion_id -> mastery data
    role_champion_pools: Dict[str, List[int]]  # role -> list of champion_ids
    last_updated: datetime
```

### Champion Mastery Model
```python
@dataclass
class ChampionMastery:
    champion_id: int
    champion_name: str
    mastery_level: int
    mastery_points: int
    chest_granted: bool
    tokens_earned: int
    primary_roles: List[str]  # roles this champion is typically played in
    last_play_time: datetime
```

### Performance Data Model
```python
@dataclass
class PerformanceData:
    role: str
    matches_played: int
    win_rate: float
    avg_kda: float
    avg_cs_per_min: float
    avg_vision_score: float
    recent_form: float  # performance trend
```

### Team Assignment Model
```python
@dataclass
class TeamAssignment:
    assignments: Dict[str, str]  # role -> player_name
    total_score: float
    individual_scores: Dict[str, float]
    synergy_scores: Dict[tuple, float]
    champion_recommendations: Dict[str, List[ChampionRecommendation]]  # role -> recommended champions
    explanation: str

@dataclass
class ChampionRecommendation:
    champion_id: int
    champion_name: str
    mastery_level: int
    mastery_points: int
    role_suitability: float  # how well this champion fits the assigned role
    confidence: float  # confidence in this recommendation
```

## Error Handling

### API Error Handling
- **Rate Limiting**: Implement exponential backoff with jitter
- **Network Errors**: Retry with timeout and fallback to cached data
- **Invalid Summoner Names**: Validate and provide user feedback
- **API Downtime**: Graceful degradation using cached data only

### Data Validation
- **Player Input**: Validate summoner names exist and are accessible
- **Preference Input**: Ensure preferences are within valid ranges
- **Team Size**: Verify exactly 5 players are selected for optimization

### Optimization Errors
- **Insufficient Data**: Handle cases where API data is limited
- **No Valid Assignment**: Detect and report impossible constraints
- **Calculation Errors**: Robust error handling in performance calculations

## Testing Strategy

### Unit Tests
- **API Client**: Mock API responses and test rate limiting
- **Performance Calculator**: Test metric calculations with known data
- **Optimization Engine**: Verify algorithm correctness with test cases
- **Data Manager**: Test data persistence and retrieval

### Integration Tests
- **End-to-End Workflow**: Test complete optimization process
- **API Integration**: Test with real API (limited to avoid rate limits)
- **Error Scenarios**: Test graceful handling of various error conditions

### Test Data
- **Mock Match Data**: Create realistic match history for testing
- **Edge Cases**: Test with minimal data, conflicting preferences
- **Performance Validation**: Compare results with manual calculations

## Configuration and Deployment

### Configuration Management
- **API Keys**: Environment variable for Riot API key
- **Cache Settings**: Configurable cache duration and size limits
- **Algorithm Parameters**: Tunable weights for different optimization factors

### Dependencies
- **Core**: `requests`, `numpy`, `scipy` (for optimization algorithms)
- **Data**: `json`, `datetime`, `dataclasses`
- **Testing**: `pytest`, `unittest.mock`
- **Optional**: `pandas` for advanced data analysis

### Performance Considerations
- **Caching Strategy**: Cache API responses for 1 hour, player data for 24 hours
- **Batch Processing**: Group API calls efficiently within rate limits
- **Memory Management**: Limit cache size and implement LRU eviction