#!/usr/bin/env python3
"""
Position Clustering
===================

Clusters spawn positions into roles (front-1, front-2, air, eco, etc.)
Handles map symmetry and identifies positions geometrically.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import cdist
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config" / "config.json"

class PositionClusterer:
    """Cluster spawn positions with symmetry handling."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.analysis_config = config['analysis']['position_clustering']
        self.paths = config['paths']
        
        # Map dimensions
        self.map_width = self.analysis_config['map_width']
        self.map_height = self.analysis_config['map_height']
        
        # Clustering parameters
        self.eps = self.analysis_config['eps']
        self.min_samples = self.analysis_config['min_samples']
        
        # Results
        self.positions: List[Dict[str, Any]] = []
        self.clusters: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self.cluster_info: Dict[int, Dict[str, Any]] = {}
    
    def load_positions(self):
        """Load positions from JSONL file."""
        positions_file = SCRIPT_DIR / self.paths['parsed'] / "positions.jsonl"
        
        if not positions_file.exists():
            print(f"❌ Error: positions.jsonl not found at {positions_file}")
            print("   Run 2-parse-demos.ts first to parse replays")
            sys.exit(1)
        
        self.positions = []
        with open(positions_file, 'r') as f:
            for line in f:
                if line.strip():
                    self.positions.append(json.loads(line))
        
        print(f"✓ Loaded {len(self.positions)} player positions from {len(set(p['replayId'] for p in self.positions))} games")
    
    def normalize_by_team(self, position: Dict[str, Any]) -> Tuple[float, float]:
        """
        Normalize coordinates by team side to handle map symmetry.
        Supreme Isthmus is symmetric along the top-left to bottom-right diagonal.
        """
        x = position['startPos']['x']
        z = position['startPos']['z']
        
        # Determine which team based on position
        # Team 0 typically spawns in top-right (higher x, lower z)
        # Team 1 typically spawns in bottom-left (lower x, higher z)
        
        # Check which side of the diagonal this position is on
        # Diagonal goes from (0, map_height) to (map_width, 0)
        # Points above diagonal have: z > map_height - (map_height/map_width) * x
        
        center_x = self.map_width / 2
        center_z = self.map_height / 2
        
        # If position is in bottom-left quadrant (Team 1 side), mirror it to top-right
        if x < center_x and z > center_z:
            # Mirror across the diagonal
            # For diagonal symmetry: swap x and z, then mirror
            x_norm = self.map_width - x
            z_norm = self.map_height - z
            return x_norm, z_norm
        
        return x, z
    
    def cluster_positions_by_team(self):
        """Cluster positions separately for each ally team."""
        print("\n🔍 Clustering positions...")
        
        # Group positions by ally team
        team_positions = defaultdict(list)
        for pos in self.positions:
            team_positions[pos['allyTeamId']].append(pos)
        
        # We'll normalize all positions to one side for clustering
        all_normalized_coords = []
        all_positions_with_coords = []
        
        for pos in self.positions:
            x_norm, z_norm = self.normalize_by_team(pos)
            all_normalized_coords.append([x_norm, z_norm])
            all_positions_with_coords.append({
                **pos,
                'normalized_x': x_norm,
                'normalized_z': z_norm
            })
        
        # Perform clustering on normalized coordinates
        coords_array = np.array(all_normalized_coords)
        
        clustering = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric='euclidean'
        ).fit(coords_array)
        
        labels = clustering.labels_
        
        # Organize results
        for i, (label, pos_data) in enumerate(zip(labels, all_positions_with_coords)):
            if label != -1:  # Ignore noise points
                pos_data['cluster_id'] = int(label)
                self.clusters[int(label)].append(pos_data)
        
        # Calculate cluster statistics
        for cluster_id, cluster_positions in self.clusters.items():
            coords = np.array([[p['normalized_x'], p['normalized_z']] for p in cluster_positions])
            centroid = coords.mean(axis=0)
            
            # Calculate statistics
            self.cluster_info[cluster_id] = {
                'cluster_id': cluster_id,
                'centroid': {
                    'x': float(centroid[0]),
                    'z': float(centroid[1])
                },
                'num_samples': len(cluster_positions),
                'players': len(set(p['playerName'] for p in cluster_positions)),
                'games': len(set(p['replayId'] for p in cluster_positions)),
                'avg_skill': float(np.mean([p['skill'] for p in cluster_positions])),
            }
        
        print(f"✓ Found {len(self.clusters)} position clusters")
        print(f"  Noise points (unclustered): {sum(1 for label in labels if label == -1)}")
    
    def assign_position_labels(self):
        """Assign descriptive labels to position clusters based on geometry."""
        print("\n🏷️  Assigning position labels...")
        
        # Calculate geometric properties for each cluster
        for cluster_id, info in self.cluster_info.items():
            centroid = info['centroid']
            x, z = centroid['x'], centroid['z']
            
            # Distance from center of map
            center_x = self.map_width / 2
            center_z = self.map_height / 2
            dist_from_center = np.sqrt((x - center_x)**2 + (z - center_z)**2)
            
            # Distance from enemy base (opposite corner)
            dist_from_enemy = np.sqrt(x**2 + z**2)
            
            # Determine position type based on geometry
            # Front positions: closest to enemy
            # Back positions: furthest from enemy
            # Side positions: along edges
            
            info['dist_from_center'] = float(dist_from_center)
            info['dist_from_enemy'] = float(dist_from_enemy)
            
            # Simple heuristic for position naming
            # We'll rank by distance to enemy
        
        # Sort clusters by distance to enemy (closest = front)
        sorted_clusters = sorted(
            self.cluster_info.items(),
            key=lambda x: x[1]['dist_from_enemy']
        )
        
        # Assign position names
        position_names = [
            "front-1",    # Closest to enemy
            "front-2",    # Second closest
            "mid-1",      # Middle positions
            "mid-2",
            "eco-1",      # Economic/safe positions
            "eco-2",
            "air",        # Usually back position for air player
            "pond",       # Special positions
        ]
        
        for i, (cluster_id, info) in enumerate(sorted_clusters):
            if i < len(position_names):
                position_name = position_names[i]
            else:
                position_name = f"position-{i+1}"
            
            self.cluster_info[cluster_id]['position_name'] = position_name
            print(f"  Cluster {cluster_id}: {position_name} ({info['num_samples']} samples)")
    
    def save_results(self):
        """Save clustering results."""
        analysis_dir = SCRIPT_DIR / self.paths['analysis']
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare output data
        output = {
            'clustering_params': {
                'algorithm': self.analysis_config['algorithm'],
                'eps': self.eps,
                'min_samples': self.min_samples,
                'map_dimensions': {
                    'width': self.map_width,
                    'height': self.map_height
                }
            },
            'clusters': self.cluster_info,
            'total_positions': len(self.positions),
            'total_clusters': len(self.clusters),
            'created_at': str(Path(__file__).stat().st_mtime)
        }
        
        # Save cluster information
        output_file = analysis_dir / "position-clusters.json"
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Cluster information saved to: {output_file}")
        
        # Save detailed position assignments
        detailed_file = analysis_dir / "position-assignments.jsonl"
        with open(detailed_file, 'w') as f:
            for cluster_id, positions in self.clusters.items():
                cluster_name = self.cluster_info[cluster_id]['position_name']
                for pos in positions:
                    assignment = {
                        'replayId': pos['replayId'],
                        'playerName': pos['playerName'],
                        'playerId': pos['playerId'],
                        'allyTeamId': pos['allyTeamId'],
                        'skill': pos['skill'],
                        'wonGame': pos['wonGame'],
                        'original_position': pos['startPos'],
                        'normalized_position': {
                            'x': pos['normalized_x'],
                            'z': pos['normalized_z']
                        },
                        'cluster_id': cluster_id,
                        'position_name': cluster_name
                    }
                    f.write(json.dumps(assignment) + '\n')
        
        print(f"✓ Position assignments saved to: {detailed_file}")
    
    def print_summary(self):
        """Print summary statistics."""
        print("\n=== Position Clustering Summary ===")
        print(f"Total positions analyzed: {len(self.positions)}")
        print(f"Total clusters found: {len(self.clusters)}")
        print(f"\nCluster Details:")
        
        # Sort by position name for better readability
        sorted_by_name = sorted(
            self.cluster_info.items(),
            key=lambda x: x[1].get('position_name', '')
        )
        
        for cluster_id, info in sorted_by_name:
            print(f"\n  {info['position_name'].upper()}:")
            print(f"    Samples: {info['num_samples']}")
            print(f"    Unique players: {info['players']}")
            print(f"    Games: {info['games']}")
            print(f"    Avg skill: {info['avg_skill']:.1f}")
            print(f"    Centroid: ({info['centroid']['x']:.0f}, {info['centroid']['z']:.0f})")
    
    def run(self):
        """Run the full clustering pipeline."""
        print("\n=== Position Clustering ===\n")
        
        self.load_positions()
        self.cluster_positions_by_team()
        self.assign_position_labels()
        self.save_results()
        self.print_summary()
        
        print("\n✓ Position clustering complete!")

def main():
    """Main execution function."""
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Run clustering
    clusterer = PositionClusterer(config)
    clusterer.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during clustering: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

