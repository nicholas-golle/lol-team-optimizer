#!/usr/bin/env python3
"""
Example demonstrating the Data Quality Validation and Anomaly Detection system.

This example shows how to use the DataQualityValidator to validate match data,
detect anomalies in performance data, and generate comprehensive quality reports.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from lol_team_optimizer.data_quality_validator import DataQualityValidator
from lol_team_optimizer.analytics_models import PerformanceMetrics
from lol_team_optimizer.models import Match, MatchParticipant, Player, ChampionMastery, ChampionPerformance


def create_sample_data():
    """Create sample data for demonstration."""
    
    # Create a valid match
    valid_match = Match(
        match_id="VALID_MATCH_001",
        game_creation=int((datetime.now() - timedelta(hours=2)).timestamp() * 1000),
        game_duration=1800,  # 30 minutes
        game_end_timestamp=int((datetime.now() - timedelta(hours=1, minutes=30)).timestamp() * 1000),
        queue_id=420,  # Ranked Solo
        map_id=11,  # Summoner's Rift
        winning_team=100,
        participants=[
            MatchParticipant(
                puuid=f"player_{i}_puuid",
                summoner_name=f"Player{i}",
                champion_id=i + 1,
                team_id=100 if i < 5 else 200,
                kills=5 + i, deaths=3, assists=8 + i,
                total_damage_dealt_to_champions=15000 + i * 1000,
                total_minions_killed=150 + i * 10,
                vision_score=25 + i,
                gold_earned=12000 + i * 500,
                win=(i < 5)  # Team 100 wins
            ) for i in range(10)
        ]
    )
    
    # Create an invalid match with issues
    invalid_match = Match(
        match_id="",  # Missing match ID - critical issue
        game_creation=int((datetime.now() + timedelta(hours=1)).timestamp() * 1000),  # Future timestamp - error
        game_duration=100,  # Very short duration - warning
        game_end_timestamp=int(datetime.now().timestamp() * 1000),
        queue_id=999,  # Invalid queue ID - info
        map_id=11,
        winning_team=100,
        participants=[
            MatchParticipant(
                puuid=f"player_{i}_puuid",
                summoner_name=f"Player{i}",
                champion_id=1 if i < 3 else 2,  # Duplicate champions - error
                team_id=100 if i < 5 else 200,
                kills=-1 if i == 0 else 5,  # Negative kills - error
                deaths=3, assists=8,
                total_damage_dealt_to_champions=15000,
                total_minions_killed=150,
                vision_score=25,
                gold_earned=12000,
                win=(i < 5)
            ) for i in range(10)
        ]
    )
    
    # Create a valid player
    valid_player = Player(
        name="ValidPlayer",
        summoner_name="ValidSummoner",
        puuid="valid_player_puuid",
        role_preferences={"top": 4, "jungle": 3, "middle": 5, "support": 2, "bottom": 3},
        champion_masteries={
            1: ChampionMastery(
                champion_id=1,
                champion_name="Annie",
                mastery_level=7,
                mastery_points=50000,
                performance=ChampionPerformance(
                    games_played=25,
                    wins=15,
                    losses=10,
                    total_kills=75,
                    total_deaths=50,
                    total_assists=125
                )
            )
        }
    )
    
    # Create an invalid player with issues
    invalid_player = Player(
        name="",  # Missing name - critical
        summoner_name="InvalidSummoner",
        puuid="",  # Missing PUUID - critical
        role_preferences={"invalid_role": 3, "top": 6},  # Invalid role and preference - errors
        champion_masteries={
            1: ChampionMastery(
                champion_id=2,  # Mismatched champion ID - error
                champion_name="Blitzcrank",
                mastery_level=8,  # High mastery level - warning
                mastery_points=10000  # Low points for level - warning
            )
        }
    )
    
    # Create performance data with anomalies
    performance_data = [
        PerformanceMetrics(games_played=10, wins=5, win_rate=0.5, avg_kda=2.0, avg_cs_per_min=7.0, avg_vision_score=20.0),
        PerformanceMetrics(games_played=12, wins=6, win_rate=0.5, avg_kda=2.1, avg_cs_per_min=7.1, avg_vision_score=21.0),
        PerformanceMetrics(games_played=11, wins=5, win_rate=0.45, avg_kda=1.9, avg_cs_per_min=6.9, avg_vision_score=19.0),
        PerformanceMetrics(games_played=13, wins=6, win_rate=0.46, avg_kda=2.0, avg_cs_per_min=7.0, avg_vision_score=20.0),
        PerformanceMetrics(games_played=10, wins=5, win_rate=0.5, avg_kda=2.1, avg_cs_per_min=7.1, avg_vision_score=21.0),
        # Outlier data point
        PerformanceMetrics(games_played=15, wins=15, win_rate=1.0, avg_kda=10.0, avg_cs_per_min=15.0, avg_vision_score=60.0),
        # Performance drop
        PerformanceMetrics(games_played=8, wins=1, win_rate=0.125, avg_kda=0.8, avg_cs_per_min=5.0, avg_vision_score=12.0)
    ]
    
    return [valid_match, invalid_match], [valid_player, invalid_player], performance_data


def main():
    """Main demonstration function."""
    print("=== Data Quality Validation and Anomaly Detection Demo ===\n")
    
    # Create validator
    validator = DataQualityValidator()
    
    # Create sample data
    matches, players, performance_data = create_sample_data()
    
    print("1. MATCH DATA VALIDATION")
    print("-" * 40)
    
    for i, match in enumerate(matches):
        match_type = "Valid" if i == 0 else "Invalid"
        print(f"\n{match_type} Match ({match.match_id or 'NO_ID'}):")
        
        issues = validator.validate_match_data(match)
        if not issues:
            print("  [OK] No validation issues found")
        else:
            for issue in issues:
                severity_icon = {"info": "INFO", "warning": "WARN", "error": "ERROR", "critical": "CRIT"}
                icon = severity_icon.get(issue.severity.value, "?")
                print(f"  [{icon}] {issue.message}")
    
    print("\n\n2. PLAYER DATA VALIDATION")
    print("-" * 40)
    
    for i, player in enumerate(players):
        player_type = "Valid" if i == 0 else "Invalid"
        print(f"\n{player_type} Player ({player.name or 'NO_NAME'}):")
        
        issues = validator.validate_player_data(player)
        if not issues:
            print("  [OK] No validation issues found")
        else:
            for issue in issues:
                severity_icon = {"info": "INFO", "warning": "WARN", "error": "ERROR", "critical": "CRIT"}
                icon = severity_icon.get(issue.severity.value, "?")
                print(f"  [{icon}] {issue.message}")
    
    print("\n\n3. PERFORMANCE ANOMALY DETECTION")
    print("-" * 40)
    
    context = {"player_name": "TestPlayer", "puuid": "test_puuid"}
    anomalies = validator.detect_performance_anomalies(performance_data, context)
    
    if not anomalies:
        print("  [OK] No anomalies detected")
    else:
        print(f"  Detected {len(anomalies)} anomalies:")
        for anomaly in anomalies:
            anomaly_icon = {"statistical_outlier": "OUTLIER", "performance_spike": "SPIKE", 
                          "performance_drop": "DROP", "temporal_anomaly": "TEMPORAL"}
            icon = anomaly_icon.get(anomaly.anomaly_type.value, "ANOMALY")
            print(f"    [{icon}] {anomaly.description}")
            print(f"       Confidence: {anomaly.confidence:.2f}")
            if anomaly.statistical_measures:
                for key, value in anomaly.statistical_measures.items():
                    if isinstance(value, float):
                        print(f"       {key}: {value:.3f}")
                    else:
                        print(f"       {key}: {value}")
    
    print("\n\n4. DATA QUALITY SCORE")
    print("-" * 40)
    
    quality_score = validator.calculate_data_quality_score(matches, players)
    
    print(f"Overall Quality Score: {quality_score.overall_score:.2f} ({quality_score.reliability_indicator})")
    print(f"  Completeness: {quality_score.completeness_score:.2f}")
    print(f"  Consistency:  {quality_score.consistency_score:.2f}")
    print(f"  Accuracy:     {quality_score.accuracy_score:.2f}")
    print(f"  Timeliness:   {quality_score.timeliness_score:.2f}")
    print(f"  Validity:     {quality_score.validity_score:.2f}")
    print(f"  Valid Records: {quality_score.valid_records}/{quality_score.total_records}")
    
    print("\n\n5. COMPREHENSIVE QUALITY REPORT")
    print("-" * 40)
    
    report = validator.generate_quality_report(matches, players, "demo_report")
    
    print(f"Report ID: {report.report_id}")
    print(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data Source: {report.data_source}")
    
    # Summary statistics
    stats = report.summary_stats
    print(f"\nData Overview:")
    print(f"  Total Matches: {stats['data_overview']['total_matches']}")
    print(f"  Total Players: {stats['data_overview']['total_players']}")
    
    print(f"\nValidation Issues:")
    validation_summary = stats['validation_summary']
    print(f"  Critical: {validation_summary['critical_issues']}")
    print(f"  Errors:   {validation_summary['error_issues']}")
    print(f"  Warnings: {validation_summary['warning_issues']}")
    print(f"  Info:     {validation_summary['info_issues']}")
    
    print(f"\nDetected Anomalies:")
    anomaly_summary = stats['anomaly_summary']
    print(f"  Total:            {anomaly_summary['total_anomalies']}")
    print(f"  Statistical:      {anomaly_summary['outliers']}")
    print(f"  Performance Up:   {anomaly_summary['performance_spikes']}")
    print(f"  Performance Down: {anomaly_summary['performance_drops']}")
    print(f"  Temporal:         {anomaly_summary['temporal_anomalies']}")
    
    print(f"\nRecommendations:")
    for i, recommendation in enumerate(report.recommendations, 1):
        print(f"  {i}. {recommendation}")
    
    # Critical issues
    critical_items = report.get_critical_issues()
    if critical_items:
        print(f"\n[CRITICAL] ISSUES REQUIRING IMMEDIATE ATTENTION:")
        for item in critical_items:
            if hasattr(item, 'message'):  # ValidationIssue
                print(f"  - {item.message}")
            else:  # AnomalyDetection
                print(f"  - {item.description}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()