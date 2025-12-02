// Build Order Tree Explorer - Parquet Version
// Uses hyparquet library to read Parquet files

console.log('build-tree-parquet.js loading...');

import { parquetRead } from 'https://cdn.jsdelivr.net/npm/hyparquet@1.6.0/+esm';

console.log('parquetRead imported successfully');

const positions = [
    { id: 0, name: 'front-1', displayName: 'FRONT 1' },
    { id: 1, name: 'front-2', displayName: 'FRONT 2' },
    { id: 2, name: 'geo', displayName: 'GEO' },
    { id: 3, name: 'geo-sea', displayName: 'GEO SEA' },
    { id: 4, name: 'air', displayName: 'AIR' },
    { id: 5, name: 'eco', displayName: 'ECO' },
    { id: 6, name: 'pond', displayName: 'POND' },
    { id: 7, name: 'long-sea', displayName: 'LONG SEA' }
];

let lookupData = {
    units: null,
    players: null,
    positions: null
};

let currentData = {
    index: null,
    builds: null,
    positionId: null
};

let currentFilters = {
    minSkill: null,
    playerName: null,
    faction: null
};

let allPlayerNames = new Set();

// Column schemas for each parquet file type
const SCHEMAS = {
    index: ['replay_id', 'player_id', 'skill', 'rank', 'won_game', 'position_id', 'distance_from_centroid', 'faction'],
    builds: ['replay_id', 'player_id', 'build_index', 'time', 'unit_id'],
    lookup_units: ['unit_id', 'unit_name'],
    lookup_players: ['player_id', 'player_name'],
    lookup_positions: ['position_id', 'position_name'],
    lookup_replays: ['replay_id', 'replay_name']
};

// Load a Parquet file
async function loadParquet(url, schemaKey = null) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const arrayBuffer = await response.arrayBuffer();
        
        return new Promise((resolve, reject) => {
            parquetRead({
                file: arrayBuffer,
                onComplete: data => {
                    console.log('Parquet data loaded from', url, '- rows:', data.length);
                    
                    // hyparquet returns an array of row arrays
                    if (Array.isArray(data) && data.length > 0) {
                        // If we have a schema, convert arrays to objects
                        if (schemaKey && SCHEMAS[schemaKey]) {
                            const columns = SCHEMAS[schemaKey];
                            const rows = data.map(row => {
                                const obj = {};
                                columns.forEach((col, idx) => {
                                    obj[col] = row[idx];
                                });
                                return obj;
                            });
                            resolve(rows);
                        } else {
                            // No schema provided, return as-is (arrays)
                            resolve(data);
                        }
                    } else {
                        resolve([]);
                    }
                }
            });
        });
    } catch (error) {
        console.error(`Error loading ${url}:`, error);
        throw error;
    }
}

// Initialize - load lookup tables
async function init() {
    console.log('Initializing...');
    
    // Initialize position buttons immediately
    initPositionSelector();
    setupFilterButtons();
    
    try {
        console.log('Loading lookup tables...');
        
        [lookupData.units, lookupData.players, lookupData.positions] = await Promise.all([
            loadParquet('data/optimized/lookup_units.parquet', 'lookup_units'),
            loadParquet('data/optimized/lookup_players.parquet', 'lookup_players'),
            loadParquet('data/optimized/lookup_positions.parquet', 'lookup_positions')
        ]);
        
        console.log('Lookup tables loaded:', {
            units: lookupData.units.length,
            players: lookupData.players.length,
            positions: lookupData.positions.length
        });
        
        // Debug: Check first few units
        console.log('Sample units:', lookupData.units.slice(0, 5));
        
        // Build player name set for autocomplete
        lookupData.players.forEach(p => allPlayerNames.add(p.player_name));
        
        setupPlayerAutocomplete();
        
        console.log('Initialization complete');
        
    } catch (error) {
        console.error('Initialization error:', error);
        document.getElementById('treeContainer').innerHTML = 
            `<div class="error">Failed to initialize: ${error.message}<br><br>Please check the browser console for more details.</div>`;
    }
}

// Initialize position selector
function initPositionSelector() {
    console.log('Setting up position selector buttons...');
    // Buttons are now in HTML, just set up click handlers
    const buttons = document.querySelectorAll('.position-btn');
    console.log('Found', buttons.length, 'position buttons');
    buttons.forEach((btn, idx) => {
        if (idx < positions.length) {
            btn.onclick = () => {
                console.log('Position button clicked:', positions[idx].name);
                loadPosition(positions[idx].id, positions[idx].name);
            };
        }
    });
}

// Load position data
async function loadPosition(positionId, positionName) {
    try {
        // Update active button
        document.querySelectorAll('.position-btn').forEach((btn, idx) => {
            btn.classList.toggle('active', positions[idx].id === positionId);
        });
        
        const treeContainer = document.getElementById('treeContainer');
        treeContainer.innerHTML = '<div class="loading">Loading data...</div>';
        
        console.log(`Loading position ${positionId} (${positionName})...`);
        
        // Load index and builds for this position
        const [index, builds] = await Promise.all([
            loadParquet('data/optimized/index.parquet', 'index'),
            loadParquet(`data/optimized/builds_by_position/builds_position_${positionId}_${positionName}.parquet`, 'builds')
        ]);
        
        console.log('Data loaded:', {
            indexRows: index.length,
            buildRows: builds.length
        });
        
        // Filter index for this position
        currentData.index = index.filter(row => row.position_id === positionId);
        currentData.builds = builds;
        currentData.positionId = positionId;
        
        console.log('Filtered data:', {
            players: currentData.index.length,
            builds: currentData.builds.length
        });
        
        // Sample first player to see data structure
        if (currentData.index.length > 0) {
            console.log('Sample player:', currentData.index[0]);
        }
        if (currentData.builds.length > 0) {
            console.log('Sample build:', currentData.builds[0]);
        }
        
        // Apply filters and build tree
        applyFiltersAndRebuild();
        
    } catch (error) {
        console.error('Error loading position:', error);
        document.getElementById('treeContainer').innerHTML = 
            `<div class="error">Error loading position: ${error.message}</div>`;
    }
}

// Build tree structure from filtered data
function buildTree(filteredPlayers) {
    if (!filteredPlayers || filteredPlayers.length === 0) {
        document.getElementById('treeContainer').innerHTML = 
            '<div class="loading">No players match the current filters</div>';
        return;
    }
    
    console.log('Building tree for', filteredPlayers.length, 'players');
    
    // Create player ID set for quick lookup
    const playerSet = new Set();
    const playerMap = new Map();
    
    filteredPlayers.forEach(player => {
        const key = `${player.replay_id}-${player.player_id}`;
        playerSet.add(key);
        playerMap.set(key, player);
    });
    
    // Get builds for these players
    const playerBuilds = currentData.builds.filter(build => {
        const key = `${build.replay_id}-${build.player_id}`;
        return playerSet.has(key);
    });
    
    console.log('Filtered builds:', playerBuilds.length);
    
    // Group builds by player
    const buildsByPlayer = new Map();
    playerBuilds.forEach(build => {
        const key = `${build.replay_id}-${build.player_id}`;
        if (!buildsByPlayer.has(key)) {
            buildsByPlayer.set(key, []);
        }
        buildsByPlayer.get(key).push(build);
    });
    
    // Sort builds by build_index for each player
    buildsByPlayer.forEach((builds, key) => {
        builds.sort((a, b) => a.build_index - b.build_index);
    });
    
    // Build tree
    const tree = {};
    
    buildsByPlayer.forEach((builds, key) => {
        const player = playerMap.get(key);
        if (!player) return;
        
        // Convert unit IDs to names and combine consecutive items
        const buildNames = builds.map(b => getUnitName(b.unit_id));
        const combined = combineConsecutive(buildNames);
        
        let currentNode = tree;
        
        combined.forEach((item) => {
            const nodeKey = item.count > 1 ? `${item.name} x${item.count}` : item.name;
            
            if (!currentNode[nodeKey]) {
                currentNode[nodeKey] = {
                    name: nodeKey,
                    count: 0,
                    totalSkill: 0,
                    children: {}
                };
            }
            
            currentNode[nodeKey].count++;
            currentNode[nodeKey].totalSkill += player.skill;
            
            currentNode = currentNode[nodeKey].children;
        });
    });
    
    renderTree(tree);
    showStats(filteredPlayers, buildsByPlayer.size);
}

// Get unit name from ID
function getUnitName(unitId) {
    // Handle BigInt comparison - Parquet may return BigInt for integer columns
    const unit = lookupData.units.find(u => {
        const lookupId = typeof u.unit_id === 'bigint' ? Number(u.unit_id) : u.unit_id;
        return lookupId === unitId;
    });
    return unit ? unit.unit_name : `Unit ${unitId}`;
}

// Get player name from ID
function getPlayerName(playerId) {
    // Handle BigInt comparison - Parquet may return BigInt for integer columns
    const player = lookupData.players.find(p => {
        const lookupId = typeof p.player_id === 'bigint' ? Number(p.player_id) : p.player_id;
        return lookupId === playerId;
    });
    return player ? player.player_name : `Player ${playerId}`;
}

// Combine consecutive same items
function combineConsecutive(items) {
    if (!items || items.length === 0) return [];
    
    const combined = [];
    let current = { name: items[0], count: 1 };
    
    for (let i = 1; i < items.length; i++) {
        if (items[i] === current.name) {
            current.count++;
        } else {
            combined.push(current);
            current = { name: items[i], count: 1 };
        }
    }
    combined.push(current);
    
    return combined;
}

// Render tree HTML
function renderTree(tree) {
    const container = document.getElementById('treeContainer');
    container.innerHTML = '';
    
    const rootNodes = Object.values(tree);
    if (rootNodes.length === 0) {
        container.innerHTML = '<div class="loading">No build data available</div>';
        return;
    }
    
    // Sort root nodes by count
    rootNodes.sort((a, b) => b.count - a.count);
    
    rootNodes.forEach(node => {
        container.appendChild(createNodeElement(node, 0));
    });
}

// Create a node element
function createNodeElement(node, depth) {
    const nodeDiv = document.createElement('div');
    nodeDiv.className = 'tree-node';
    
    const avgSkill = (node.totalSkill / node.count).toFixed(1);
    const hasChildren = Object.keys(node.children).length > 0;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'node-content';
    
    const expandIcon = document.createElement('span');
    expandIcon.className = 'expand-icon';
    expandIcon.textContent = hasChildren ? '▶' : '•';
    if (!hasChildren) expandIcon.classList.add('no-children');
    
    const itemName = document.createElement('span');
    itemName.className = 'item-name';
    itemName.textContent = node.name;
    
    const countBadge = document.createElement('span');
    countBadge.className = 'item-count';
    countBadge.textContent = `${node.count} players`;
    
    const skillBadge = document.createElement('span');
    skillBadge.className = 'item-skill';
    skillBadge.textContent = `Avg: ${avgSkill}`;
    
    contentDiv.appendChild(expandIcon);
    contentDiv.appendChild(itemName);
    contentDiv.appendChild(countBadge);
    contentDiv.appendChild(skillBadge);
    
    const childrenDiv = document.createElement('div');
    childrenDiv.className = 'children';
    
    if (hasChildren) {
        const childNodes = Object.values(node.children)
            .sort((a, b) => b.count - a.count);
        
        childNodes.forEach(child => {
            childrenDiv.appendChild(createNodeElement(child, depth + 1));
        });
        
        contentDiv.onclick = () => {
            childrenDiv.classList.toggle('expanded');
            expandIcon.textContent = childrenDiv.classList.contains('expanded') ? '▼' : '▶';
        };
    }
    
    nodeDiv.appendChild(contentDiv);
    nodeDiv.appendChild(childrenDiv);
    
    return nodeDiv;
}

// Show statistics
function showStats(players, playerCount) {
    const statsContainer = document.getElementById('statsContainer');
    const statsContent = document.getElementById('statsContent');
    
    statsContainer.style.display = 'block';
    
    const totalPlayers = players.length;
    if (totalPlayers === 0) {
        statsContent.innerHTML = '<p>No players match filters</p>';
        return;
    }
    
    const avgSkill = (players.reduce((sum, p) => sum + p.skill, 0) / totalPlayers).toFixed(1);
    const maxSkill = Math.max(...players.map(p => p.skill)).toFixed(1);
    const minSkill = Math.min(...players.map(p => p.skill)).toFixed(1);
    
    const wonCount = players.filter(p => p.won_game).length;
    const winRate = ((wonCount / totalPlayers) * 100).toFixed(1);
    
    // Count factions
    const factions = {};
    players.forEach(p => {
        factions[p.faction] = (factions[p.faction] || 0) + 1;
    });
    
    const factionHtml = Object.entries(factions)
        .sort((a, b) => b[1] - a[1])
        .map(([faction, count]) => {
            const pct = ((count / totalPlayers) * 100).toFixed(1);
            return `${faction}: ${count} (${pct}%)`;
        })
        .join(', ');
    
    statsContent.innerHTML = `
        <p><strong>Total Players:</strong> ${totalPlayers}</p>
        <p><strong>Players with Builds:</strong> ${playerCount}</p>
        <p><strong>Average Skill:</strong> ${avgSkill} (range: ${minSkill} - ${maxSkill})</p>
        <p><strong>Win Rate:</strong> ${winRate}% (${wonCount} wins)</p>
        <p><strong>Factions:</strong> ${factionHtml}</p>
    `;
}

// Apply filters and rebuild
function applyFiltersAndRebuild() {
    if (!currentData.index) {
        console.log('No index data available');
        return;
    }
    
    console.log('Current filters:', currentFilters);
    console.log('Total players in index:', currentData.index.length);
    
    let filtered = currentData.index.filter(player => {
        // Apply skill filter
        if (currentFilters.minSkill !== null && player.skill < currentFilters.minSkill) {
            return false;
        }
        
        // Apply faction filter
        if (currentFilters.faction && player.faction !== currentFilters.faction) {
            return false;
        }
        
        // Apply player name filter
        if (currentFilters.playerName) {
            const playerName = getPlayerName(player.player_id);
            if (playerName !== currentFilters.playerName) {
                return false;
            }
        }
        
        return true;
    });
    
    console.log('Filtered players:', filtered.length);
    
    buildTree(filtered);
}

// Setup player name autocomplete
function setupPlayerAutocomplete() {
    const input = document.getElementById('playerSearchInput');
    const suggestions = document.getElementById('playerSuggestions');
    
    input.addEventListener('input', function() {
        const value = this.value.toLowerCase();
        suggestions.innerHTML = '';
        
        if (value.length < 2) {
            suggestions.style.display = 'none';
            return;
        }
        
        const matches = Array.from(allPlayerNames)
            .filter(name => name.toLowerCase().includes(value))
            .sort()
            .slice(0, 10);
        
        if (matches.length === 0) {
            suggestions.style.display = 'none';
            return;
        }
        
        matches.forEach(name => {
            const div = document.createElement('div');
            div.textContent = name;
            div.style.padding = '8px 12px';
            div.style.cursor = 'pointer';
            div.style.borderBottom = '1px solid var(--border-color)';
            
            div.addEventListener('mouseenter', function() {
                this.style.background = 'var(--hover-bg)';
            });
            
            div.addEventListener('mouseleave', function() {
                this.style.background = '';
            });
            
            div.addEventListener('click', function() {
                input.value = name;
                suggestions.style.display = 'none';
            });
            
            suggestions.appendChild(div);
        });
        
        suggestions.style.display = 'block';
    });
    
    document.addEventListener('click', function(e) {
        if (e.target !== input && e.target !== suggestions) {
            suggestions.style.display = 'none';
        }
    });
}

// Setup filter buttons
function setupFilterButtons() {
    document.getElementById('applyFiltersBtn').addEventListener('click', function() {
        const minSkillInput = document.getElementById('minSkillInput').value;
        const factionSelect = document.getElementById('factionSelect').value;
        const playerNameInput = document.getElementById('playerSearchInput').value.trim();
        
        currentFilters.minSkill = minSkillInput ? parseFloat(minSkillInput) : null;
        currentFilters.faction = factionSelect || null;
        currentFilters.playerName = playerNameInput || null;
        
        applyFiltersAndRebuild();
    });
    
    document.getElementById('clearFiltersBtn').addEventListener('click', function() {
        document.getElementById('minSkillInput').value = '';
        document.getElementById('factionSelect').value = '';
        document.getElementById('playerSearchInput').value = '';
        currentFilters.minSkill = null;
        currentFilters.faction = null;
        currentFilters.playerName = null;
        
        applyFiltersAndRebuild();
    });
}

// Initialize on page load
console.log('Setting up DOMContentLoaded listener...');
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded fired!');
    init();
});
