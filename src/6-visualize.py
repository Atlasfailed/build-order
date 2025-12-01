#!/usr/bin/env python3
"""
Visualization Generator
=======================

Generates interactive HTML dashboards for build order analysis.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict, Counter
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config" / "config.json"

class Visualizer:
    """Generate interactive visualizations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.paths = config['paths']
        
        # Data
        self.position_clusters = {}
        self.build_clusters = {}
        self.analysis_report = {}
        self.position_assignments = []
        
        # Output directory
        self.viz_dir = SCRIPT_DIR / self.paths['visualizations']
        self.viz_dir.mkdir(parents=True, exist_ok=True)
    
    def load_data(self):
        """Load all analysis results."""
        print("📂 Loading data...")
        
        # Position clusters
        pos_file = SCRIPT_DIR / self.paths['analysis'] / "position-clusters.json"
        with open(pos_file, 'r') as f:
            self.position_clusters = json.load(f)
        
        # Build clusters
        build_file = SCRIPT_DIR / self.paths['analysis'] / "build-clusters.json"
        with open(build_file, 'r') as f:
            self.build_clusters = json.load(f)
        
        # Analysis report
        report_file = SCRIPT_DIR / self.paths['reports'] / "complete-analysis.json"
        with open(report_file, 'r') as f:
            self.analysis_report = json.load(f)
        
        # Position assignments
        assign_file = SCRIPT_DIR / self.paths['analysis'] / "position-assignments.jsonl"
        self.position_assignments = []
        with open(assign_file, 'r') as f:
            for line in f:
                if line.strip():
                    self.position_assignments.append(json.loads(line))
        
        print(f"  ✓ Loaded {len(self.position_clusters['clusters'])} position clusters")
        print(f"  ✓ Loaded build clusters for {len(self.build_clusters['positions'])} positions")
        print(f"  ✓ Loaded {len(self.position_assignments)} position assignments")
    
    def create_position_map(self) -> go.Figure:
        """Create 2D map of position clusters."""
        # Prepare data
        clusters_data = []
        for cluster_id, cluster_info in self.position_clusters['clusters'].items():
            clusters_data.append({
                'cluster_id': cluster_id,
                'position_name': cluster_info['position_name'],
                'x': cluster_info['centroid']['x'],
                'z': cluster_info['centroid']['z'],
                'num_samples': cluster_info['num_samples'],
                'avg_skill': cluster_info['avg_skill']
            })
        
        df = pd.DataFrame(clusters_data)
        
        # Create scatter plot
        fig = px.scatter(
            df,
            x='x',
            y='z',
            size='num_samples',
            color='position_name',
            hover_data=['position_name', 'num_samples', 'avg_skill'],
            title='Supreme Isthmus - Position Clusters',
            labels={'x': 'X Coordinate', 'z': 'Z Coordinate'},
            width=900,
            height=900
        )
        
        # Add position labels
        for _, row in df.iterrows():
            fig.add_annotation(
                x=row['x'],
                y=row['z'],
                text=row['position_name'],
                showarrow=False,
                yshift=15,
                font=dict(size=10, color='black', family='Arial Black')
            )
        
        fig.update_layout(
            plot_bgcolor='#e8f4ea',
            showlegend=True,
            font=dict(size=12)
        )
        
        return fig
    
    def create_win_rate_comparison(self) -> go.Figure:
        """Create win rate comparison by position."""
        position_reports = self.analysis_report['position_reports']
        
        positions = []
        overall_wr = []
        high_skill_wr = []
        mid_skill_wr = []
        
        for pos_name, report in sorted(position_reports.items()):
            positions.append(pos_name)
            overall_wr.append(report['win_rate'] * 100)
            high_skill_wr.append(report['high_skill_win_rate'] * 100)
            mid_skill_wr.append(report['mid_skill_win_rate'] * 100)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Overall',
            x=positions,
            y=overall_wr,
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='High Skill (>40)',
            x=positions,
            y=high_skill_wr,
            marker_color='darkblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Mid Skill (30-40)',
            x=positions,
            y=mid_skill_wr,
            marker_color='orange'
        ))
        
        fig.update_layout(
            title='Win Rates by Position and Skill Level',
            xaxis_title='Position',
            yaxis_title='Win Rate (%)',
            barmode='group',
            height=500,
            font=dict(size=12)
        )
        
        return fig
    
    def create_archetype_success_chart(self, position_name: str) -> go.Figure:
        """Create success rate chart for build archetypes."""
        archetypes = [
            a for a in self.analysis_report['archetype_analysis']
            if a['position_name'] == position_name
        ]
        
        if not archetypes:
            return None
        
        # Sort by frequency
        archetypes = sorted(archetypes, key=lambda x: x['frequency'], reverse=True)[:10]
        
        names = [f"Build {i+1}" for i in range(len(archetypes))]
        win_rates = [a['win_rate'] * 100 for a in archetypes]
        frequencies = [a['frequency'] for a in archetypes]
        avg_skills = [a['avg_skill'] for a in archetypes]
        
        # Color based on performance
        colors = ['green' if a['performance'] == 'above_average' else 'red' for a in archetypes]
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Win Rate', 'Frequency'),
            vertical_spacing=0.15,
            row_heights=[0.5, 0.5]
        )
        
        # Win rate chart
        fig.add_trace(
            go.Bar(
                x=names,
                y=win_rates,
                marker_color=colors,
                hovertemplate='%{y:.1f}%<br>Avg Skill: %{customdata:.1f}<extra></extra>',
                customdata=avg_skills,
                showlegend=False
            ),
            row=1, col=1
        )
        
        # Frequency chart
        fig.add_trace(
            go.Bar(
                x=names,
                y=frequencies,
                marker_color='lightblue',
                showlegend=False
            ),
            row=2, col=1
        )
        
        # Add baseline win rate line
        baseline = self.analysis_report['position_reports'][position_name]['win_rate'] * 100
        fig.add_hline(
            y=baseline,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Position Average: {baseline:.1f}%",
            row=1, col=1
        )
        
        fig.update_layout(
            title=f'{position_name.upper()} - Build Archetype Performance',
            height=600,
            font=dict(size=11)
        )
        
        fig.update_yaxes(title_text="Win Rate (%)", row=1, col=1)
        fig.update_yaxes(title_text="# of Games", row=2, col=1)
        
        return fig
    
    def create_build_order_timeline(self, position_name: str) -> go.Figure:
        """Create timeline visualization of build orders."""
        archetypes = self.build_clusters['positions'].get(position_name, {}).get('archetypes', [])
        
        if not archetypes:
            return None
        
        # Show top 3 archetypes
        top_archetypes = sorted(archetypes, key=lambda x: x['frequency'], reverse=True)[:3]
        
        fig = go.Figure()
        
        for i, archetype in enumerate(top_archetypes):
            sequence = archetype['representative_sequence'][:15]  # First 15 buildings
            
            # Create timeline
            times = list(range(len(sequence)))
            
            fig.add_trace(go.Scatter(
                x=times,
                y=[i] * len(times),
                mode='markers+text',
                marker=dict(size=15, symbol='circle'),
                text=sequence,
                textposition="top center",
                textfont=dict(size=9),
                name=f"Build {i+1} ({archetype['frequency']} games, {archetype['win_rate']*100:.1f}% WR)",
                hovertext=[f"{j+1}. {unit}" for j, unit in enumerate(sequence)],
                hoverinfo='text+name'
            ))
        
        fig.update_layout(
            title=f'{position_name.upper()} - Build Order Timelines (Top 3 Archetypes)',
            xaxis_title='Build Order Position',
            yaxis=dict(
                tickmode='array',
                tickvals=list(range(len(top_archetypes))),
                ticktext=[f'Build {i+1}' for i in range(len(top_archetypes))]
            ),
            height=400,
            font=dict(size=11),
            showlegend=True,
            hovermode='closest'
        )
        
        return fig
    
    def create_skill_comparison_chart(self) -> go.Figure:
        """Create chart comparing high-skill vs mid-skill patterns."""
        skill_comp = self.analysis_report['skill_comparisons']
        
        # Top openings comparison
        high_skill = skill_comp['high_skill_openings'][:5]
        mid_skill = skill_comp['mid_skill_openings'][:5]
        
        high_names = [f"HS-{i+1}" for i in range(len(high_skill))]
        mid_names = [f"MS-{i+1}" for i in range(len(mid_skill))]
        
        high_pct = [o['percentage'] for o in high_skill]
        mid_pct = [o['percentage'] for o in mid_skill]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='High Skill (>40)',
            x=high_names,
            y=high_pct,
            marker_color='darkblue',
            hovertemplate='%{y:.1f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='Mid Skill (30-40)',
            x=mid_names,
            y=mid_pct,
            marker_color='orange',
            hovertemplate='%{y:.1f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title='Most Common Openings by Skill Level (Top 5)',
            xaxis_title='Opening Pattern',
            yaxis_title='Frequency (%)',
            height=400,
            font=dict(size=12),
            barmode='group'
        )
        
        return fig
    
    def create_timing_differences_chart(self) -> go.Figure:
        """Create chart showing timing differences between skill levels."""
        timing_diffs = self.analysis_report['skill_comparisons']['timing_differences'][:10]
        
        if not timing_diffs:
            return None
        
        units = [t['unit'] for t in timing_diffs]
        differences = [t['difference_ms'] / 1000 for t in timing_diffs]  # Convert to seconds
        
        colors = ['green' if t['high_skill_faster'] else 'red' for t in timing_diffs]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=differences,
            y=units,
            orientation='h',
            marker_color=colors,
            hovertemplate='%{x:.1f}s difference<extra></extra>'
        ))
        
        fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="black")
        
        fig.update_layout(
            title='Build Timing Differences: High-Skill vs Mid-Skill<br><sub>Green = High-skill builds faster | Red = High-skill builds slower</sub>',
            xaxis_title='Time Difference (seconds)',
            yaxis_title='Unit Type',
            height=500,
            font=dict(size=11)
        )
        
        return fig
    
    def create_main_dashboard(self):
        """Create main HTML dashboard combining all visualizations."""
        print("\n🎨 Creating visualizations...")
        
        # Generate all figures
        position_map = self.create_position_map()
        win_rate_chart = self.create_win_rate_comparison()
        skill_comparison = self.create_skill_comparison_chart()
        timing_chart = self.create_timing_differences_chart()
        
        # Generate position-specific charts
        position_charts = {}
        for position_name in self.build_clusters['positions'].keys():
            archetype_chart = self.create_archetype_success_chart(position_name)
            timeline_chart = self.create_build_order_timeline(position_name)
            if archetype_chart and timeline_chart:
                position_charts[position_name] = {
                    'archetype': archetype_chart,
                    'timeline': timeline_chart
                }
        
        print(f"  ✓ Created {len(position_charts)} position-specific visualizations")
        
        # Create HTML
        html_parts = []
        
        # Header
        html_parts.append("""
<!DOCTYPE html>
<html>
<head>
    <title>BAR Position Analysis - Supreme Isthmus</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 5px 0;
            font-size: 1.1em;
        }
        .section {
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-top: 0;
        }
        .chart {
            margin: 20px 0;
        }
        .position-tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
        }
        .tab:hover {
            background: #764ba2;
        }
        .tab.active {
            background: #764ba2;
        }
        .position-content {
            display: none;
        }
        .position-content.active {
            display: block;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            font-size: 2em;
        }
        .stat-card p {
            margin: 0;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎮 BAR Position Analysis</h1>
        <h2>Supreme Isthmus v2.1</h2>
        <p>Build Order Analysis & Success Patterns</p>
    </div>
""")
        
        # Statistics cards
        total_games = len(set(a['replayId'] for a in self.position_assignments))
        total_positions = len(self.position_assignments)
        total_archetypes = sum(
            len(pos_data['archetypes'])
            for pos_data in self.build_clusters['positions'].values()
        )
        
        html_parts.append(f"""
    <div class="section">
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{total_games}</h3>
                <p>Games Analyzed</p>
            </div>
            <div class="stat-card">
                <h3>{total_positions}</h3>
                <p>Player Positions</p>
            </div>
            <div class="stat-card">
                <h3>{len(self.position_clusters['clusters'])}</h3>
                <p>Position Clusters</p>
            </div>
            <div class="stat-card">
                <h3>{total_archetypes}</h3>
                <p>Build Archetypes</p>
            </div>
        </div>
    </div>
""")
        
        # Overview charts
        html_parts.append("""
    <div class="section">
        <h2>📍 Position Overview</h2>
        <div class="chart" id="position-map"></div>
        <div class="chart" id="win-rate-chart"></div>
    </div>
""")
        
        # Skill comparison
        html_parts.append("""
    <div class="section">
        <h2>🏆 High-Skill Player Analysis</h2>
        <div class="chart" id="skill-comparison"></div>
        <div class="chart" id="timing-differences"></div>
    </div>
""")
        
        # Position-specific sections
        html_parts.append("""
    <div class="section">
        <h2>📊 Position-Specific Analysis</h2>
        <div class="position-tabs">
""")
        
        for i, position_name in enumerate(sorted(position_charts.keys())):
            active = 'active' if i == 0 else ''
            html_parts.append(f'            <button class="tab {active}" onclick="showPosition(\'{position_name}\')">{position_name.upper()}</button>\n')
        
        html_parts.append("""
        </div>
""")
        
        for i, (position_name, charts) in enumerate(sorted(position_charts.items())):
            active = 'active' if i == 0 else ''
            html_parts.append(f"""
        <div id="pos-{position_name}" class="position-content {active}">
            <div class="chart" id="archetype-{position_name}"></div>
            <div class="chart" id="timeline-{position_name}"></div>
        </div>
""")
        
        html_parts.append("""
    </div>
    
    <script>
        // Position map
        var positionMapData = """ + position_map.to_json() + """;
        Plotly.newPlot('position-map', positionMapData.data, positionMapData.layout);
        
        // Win rate chart
        var winRateData = """ + win_rate_chart.to_json() + """;
        Plotly.newPlot('win-rate-chart', winRateData.data, winRateData.layout);
        
        // Skill comparison
        var skillCompData = """ + skill_comparison.to_json() + """;
        Plotly.newPlot('skill-comparison', skillCompData.data, skillCompData.layout);
        
""")
        
        if timing_chart:
            html_parts.append("""
        // Timing differences
        var timingData = """ + timing_chart.to_json() + """;
        Plotly.newPlot('timing-differences', timingData.data, timingData.layout);
""")
        
        # Position-specific charts
        for position_name, charts in position_charts.items():
            html_parts.append(f"""
        // {position_name} - archetype chart
        var archData_{position_name.replace('-', '_')} = """ + charts['archetype'].to_json() + """;
        Plotly.newPlot('archetype-{position_name}', archData_{position_name.replace('-', '_')}.data, archData_{position_name.replace('-', '_')}.layout);
        
        // {position_name} - timeline chart
        var timelineData_{position_name.replace('-', '_')} = """ + charts['timeline'].to_json() + """;
        Plotly.newPlot('timeline-{position_name}', timelineData_{position_name.replace('-', '_')}.data, timelineData_{position_name.replace('-', '_')}.layout);
""")
        
        html_parts.append("""
        
        // Tab switching
        function showPosition(positionName) {
            // Hide all
            document.querySelectorAll('.position-content').forEach(el => {
                el.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(el => {
                el.classList.remove('active');
            });
            
            // Show selected
            document.getElementById('pos-' + positionName).classList.add('active');
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
""")
        
        # Save HTML
        output_file = self.viz_dir / "index.html"
        with open(output_file, 'w') as f:
            f.write(''.join(html_parts))
        
        print(f"\n✓ Main dashboard saved to: {output_file}")
    
    def run(self):
        """Run the full visualization pipeline."""
        print("\n=== Visualization Generator ===\n")
        
        self.load_data()
        self.create_main_dashboard()
        
        print("\n✓ Visualization complete!")
        print(f"\n🌐 Open {self.viz_dir / 'index.html'} in your browser to view the dashboard")

def main():
    """Main execution function."""
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Run visualizer
    visualizer = Visualizer(config)
    visualizer.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during visualization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

