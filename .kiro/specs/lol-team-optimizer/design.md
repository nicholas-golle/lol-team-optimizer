# Design Document

## Overview

The streamlined League of Legends Team Optimizer consolidates multiple redundant interfaces into a single, unified CLI experience. The redesign eliminates menu depth, integrates workflows, and removes code duplication while maintaining all core optimization capabilities. The system provides a simplified 4-option main menu with intelligent defaults and inline functionality.

## Architecture

The streamlined architecture consolidates interfaces and eliminates redundancy:

```
┌─────────────────────────────────────────────────────────────┐
│                 Unified CLI Interface                       │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ │Quick        │ │Manage       │ │View         │ │Settings │ │
│ │Optimize     │ │Players      │ │Analysis     │ │         │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Engine                              │
│                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ │Data         │ │Performance  │ │Optimization │ │API      │ │
│ │Manager      │ │Calculator   │ │Engine       │ │Client   │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Simplified Notebook Interface                  │
│                                                             │
│ - Calls core engine functions                               │
│ - No duplicated logic                                       │
│ - Minimal setup cells                                       │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Unified CLI Interface (`streamlined_cli.py`)
- **Purpose**: Single streamlined interface with 4 main options
- **Key Methods**:
  - `main()`: Entry point with simplified 4-option menu
  - `quick_optimize()`: Integrated workflow for team optimization
  - `manage_players()`: Consolidated player management (add/edit/remove/bulk)
  - `view_analysis()`: Comprehensive analysis dashboard
  - `settings()`: Configuration and maintenance

### 2. Core Engine (`core_engine.py`)
- **Purpose**: Centralized business logic accessible by all interfaces
- **Key Methods**:
  - `add_player_with_data(name, riot_id)`: Add player with automatic data fetching
  - `optimize_team_smart(player_selection)`: Optimization with intelligent defaults
  - `get_comprehensive_analysis(players)`: Complete player and team analysis
  - `bulk_player_operations(operations)`: Batch player management
- **Features**:
  - Automatic API data fetching with fallbacks
  - Smart default preference calculation
  - Integrated validation and error handling
  - Consolidated result formatting

### 3. Workflow Managers
- **Quick Optimize Workflow**: Streamlined optimization with inline player management
- **Player Management Workflow**: Unified add/edit/remove/bulk operations
- **Analysis Workflow**: Comprehensive reporting with multiple views
- **Settings Workflow**: Configuration, cache management, diagnostics

### 4. Existing Components (Unchanged)
- **Riot API Client**: Maintains current functionality
- **Data Manager**: Maintains current persistence logic
- **Performance Calculator**: Maintains current calculation methods
- **Optimization Engine**: Maintains current optimization algorithms
- **Champion Data Manager**: Maintains current champion data handling

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