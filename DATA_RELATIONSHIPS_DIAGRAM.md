# Data Relationships Diagram

This document provides detailed visual representations of how data flows and relates within the League of Legends Team Optimizer.

## High-Level Data Flow Architecture

```mermaid
graph TB
    subgraph "External Data Sources"
        API[Riot Games API]
        DDragon[Data Dragon API]
    end
    
    subgraph "Application Core"
        Engine[Core Engine]
        DataMgr[Data Manager]
        RiotClient[Riot API Client]
        ChampMgr[Champion Data Manager]
        SynergyMgr[Synergy Manager]
        PerfCalc[Performance Calculator]
        Optimizer[Optimization Engine]
    end
    
    subgraph "Persistent Storage"
        PlayerDB[(players.json)]
        MatchDB[(matches.json)]
        MatchIndex[(match_index.json)]
        MigrationLog[(migration_log.json)]
        Backups[(backups/)]
    end
    
    subgraph "Cache Layer"
        APICache[(API Response Cache)]
        ChampCache[(Champion Data Cache)]
        MasteryCache[(Mastery Cache)]
        SynergyCache[(synergy_data.json)]
    end
    
    subgraph "Configuration"
        Config[(.env / config)]
    end
    
    %% External API connections
    API --> RiotClient
    DDragon --> ChampMgr
    
    %% Core component relationships
    Engine --> DataMgr
    Engine --> RiotClient
    Engine --> ChampMgr
    Engine --> SynergyMgr
    Engine --> PerfCalc
    Engine --> Optimizer
    
    %% Data Manager connections
    DataMgr --> PlayerDB
    DataMgr --> APICache
    DataMgr --> MigrationLog
    DataMgr --> Backups
    
    %% Match Manager connections
    Engine --> MatchDB
    Engine --> MatchIndex
    
    %% Cache connections
    RiotClient --> APICache
    RiotClient --> MasteryCache
    ChampMgr --> ChampCache
    SynergyMgr --> SynergyCache
    
    %% Match data flow
    RiotClient --> MatchDB
    MatchDB --> MatchIndex
    
    %% Configuration
    Config --> Engine
    Config --> DataMgr
    Config --> RiotClient
    Config --> ChampMgr
    
    %% Styling
    classDef external fill:#e1f5fe
    classDef core fill:#f3e5f5
    classDef storage fill:#e8f5e8
    classDef cache fill:#fff3e0
    classDef config fill:#fce4ec
    
    class API,DDragon external
    class Engine,DataMgr,RiotClient,ChampMgr,SynergyMgr,PerfCalc,Optimizer core
    class PlayerDB,MigrationLog,Backups storage
    class APICache,ChampCache,MasteryCache,MatchCache,SynergyCache cache
    class Config config
```

## Detailed Data Model Relationships

```mermaid
erDiagram
    PLAYER {
        string name PK "Display name"
        string summoner_name "Riot ID (gameName#tagLine)"
        string puuid UK "Riot unique identifier"
        json role_preferences "Role preferences (1-5)"
        json performance_cache "Cached performance by role"
        json role_champion_pools "Champions per role"
        datetime last_updated "Last data refresh"
    }
    
    CHAMPION_MASTERY {
        int champion_id PK "Riot champion ID"
        string champion_name "Champion display name"
        int mastery_level "Mastery level (0-7)"
        int mastery_points "Total mastery points"
        boolean chest_granted "Season chest earned"
        int tokens_earned "Mastery tokens"
        json primary_roles "Roles this champion plays"
        datetime last_play_time "Last played timestamp"
    }
    
    CHAMPION_INFO {
        int champion_id PK "Unique champion identifier"
        string name "Champion name"
        string title "Champion title"
        json tags "Role classifications"
        string key "Champion key (string ID)"
    }
    
    CHAMPION_PERFORMANCE {
        int games_played "Total games with champion"
        int wins "Games won"
        int losses "Games lost"
        int total_kills "Cumulative kills"
        int total_deaths "Cumulative deaths"
        int total_assists "Cumulative assists"
        int recent_games "Games in last 30 days"
        datetime last_played "Last game timestamp"
    }
    
    PERFORMANCE_DATA {
        string role PK "Role (top/jungle/middle/support/bottom)"
        int matches_played "Total matches in role"
        float win_rate "Win rate (0.0-1.0)"
        float avg_kda "Average KDA ratio"
        float avg_cs_per_min "Average CS per minute"
        float avg_vision_score "Average vision score"
        float recent_form "Performance trend (-1 to 1)"
    }
    
    PLAYER_SYNERGY_DATA {
        string player1_name PK "First player name"
        string player2_name PK "Second player name"
        int games_together "Total games played together"
        int wins_together "Games won together"
        int losses_together "Games lost together"
        float avg_combined_kda "Average combined KDA"
        float avg_game_duration "Average game length"
        float avg_vision_score_combined "Combined vision score"
        json role_combinations "Performance by role pairs"
        json champion_combinations "Performance by champion pairs"
        datetime last_played_together "Last game timestamp"
    }
    
    ROLE_SPECIFIC_SYNERGY {
        string player1_name PK "First player name"
        string player1_role PK "First player role"
        string player2_name PK "Second player name"
        string player2_role PK "Second player role"
        int games_together "Games in these roles"
        int wins_together "Wins in these roles"
        float avg_combined_kda "Combined KDA in roles"
        json champion_combinations "Champion combos in roles"
        datetime last_played_together "Last game in roles"
    }
    
    TEAM_ASSIGNMENT {
        json assignments "Role to player mappings"
        float total_score "Overall team score"
        json individual_scores "Player individual scores"
        json synergy_scores "Pairwise synergy scores"
        json champion_recommendations "Recommended champions per role"
        string explanation "Assignment reasoning"
    }
    
    CHAMPION_RECOMMENDATION {
        int champion_id "Recommended champion ID"
        string champion_name "Champion name"
        int mastery_level "Player's mastery level"
        int mastery_points "Player's mastery points"
        float role_suitability "Role fit score (0-1)"
        float confidence "Recommendation confidence (0-1)"
    }
    
    %% Primary relationships
    PLAYER ||--o{ CHAMPION_MASTERY : "has masteries for"
    PLAYER ||--o{ PERFORMANCE_DATA : "has performance in"
    PLAYER ||--o{ PLAYER_SYNERGY_DATA : "synergizes with"
    PLAYER ||--o{ TEAM_ASSIGNMENT : "assigned to"
    
    %% Champion relationships
    CHAMPION_MASTERY ||--|| CHAMPION_INFO : "references"
    CHAMPION_MASTERY ||--o| CHAMPION_PERFORMANCE : "includes"
    CHAMPION_RECOMMENDATION ||--|| CHAMPION_INFO : "recommends"
    
    %% Synergy relationships
    PLAYER_SYNERGY_DATA ||--o{ ROLE_SPECIFIC_SYNERGY : "detailed by"
    
    %% Team assignment relationships
    TEAM_ASSIGNMENT ||--o{ CHAMPION_RECOMMENDATION : "includes"
    
    %% Cross-references
    PERFORMANCE_DATA ||--|| PLAYER : "belongs to"
    ROLE_SPECIFIC_SYNERGY ||--|| PLAYER_SYNERGY_DATA : "details"
```

## Cache Architecture and Data Flow

```mermaid
graph LR
    subgraph "Application Request Flow"
        A[User Request] --> B[Core Engine]
        B --> C[Data Manager]
    end
    
    subgraph "Cache Hierarchy"
        C --> D{In-Memory Cache}
        D -->|Hit| E[Return Cached Data]
        D -->|Miss| F{File Cache}
        F -->|Hit| G[Load from File]
        F -->|Miss| H[API Request]
        G --> I[Update Memory Cache]
        H --> J[Cache to File]
        J --> I
        I --> E
    end
    
    subgraph "Cache Types"
        K[Player Data Cache<br/>TTL: 24h]
        L[API Response Cache<br/>TTL: 1h]
        M[Champion Data Cache<br/>TTL: 24h]
        N[Match History Cache<br/>TTL: 1h]
        O[Mastery Cache<br/>TTL: 1h]
    end
    
    subgraph "Storage Files"
        P[(players.json)]
        Q[(cache/*.json)]
        R[(champion_data/)]
        S[(synergy_data.json)]
    end
    
    %% Cache type connections
    F --> K
    F --> L
    F --> M
    F --> N
    F --> O
    
    %% Storage connections
    K --> P
    L --> Q
    M --> R
    N --> Q
    O --> Q
    
    %% Styling
    classDef request fill:#e3f2fd
    classDef cache fill:#f1f8e9
    classDef storage fill:#fce4ec
    
    class A,B,C request
    class D,F,K,L,M,N,O cache
    class P,Q,R,S storage
```

## Data Transformation Pipeline

```mermaid
graph TD
    subgraph "Raw API Data"
        A[Riot API Response]
        B[Match History JSON]
        C[Champion Mastery JSON]
        D[Summoner Data JSON]
    end
    
    subgraph "Data Processing"
        E[Parse API Response]
        F[Validate Data Format]
        G[Transform to Models]
        H[Calculate Derived Metrics]
        I[Update Relationships]
    end
    
    subgraph "Data Models"
        J[Player Object]
        K[ChampionMastery Objects]
        L[PerformanceData Objects]
        M[SynergyData Objects]
    end
    
    subgraph "Storage Operations"
        N[Serialize to JSON]
        O[Atomic File Write]
        P[Update Cache]
        Q[Backup Creation]
    end
    
    subgraph "Persistent Storage"
        R[(players.json)]
        S[(cache files)]
        T[(backup files)]
    end
    
    %% Data flow
    A --> E
    B --> E
    C --> E
    D --> E
    
    E --> F
    F --> G
    G --> H
    H --> I
    
    I --> J
    I --> K
    I --> L
    I --> M
    
    J --> N
    K --> N
    L --> N
    M --> N
    
    N --> O
    O --> P
    O --> Q
    
    P --> S
    Q --> T
    O --> R
    
    %% Styling
    classDef api fill:#e8f5e8
    classDef process fill:#fff3e0
    classDef model fill:#f3e5f5
    classDef storage fill:#e1f5fe
    classDef persist fill:#fce4ec
    
    class A,B,C,D api
    class E,F,G,H,I process
    class J,K,L,M model
    class N,O,P,Q storage
    class R,S,T persist
```

## Synergy Data Relationships

```mermaid
graph TB
    subgraph "Player Synergy Network"
        P1[Player 1]
        P2[Player 2]
        P3[Player 3]
        P4[Player 4]
        P5[Player 5]
    end
    
    subgraph "Synergy Data Structure"
        S12[P1-P2 Synergy]
        S13[P1-P3 Synergy]
        S14[P1-P4 Synergy]
        S23[P2-P3 Synergy]
        S24[P2-P4 Synergy]
        S34[P3-P4 Synergy]
    end
    
    subgraph "Role-Specific Synergies"
        R1[Top-Jungle Synergy]
        R2[Jungle-Mid Synergy]
        R3[Mid-Support Synergy]
        R4[Support-ADC Synergy]
        R5[Top-Support Synergy]
    end
    
    subgraph "Champion Combinations"
        C1[Champion Pair 1]
        C2[Champion Pair 2]
        C3[Champion Pair 3]
        C4[Champion Pair 4]
    end
    
    %% Player connections
    P1 -.-> S12
    P2 -.-> S12
    P1 -.-> S13
    P3 -.-> S13
    P1 -.-> S14
    P4 -.-> S14
    P2 -.-> S23
    P3 -.-> S23
    P2 -.-> S24
    P4 -.-> S24
    P3 -.-> S34
    P4 -.-> S34
    
    %% Synergy to role-specific
    S12 --> R1
    S12 --> R2
    S13 --> R2
    S13 --> R3
    S23 --> R3
    S23 --> R4
    S24 --> R4
    S24 --> R5
    
    %% Role-specific to champion combinations
    R1 --> C1
    R2 --> C2
    R3 --> C3
    R4 --> C4
    
    %% Styling
    classDef player fill:#e3f2fd
    classDef synergy fill:#f1f8e9
    classDef role fill:#fff3e0
    classDef champion fill:#fce4ec
    
    class P1,P2,P3,P4,P5 player
    class S12,S13,S14,S23,S24,S34 synergy
    class R1,R2,R3,R4,R5 role
    class C1,C2,C3,C4 champion
```

## Data Access Patterns

```mermaid
sequenceDiagram
    participant U as User Interface
    participant E as Core Engine
    participant D as Data Manager
    participant C as Cache Layer
    participant F as File System
    participant A as Riot API
    
    Note over U,A: Player Data Refresh Flow
    
    U->>E: Request player data refresh
    E->>D: Load player data
    D->>C: Check in-memory cache
    
    alt Cache Hit
        C->>D: Return cached data
    else Cache Miss
        D->>F: Load from players.json
        F->>D: Return player data
        D->>C: Update cache
    end
    
    D->>E: Return player objects
    E->>A: Request fresh API data
    A->>E: Return API response
    E->>D: Update player data
    D->>F: Save to players.json
    D->>C: Update cache
    D->>E: Confirm update
    E->>U: Return success
    
    Note over U,A: Team Optimization Flow
    
    U->>E: Request team optimization
    E->>D: Load all players
    D->>C: Get cached players
    C->>D: Return player data
    E->>D: Load synergy data
    D->>F: Load synergy_data.json
    F->>D: Return synergy data
    E->>E: Calculate optimal assignments
    E->>U: Return team assignments
```

## File System Organization

```
lol-team-optimizer/
├── data/                                    # Persistent application data
│   ├── players.json                        # Main player database (JSON array)
│   │   └── [Player objects with embedded ChampionMastery and PerformanceData]
│   ├── migration_log.json                  # Migration history and status
│   ├── backups/                           # Timestamped data backups
│   │   ├── backup_20250128_120000/        # Backup directory
│   │   │   ├── players.json               # Backed up player data
│   │   │   ├── cache/                     # Backed up cache
│   │   │   └── backup_manifest.json       # Backup metadata
│   │   └── manual_backup_20250128/        # Manual backup
│   └── logs/                              # Application logs
│       └── app.log                        # Main application log
│
├── cache/                                  # Temporary cached data with TTL
│   ├── champion_data/                     # Static champion information
│   │   ├── champions.json                 # All champion data from Data Dragon
│   │   └── version.json                   # Data Dragon version info
│   ├── api_cache/                         # Legacy cache directory
│   ├── synergy_data.json                  # Player synergy database
│   ├── api_cache_old.json                 # Migrated legacy cache file
│   ├── mastery_[PUUID].json              # Per-player champion mastery cache
│   ├── matches_[PUUID].json              # Per-player match history cache
│   └── [hash].json                       # Individual API response caches
│
└── .env                                   # Environment configuration
    └── RIOT_API_KEY=...                   # Riot Games API key
```

This comprehensive data architecture documentation provides a complete understanding of how data flows through the League of Legends Team Optimizer, from external APIs through processing pipelines to persistent storage and caching layers.