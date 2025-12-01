import * as fs from 'fs';
import * as path from 'path';

interface Player {
  playerId: number;
  name: string;
  teamId: number;
}

interface AllyTeam {
  allyTeamId: number;
  Players: Player[];
}

interface ReplayData {
  id: string;
  fileName: string;
  AllyTeams: AllyTeam[];
}

// Read the labeling links file
const labelingFilePath = path.join(__dirname, 'POSITION-LABELING-LINKS.txt');
const labelingContent = fs.readFileSync(labelingFilePath, 'utf-8');

// Parse the existing file to extract game filenames and replay IDs
const gameEntries: Array<{ fileName: string; replayId: string }> = [];
const lines = labelingContent.split('\n');

for (let i = 0; i < lines.length; i++) {
  const line = lines[i].trim();
  if (line.startsWith('Game: ')) {
    const fileName = line.replace('Game: ', '');
    const nextLine = lines[i + 1]?.trim() || '';
    if (nextLine.startsWith('Link: ')) {
      const link = nextLine.replace('Link: ', '');
      const replayId = link.split('/').pop() || '';
      gameEntries.push({ fileName, replayId });
    }
  }
}

console.log(`Found ${gameEntries.length} games to process`);

// Read replay JSONs
const replayJsonsDir = path.join(__dirname, '../archive/data/replay_jsons');

// Build new content
let newContent = 'POSITION LABELING TOOL - PLAYER INFORMATION\n';
newContent += '='.repeat(50) + '\n\n';
newContent += 'For each game, manually add the position for each player.\n';
newContent += 'Format: Player | Team | Position (leave Position empty, to be filled manually)\n\n';
newContent += '='.repeat(50) + '\n\n';

for (const entry of gameEntries) {
  const jsonFilePath = path.join(replayJsonsDir, `${entry.replayId}.json`);
  
  newContent += `Game: ${entry.fileName}\n`;
  newContent += `Link: https://bar-rts.com/replays/${entry.replayId}\n`;
  newContent += `---\n`;

  if (fs.existsSync(jsonFilePath)) {
    try {
      const replayData: ReplayData = JSON.parse(fs.readFileSync(jsonFilePath, 'utf-8'));
      
      // Sort ally teams by allyTeamId
      const sortedAllyTeams = replayData.AllyTeams.sort((a, b) => a.allyTeamId - b.allyTeamId);
      
      for (const allyTeam of sortedAllyTeams) {
        newContent += `\nTeam ${allyTeam.allyTeamId}:\n`;
        
        // Sort players by playerId
        const sortedPlayers = allyTeam.Players.sort((a, b) => a.playerId - b.playerId);
        
        for (const player of sortedPlayers) {
          newContent += `  ${player.name} | Team ${allyTeam.allyTeamId} | Position: _____\n`;
        }
      }
      
      newContent += '\n';
    } catch (error) {
      newContent += `  ERROR: Could not parse JSON file\n\n`;
      console.error(`Error processing ${entry.replayId}:`, error);
    }
  } else {
    newContent += `  ERROR: JSON file not found\n\n`;
    console.error(`JSON file not found: ${jsonFilePath}`);
  }
  
  newContent += '='.repeat(50) + '\n\n';
}

// Write the new file
const outputFilePath = path.join(__dirname, 'POSITION-LABELING-LINKS-WITH-PLAYERS.txt');
fs.writeFileSync(outputFilePath, newContent, 'utf-8');

console.log(`\nOutput written to: ${outputFilePath}`);
console.log(`Processed ${gameEntries.length} games`);
