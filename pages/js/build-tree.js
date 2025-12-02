// Build Order Tree Explorer JavaScript

const positions = [
    'position_front-1',
    'position_front-2',
    'position_eco',
    'position_air',
    'position_geo',
    'position_geo-sea',
    'position_pond',
    'position_long-sea'
];

let currentData = null;
let currentFilters = {
    minSkill: null,
    playerName: null
};
let allPlayerNames = new Set();

// Initialize position selector
function initPositionSelector() {
    const selector = document.getElementById('positionSelector');
    positions.forEach(pos => {
        const btn = document.createElement('button');
        btn.className = 'position-btn';
        btn.textContent = pos.replace('position_', '').replace(/-/g, ' ').toUpperCase();
        btn.onclick = () => loadPosition(pos);
        selector.appendChild(btn);
    });
}

// Load CSV data for a position
async function loadPosition(positionName) {
    try {
        // Update active button
        document.querySelectorAll('.position-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent === positionName.replace('position_', '').replace(/-/g, ' ').toUpperCase()) {
                btn.classList.add('active');
            }
        });
        
        const treeContainer = document.getElementById('treeContainer');
        treeContainer.innerHTML = '<div class="loading">Loading data...</div>';
        
        const response = await fetch(`../output/position_csvs/${positionName}.csv`);
        if (!response.ok) {
            throw new Error(`Failed to load CSV file: ${response.statusText}`);
        }
        const csvText = await response.text();
        
        currentData = parseCSV(csvText);
        
        // Apply current filters and build tree
        applyFiltersAndRebuild();
        showStats(currentData);
        
    } catch (error) {
        document.getElementById('treeContainer').innerHTML = 
            `<div class="error">Error loading data: ${error.message}</div>`;
    }
}

// Parse CSV data
function parseCSV(csvText) {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',');
    
    const data = {
        players: [],
        builds: []
    };
    
    // Find player name row
    const playerNameRow = lines[1].split(',');
    
    // Parse each column (player)
    for (let col = 1; col < headers.length; col++) {
        const player = {
            id: headers[col],
            name: playerNameRow[col],
            skill: 0,
            builds: []
        };
        
        // Get player skill (row 4)
        const skillRow = lines[4].split(',');
        player.skill = parseFloat(skillRow[col]) || 0;
        
        // Add player name to global set for autocomplete
        if (player.name) {
            allPlayerNames.add(player.name);
        }
        
        // Get build orders (starting from row with "Build 1")
        let buildNum = 1;
        for (let row = 0; row < lines.length; row++) {
            if (lines[row].startsWith(`Build ${buildNum}`)) {
                const buildRow = lines[row].split(',');
                if (buildRow[col]) {
                    const buildItem = buildRow[col].trim();
                    if (buildItem && buildItem !== '---') {
                        // Extract item name (remove timestamp)
                        const match = buildItem.match(/^(.+?)\s*\(/);
                        if (match) {
                            player.builds.push(match[1].trim());
                        }
                    }
                }
                buildNum++;
            }
        }
        
        if (player.builds.length > 0) {
            data.players.push(player);
        }
    }
    
    return data;
}

// Combine consecutive same items into "x3" format
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

// Build tree structure
function buildTree(data) {
    const tree = {};
    
    // Build tree from all players' build orders
    data.players.forEach(player => {
        const combined = combineConsecutive(player.builds);
        let currentNode = tree;
        
        combined.forEach((item, depth) => {
            const key = item.count > 1 ? `${item.name} x${item.count}` : item.name;
            
            if (!currentNode[key]) {
                currentNode[key] = {
                    name: key,
                    count: 0,
                    totalSkill: 0,
                    children: {}
                };
            }
            
            currentNode[key].count++;
            currentNode[key].totalSkill += player.skill;
            
            currentNode = currentNode[key].children;
        });
    });
    
    renderTree(tree);
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
            .sort((a, b) => b.count - a.count); // Sort by count descending
        
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
function showStats(data) {
    const statsContainer = document.getElementById('statsContainer');
    const statsContent = document.getElementById('statsContent');
    
    statsContainer.style.display = 'block';
    
    const totalPlayers = data.players.length;
    const avgSkill = (data.players.reduce((sum, p) => sum + p.skill, 0) / totalPlayers).toFixed(1);
    const maxSkill = Math.max(...data.players.map(p => p.skill)).toFixed(1);
    const minSkill = Math.min(...data.players.map(p => p.skill)).toFixed(1);
    
    // Get most common first build
    const firstBuilds = {};
    data.players.forEach(p => {
        if (p.builds.length > 0) {
            const first = p.builds[0];
            firstBuilds[first] = (firstBuilds[first] || 0) + 1;
        }
    });
    const mostCommon = Object.entries(firstBuilds)
        .sort((a, b) => b[1] - a[1])[0];
    
    let mostCommonHtml = '';
    if (mostCommon && mostCommon.length > 0) {
        mostCommonHtml = `<p><strong>Most Common First Build:</strong> ${mostCommon[0]} (${mostCommon[1]} players, ${(mostCommon[1]/totalPlayers*100).toFixed(1)}%)</p>`;
    }
    
    statsContent.innerHTML = `
        <p><strong>Total Players:</strong> ${totalPlayers}</p>
        <p><strong>Average Skill:</strong> ${avgSkill} (range: ${minSkill} - ${maxSkill})</p>
        ${mostCommonHtml}
    `;
}

// Apply filters and rebuild tree
function applyFiltersAndRebuild() {
    if (!currentData) return;
    
    // Filter players based on current filters
    let filteredData = {
        players: currentData.players.filter(player => {
            // Apply skill filter
            if (currentFilters.minSkill !== null && player.skill < currentFilters.minSkill) {
                return false;
            }
            
            // Apply player name filter
            if (currentFilters.playerName && player.name !== currentFilters.playerName) {
                return false;
            }
            
            return true;
        }),
        builds: currentData.builds
    };
    
    buildTree(filteredData);
    showStats(filteredData);
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
        
        // Filter player names
        const matches = Array.from(allPlayerNames)
            .filter(name => name.toLowerCase().includes(value))
            .sort()
            .slice(0, 10);
        
        if (matches.length === 0) {
            suggestions.style.display = 'none';
            return;
        }
        
        // Show suggestions
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
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (e.target !== input && e.target !== suggestions) {
            suggestions.style.display = 'none';
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initPositionSelector();
    setupPlayerAutocomplete();
    
    // Apply filters button
    document.getElementById('applyFiltersBtn').addEventListener('click', function() {
        const minSkillInput = document.getElementById('minSkillInput').value;
        const playerNameInput = document.getElementById('playerSearchInput').value.trim();
        
        currentFilters.minSkill = minSkillInput ? parseFloat(minSkillInput) : null;
        currentFilters.playerName = playerNameInput || null;
        
        applyFiltersAndRebuild();
    });
    
    // Clear filters button
    document.getElementById('clearFiltersBtn').addEventListener('click', function() {
        document.getElementById('minSkillInput').value = '';
        document.getElementById('playerSearchInput').value = '';
        currentFilters.minSkill = null;
        currentFilters.playerName = null;
        
        applyFiltersAndRebuild();
    });
});
