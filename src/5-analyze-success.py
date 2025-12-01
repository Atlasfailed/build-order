#!/usr/bin/env python3
"""
Success Analysis
================

Analyzes build order success rates and identifies what high-skill players do differently.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict, Counter
from scipy import stats
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config" / "config.json"

class SuccessAnalyzer:
    """Analyze build order success rates."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.analysis_config = config['analysis']
        self.paths = config['paths']
        
        # Thresholds
        self.high_skill_threshold = self.analysis_config['high_skill_threshold']
        self.mid_skill_threshold = self.analysis_config['mid_skill_threshold']
        
        # Data
        self.builds: List[Dict[str, Any]] = []
        self.position_assignments: Dict[str, Dict[str, Any]] = {}
        self.build_clusters: Dict[str, Any] = {}
        
        # Results
        self.position_reports: Dict[str, Dict[str, Any]] = {}
        self.archetype_analysis: List[Dict[str, Any]] = []
        self.skill_comparisons: Dict[str, Dict[str, Any]] = {}
    
    def load_data(self):
        """Load all required data."""
        print("📂 Loading data...")
        
        # Load builds
        builds_file = SCRIPT_DIR / self.paths['parsed'] / "builds.jsonl"
        self.builds = []
        with open(builds_file, 'r') as f:
            for line in f:
                if line.strip():
                    self.builds.append(json.loads(line))
        print(f"  ✓ Loaded {len(self.builds)} build orders")
        
        # Load position assignments
        assignments_file = SCRIPT_DIR / self.paths['analysis'] / "position-assignments.jsonl"
        with open(assignments_file, 'r') as f:
            for line in f:
                if line.strip():
                    assignment = json.loads(line)
                    key = f"{assignment['replayId']}_{assignment['playerId']}"
                    self.position_assignments[key] = assignment
        print(f"  ✓ Loaded {len(self.position_assignments)} position assignments")
        
        # Load build clusters
        clusters_file = SCRIPT_DIR / self.paths['analysis'] / "build-clusters.json"
        with open(clusters_file, 'r') as f:
            self.build_clusters = json.load(f)
        print(f"  ✓ Loaded build clusters for {len(self.build_clusters['positions'])} positions")
    
    def analyze_position_overview(self):
        """Analyze overall statistics for each position."""
        print("\n📊 Analyzing position overview...")
        
        # Organize builds by position
        builds_by_position = defaultdict(list)
        for build in self.builds:
            key = f"{build['replayId']}_{build['playerId']}"
            if key in self.position_assignments:
                position = self.position_assignments[key]['position_name']
                build['position_name'] = position
                builds_by_position[position].append(build)
        
        # Calculate statistics for each position
        for position, builds in builds_by_position.items():
            total = len(builds)
            wins = sum(1 for b in builds if b['wonGame'])
            win_rate = wins / total if total > 0 else 0
            
            avg_skill = np.mean([b['skill'] for b in builds])
            
            # Skill-stratified stats
            high_skill_builds = [b for b in builds if b['skill'] >= self.high_skill_threshold]
            mid_skill_builds = [b for b in builds if self.mid_skill_threshold <= b['skill'] < self.high_skill_threshold]
            
            high_skill_win_rate = (
                sum(1 for b in high_skill_builds if b['wonGame']) / len(high_skill_builds)
                if high_skill_builds else 0
            )
            mid_skill_win_rate = (
                sum(1 for b in mid_skill_builds if b['wonGame']) / len(mid_skill_builds)
                if mid_skill_builds else 0
            )
            
            self.position_reports[position] = {
                'position_name': position,
                'total_games': total,
                'win_rate': float(win_rate),
                'avg_skill': float(avg_skill),
                'high_skill_games': len(high_skill_builds),
                'high_skill_win_rate': float(high_skill_win_rate),
                'mid_skill_games': len(mid_skill_builds),
                'mid_skill_win_rate': float(mid_skill_win_rate),
            }
    
    def analyze_archetype_success(self):
        """Analyze success rates for each build order archetype."""
        print("\n🎯 Analyzing archetype success rates...")
        
        for position_name, position_data in self.build_clusters['positions'].items():
            archetypes = position_data['archetypes']
            
            for archetype in archetypes:
                archetype_name = archetype['name']
                
                # Statistical significance test
                # Compare win rate to overall position win rate
                position_win_rate = self.position_reports[position_name]['win_rate']
                archetype_wins = int(archetype['win_rate'] * archetype['frequency'])
                archetype_total = archetype['frequency']
                
                # Binomial test
                if archetype_total >= 10:  # Only test if enough samples
                    result = stats.binomtest(
                        archetype_wins,
                        archetype_total,
                        position_win_rate,
                        alternative='two-sided'
                    )
                    p_value = result.pvalue
                    significantly_different = p_value < 0.05
                else:
                    p_value = None
                    significantly_different = False
                
                analysis = {
                    **archetype,
                    'position_baseline_win_rate': float(position_win_rate),
                    'win_rate_difference': float(archetype['win_rate'] - position_win_rate),
                    'p_value': float(p_value) if p_value is not None else None,
                    'statistically_significant': significantly_different,
                    'performance': 'above_average' if archetype['win_rate'] > position_win_rate else 'below_average'
                }
                
                self.archetype_analysis.append(analysis)
        
        # Sort by win rate difference
        self.archetype_analysis.sort(key=lambda x: abs(x['win_rate_difference']), reverse=True)
    
    def analyze_skill_differences(self):
        """Analyze what high-skill players do differently."""
        print("\n🏆 Analyzing high-skill player patterns...")
        
        # Organize builds by skill level
        high_skill_builds = [b for b in self.builds if b['skill'] >= self.high_skill_threshold]
        mid_skill_builds = [b for b in self.builds if self.mid_skill_threshold <= b['skill'] < self.high_skill_threshold]
        
        # Analyze opening builds
        def extract_opening_units(builds, n=5):
            """Extract first N units from builds."""
            openings = []
            for build in builds:
                if len(build['buildOrder']) >= n:
                    opening = tuple(b['unitDisplayName'] for b in build['buildOrder'][:n])
                    openings.append(opening)
            return Counter(openings)
        
        high_skill_openings = extract_opening_units(high_skill_builds, 5)
        mid_skill_openings = extract_opening_units(mid_skill_builds, 5)
        
        # Find most common openings for each skill level
        top_high_skill = high_skill_openings.most_common(10)
        top_mid_skill = mid_skill_openings.most_common(10)
        
        # Analyze timing differences
        def calculate_avg_timings(builds):
            """Calculate average timing for each unit type."""
            timings = defaultdict(list)
            for build in builds:
                seen_units = set()
                for b in build['buildOrder']:
                    unit = b['unitDisplayName']
                    if unit not in seen_units:
                        timings[unit].append(b['time'])
                        seen_units.add(unit)
            
            return {
                unit: {
                    'avg_time': float(np.mean(times)),
                    'std_time': float(np.std(times)),
                    'count': len(times)
                }
                for unit, times in timings.items()
                if len(times) >= 10  # Only include if enough samples
            }
        
        high_skill_timings = calculate_avg_timings(high_skill_builds)
        mid_skill_timings = calculate_avg_timings(mid_skill_builds)
        
        # Find significant timing differences
        timing_differences = []
        for unit in set(high_skill_timings.keys()) & set(mid_skill_timings.keys()):
            high_avg = high_skill_timings[unit]['avg_time']
            mid_avg = mid_skill_timings[unit]['avg_time']
            difference = high_avg - mid_avg
            
            if abs(difference) > 5000:  # More than 5 seconds difference
                timing_differences.append({
                    'unit': unit,
                    'high_skill_avg': high_avg,
                    'mid_skill_avg': mid_avg,
                    'difference_ms': difference,
                    'high_skill_faster': difference < 0
                })
        
        timing_differences.sort(key=lambda x: abs(x['difference_ms']), reverse=True)
        
        self.skill_comparisons = {
            'high_skill_openings': [
                {'opening': list(opening), 'count': count, 'percentage': count/len(high_skill_builds)*100}
                for opening, count in top_high_skill
            ],
            'mid_skill_openings': [
                {'opening': list(opening), 'count': count, 'percentage': count/len(mid_skill_builds)*100}
                for opening, count in top_mid_skill
            ],
            'timing_differences': timing_differences[:20],  # Top 20
            'sample_sizes': {
                'high_skill': len(high_skill_builds),
                'mid_skill': len(mid_skill_builds)
            }
        }
    
    def save_results(self):
        """Save analysis results."""
        reports_dir = SCRIPT_DIR / self.paths['reports']
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        print("\n💾 Saving results...")
        
        # 1. Position summary CSV
        position_df = pd.DataFrame(list(self.position_reports.values()))
        position_df = position_df.sort_values('win_rate', ascending=False)
        position_csv = reports_dir / "position-summary.csv"
        position_df.to_csv(position_csv, index=False)
        print(f"  ✓ {position_csv}")
        
        # 2. Build success rates CSV
        archetype_df = pd.DataFrame(self.archetype_analysis)
        archetype_df = archetype_df.sort_values('win_rate_difference', ascending=False)
        archetype_csv = reports_dir / "build-success-rates.csv"
        archetype_df.to_csv(archetype_csv, index=False)
        print(f"  ✓ {archetype_csv}")
        
        # 3. High-skill patterns JSON
        high_skill_json = reports_dir / "high-skill-patterns.json"
        with open(high_skill_json, 'w') as f:
            json.dump(self.skill_comparisons, f, indent=2)
        print(f"  ✓ {high_skill_json}")
        
        # 4. Complete analysis report JSON
        full_report = {
            'position_reports': self.position_reports,
            'archetype_analysis': self.archetype_analysis,
            'skill_comparisons': self.skill_comparisons,
            'thresholds': {
                'high_skill': self.high_skill_threshold,
                'mid_skill': self.mid_skill_threshold
            }
        }
        
        full_report_json = reports_dir / "complete-analysis.json"
        with open(full_report_json, 'w') as f:
            json.dump(full_report, f, indent=2)
        print(f"  ✓ {full_report_json}")
    
    def print_summary(self):
        """Print analysis summary."""
        print("\n=== Success Analysis Summary ===\n")
        
        print("Position Win Rates:")
        for position, report in sorted(self.position_reports.items(), key=lambda x: x[1]['win_rate'], reverse=True):
            print(f"  {position:15s}: {report['win_rate']*100:5.1f}% "
                  f"(High-skill: {report['high_skill_win_rate']*100:5.1f}%, "
                  f"Mid-skill: {report['mid_skill_win_rate']*100:5.1f}%)")
        
        print("\n\nTop Performing Build Archetypes:")
        for i, archetype in enumerate(self.archetype_analysis[:5], 1):
            print(f"\n{i}. {archetype['name']}")
            print(f"   Win rate: {archetype['win_rate']*100:.1f}% "
                  f"(+{archetype['win_rate_difference']*100:.1f}% vs position average)")
            print(f"   Frequency: {archetype['frequency']} games")
            print(f"   Avg skill: {archetype['avg_skill']:.1f}")
            if archetype['statistically_significant']:
                print(f"   ✓ Statistically significant (p={archetype['p_value']:.4f})")
        
        print("\n\nHigh-Skill Player Insights:")
        print(f"  Sample size: {self.skill_comparisons['sample_sizes']['high_skill']} games")
        print(f"\n  Most common opening (top 3):")
        for i, opening_data in enumerate(self.skill_comparisons['high_skill_openings'][:3], 1):
            opening = ' → '.join(opening_data['opening'])
            print(f"    {i}. {opening} ({opening_data['percentage']:.1f}%)")
        
        if self.skill_comparisons['timing_differences']:
            print(f"\n  Significant timing differences:")
            for diff in self.skill_comparisons['timing_differences'][:3]:
                faster_slower = "faster" if diff['high_skill_faster'] else "slower"
                print(f"    {diff['unit']}: {abs(diff['difference_ms'])/1000:.1f}s {faster_slower}")
    
    def run(self):
        """Run the full success analysis pipeline."""
        print("\n=== Success Analysis ===\n")
        
        self.load_data()
        self.analyze_position_overview()
        self.analyze_archetype_success()
        self.analyze_skill_differences()
        self.save_results()
        self.print_summary()
        
        print("\n✓ Success analysis complete!")

def main():
    """Main execution function."""
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Run analysis
    analyzer = SuccessAnalyzer(config)
    analyzer.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

