#!/usr/bin/env python3
"""
Build Order Clustering
======================

Clusters build orders per position to identify common patterns.
Uses sequence similarity and timing analysis.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
from sklearn.cluster import AgglomerativeClustering
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config" / "config.json"

class BuildOrderClusterer:
    """Cluster build orders to find common patterns."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clustering_config = config['analysis']['build_clustering']
        self.paths = config['paths']
        
        # Data
        self.builds: List[Dict[str, Any]] = []
        self.position_assignments: Dict[str, Dict[str, Any]] = {}
        self.builds_by_position: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Results
        self.position_clusters: Dict[str, Dict[int, List[Dict[str, Any]]]] = defaultdict(dict)
        self.position_archetypes: Dict[str, List[Dict[str, Any]]] = {}
    
    def load_data(self):
        """Load build orders and position assignments."""
        # Load builds
        builds_file = SCRIPT_DIR / self.paths['parsed'] / "builds.jsonl"
        if not builds_file.exists():
            print(f"❌ Error: builds.jsonl not found")
            print("   Run 2-parse-demos.ts first")
            sys.exit(1)
        
        self.builds = []
        with open(builds_file, 'r') as f:
            for line in f:
                if line.strip():
                    self.builds.append(json.loads(line))
        
        print(f"✓ Loaded {len(self.builds)} build orders")
        
        # Load position assignments
        assignments_file = SCRIPT_DIR / self.paths['analysis'] / "position-assignments.jsonl"
        if not assignments_file.exists():
            print(f"❌ Error: position-assignments.jsonl not found")
            print("   Run 3-cluster-positions.py first")
            sys.exit(1)
        
        with open(assignments_file, 'r') as f:
            for line in f:
                if line.strip():
                    assignment = json.loads(line)
                    # Create unique key for each player in each game
                    key = f"{assignment['replayId']}_{assignment['playerId']}"
                    self.position_assignments[key] = assignment
        
        print(f"✓ Loaded position assignments for {len(self.position_assignments)} players")
    
    def organize_builds_by_position(self):
        """Organize build orders by position cluster."""
        print("\n📊 Organizing builds by position...")
        
        for build in self.builds:
            key = f"{build['replayId']}_{build['playerId']}"
            
            if key in self.position_assignments:
                position_name = self.position_assignments[key]['position_name']
                build['position_name'] = position_name
                self.builds_by_position[position_name].append(build)
        
        for position_name, builds in self.builds_by_position.items():
            print(f"  {position_name}: {len(builds)} build orders")
    
    def build_order_to_sequence(self, build_order: List[Dict[str, Any]], max_length: int = 20) -> List[str]:
        """Convert build order to a sequence of unit types."""
        sequence = []
        for build in build_order[:max_length]:
            unit_name = build['unitDisplayName']
            sequence.append(unit_name)
        return sequence
    
    def sequence_similarity(self, seq1: List[str], seq2: List[str]) -> float:
        """
        Calculate similarity between two build order sequences.
        Uses a combination of:
        - Longest common subsequence
        - Order preservation
        - Early game weight (first buildings matter more)
        """
        if not seq1 or not seq2:
            return 0.0
        
        # Pad sequences to same length
        max_len = max(len(seq1), len(seq2))
        seq1_padded = seq1 + [''] * (max_len - len(seq1))
        seq2_padded = seq2 + [''] * (max_len - len(seq2))
        
        # Calculate weighted similarity
        similarity = 0.0
        total_weight = 0.0
        
        for i in range(max_len):
            # Early buildings have higher weight
            weight = 1.0 / (1.0 + i * 0.1)
            total_weight += weight
            
            if seq1_padded[i] and seq2_padded[i]:
                if seq1_padded[i] == seq2_padded[i]:
                    similarity += weight
                elif seq1_padded[i].split()[0] == seq2_padded[i].split()[0]:
                    # Partial match (e.g., same factory type)
                    similarity += weight * 0.5
        
        return similarity / total_weight if total_weight > 0 else 0.0
    
    def calculate_distance_matrix(self, builds: List[Dict[str, Any]]) -> np.ndarray:
        """Calculate pairwise distance matrix for build orders."""
        n = len(builds)
        distance_matrix = np.zeros((n, n))
        
        sequences = [self.build_order_to_sequence(b['buildOrder']) for b in builds]
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self.sequence_similarity(sequences[i], sequences[j])
                distance = 1.0 - similarity
                distance_matrix[i, j] = distance
                distance_matrix[j, i] = distance
        
        return distance_matrix
    
    def cluster_builds_for_position(self, position_name: str, builds: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Cluster build orders for a specific position."""
        if len(builds) < self.clustering_config['min_cluster_size']:
            print(f"  {position_name}: Too few samples ({len(builds)}), skipping")
            return {}
        
        print(f"\n  Clustering {position_name} ({len(builds)} builds)...")
        
        # Calculate distance matrix
        distance_matrix = self.calculate_distance_matrix(builds)
        
        # Perform hierarchical clustering
        max_clusters = min(self.clustering_config['max_clusters'], len(builds) // 2)
        
        # Use condensed distance matrix for linkage
        condensed_dist = squareform(distance_matrix)
        Z = linkage(condensed_dist, method='average')
        
        # Get cluster labels
        labels = fcluster(Z, max_clusters, criterion='maxclust')
        
        # Organize results
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            clusters[int(label)].append(builds[i])
        
        # Filter out very small clusters
        min_size = self.clustering_config['min_cluster_size']
        filtered_clusters = {
            label: items for label, items in clusters.items()
            if len(items) >= min_size
        }
        
        print(f"    Found {len(filtered_clusters)} clusters")
        
        return filtered_clusters
    
    def extract_archetypes(self, position_name: str, clusters: Dict[int, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Extract representative archetypes from clusters."""
        archetypes = []
        
        for cluster_id, cluster_builds in clusters.items():
            # Find most common sequence in cluster
            sequences = [self.build_order_to_sequence(b['buildOrder']) for b in cluster_builds]
            
            # Get most common first N buildings
            first_buildings = defaultdict(Counter)
            for seq in sequences:
                for i, unit in enumerate(seq[:10]):  # First 10 buildings
                    if unit:
                        first_buildings[i][unit] += 1
            
            # Construct representative sequence
            representative_sequence = []
            for i in range(10):
                if first_buildings[i]:
                    most_common = first_buildings[i].most_common(1)[0][0]
                    representative_sequence.append(most_common)
            
            # Calculate statistics
            win_rate = sum(1 for b in cluster_builds if b['wonGame']) / len(cluster_builds)
            avg_skill = np.mean([b['skill'] for b in cluster_builds])
            
            # Find example builds (best players)
            cluster_builds_sorted = sorted(cluster_builds, key=lambda x: x['skill'], reverse=True)
            examples = [
                {
                    'playerName': b['playerName'],
                    'skill': b['skill'],
                    'wonGame': b['wonGame'],
                    'replayId': b['replayId'],
                    'buildOrder': [unit['unitDisplayName'] for unit in b['buildOrder'][:10]]
                }
                for b in cluster_builds_sorted[:3]
            ]
            
            archetype = {
                'cluster_id': cluster_id,
                'position_name': position_name,
                'name': f"{position_name}_archetype_{cluster_id}",
                'representative_sequence': representative_sequence,
                'frequency': len(cluster_builds),
                'win_rate': float(win_rate),
                'avg_skill': float(avg_skill),
                'examples': examples
            }
            
            archetypes.append(archetype)
        
        # Sort by frequency
        archetypes.sort(key=lambda x: x['frequency'], reverse=True)
        
        return archetypes
    
    def save_results(self):
        """Save clustering results."""
        analysis_dir = SCRIPT_DIR / self.paths['analysis']
        
        # Prepare output
        output = {
            'clustering_params': self.clustering_config,
            'positions': {},
            'summary': {
                'total_builds': len(self.builds),
                'positions_analyzed': len(self.builds_by_position),
                'total_archetypes': sum(len(archetypes) for archetypes in self.position_archetypes.values())
            }
        }
        
        for position_name, archetypes in self.position_archetypes.items():
            output['positions'][position_name] = {
                'total_builds': len(self.builds_by_position[position_name]),
                'archetypes': archetypes
            }
        
        # Save to file
        output_file = analysis_dir / "build-clusters.json"
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Build clusters saved to: {output_file}")
    
    def print_summary(self):
        """Print summary of build order clustering."""
        print("\n=== Build Order Clustering Summary ===")
        print(f"Total build orders analyzed: {len(self.builds)}")
        print(f"Positions analyzed: {len(self.builds_by_position)}")
        
        for position_name, archetypes in self.position_archetypes.items():
            print(f"\n{position_name.upper()}:")
            print(f"  Total builds: {len(self.builds_by_position[position_name])}")
            print(f"  Archetypes found: {len(archetypes)}")
            
            for i, archetype in enumerate(archetypes[:3], 1):  # Show top 3
                print(f"\n  Archetype {i}: {archetype['name']}")
                print(f"    Frequency: {archetype['frequency']} ({archetype['frequency']/len(self.builds_by_position[position_name])*100:.1f}%)")
                print(f"    Win rate: {archetype['win_rate']*100:.1f}%")
                print(f"    Avg skill: {archetype['avg_skill']:.1f}")
                print(f"    Opening: {' → '.join(archetype['representative_sequence'][:5])}")
    
    def run(self):
        """Run the full build order clustering pipeline."""
        print("\n=== Build Order Clustering ===\n")
        
        self.load_data()
        self.organize_builds_by_position()
        
        # Cluster builds for each position
        print("\n🔍 Clustering build orders by position...")
        for position_name, builds in self.builds_by_position.items():
            clusters = self.cluster_builds_for_position(position_name, builds)
            if clusters:
                self.position_clusters[position_name] = clusters
                archetypes = self.extract_archetypes(position_name, clusters)
                self.position_archetypes[position_name] = archetypes
        
        self.save_results()
        self.print_summary()
        
        print("\n✓ Build order clustering complete!")

def main():
    """Main execution function."""
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Run clustering
    clusterer = BuildOrderClusterer(config)
    clusterer.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during build clustering: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

