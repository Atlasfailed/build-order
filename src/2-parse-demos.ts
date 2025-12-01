import * as path from "path";
import * as fs from "fs";
import { DemoParser, DemoModel, isPacket } from "../../src/index";

interface Config {
    analysis: {
        time_window_seconds: number;
    };
    paths: {
        replays: string;
        parsed: string;
    };
}

interface BuildCommand {
    time: number;
    unitName: string;
    unitDisplayName: string;
    builderType: string;
}

interface PlayerPosition {
    replayId: string;
    fileName: string;
    gameDate: string;
    playerName: string;
    playerId: number;
    teamId: number;
    allyTeamId: number;
    skill: number;
    rank: number | null;
    faction: string;
    startPos: { x: number, z: number };
    wonGame: boolean;
}

interface PlayerBuildOrder {
    replayId: string;
    fileName: string;
    gameDate: string;
    playerName: string;
    playerId: number;
    teamId: number;
    allyTeamId: number;
    skill: number;
    rank: number | null;
    position: { x: number, z: number };
    wonGame: boolean;
    buildOrder: BuildCommand[];
}

interface GameData {
    replayId: string;
    fileName: string;
    gameDate: string;
    duration: number;
    mapName: string;
    winningAllyTeamIds: number[];
    players: Array<{
        name: string;
        playerId: number;
        teamId: number;
        allyTeamId: number;
        skill: number;
        rank: number | null;
        faction: string;
        startPos?: { x: number, z: number };
    }>;
}

interface UnitNames {
    units: {
        names: { [key: string]: string };
    };
}

// Load configuration
const configPath = path.join(__dirname, "..", "config", "config.json");
const config: Config = JSON.parse(fs.readFileSync(configPath, "utf8"));

// Load human-readable unit names
let unitNames: { [key: string]: string } = {};
try {
    const unitsJson: UnitNames = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "units.json"), "utf8"));
    unitNames = unitsJson.units.names;
} catch (error) {
    console.warn("⚠ Warning: Could not load units.json, using unit IDs instead");
}

function extractSkillFromString(skillStr: string | undefined): number {
    if (!skillStr) return 0;
    try {
        // Extract skill value from string like "[35.81]"
        const match = skillStr.match(/\[([\d.]+)\]/);
        if (match) {
            return parseFloat(match[1]);
        }
    } catch (e) {
        // Ignore
    }
    return 0;
}

function getBuilderType(unitName?: string, builtUnitName?: string): string {
    if (!unitName) return "unknown";
    
    const unit = unitName.toLowerCase();
    
    // Commanders
    if (unit.includes("armcom") || unit.includes("corcom")) {
        return "commander";
    }
    
    // Construction units
    if (unit.includes("armcv") || unit.includes("corcv")) {
        return "vehicle-con";
    }
    if (unit.includes("armck") || unit.includes("corck")) {
        return "bot-con";
    }
    if (unit.includes("armca") || unit.includes("corca")) {
        return "air-con";
    }
    if (unit.includes("armcs") || unit.includes("corcs")) {
        return "ship-con";
    }
    
    // Factory types
    if (unit.includes("bot") || unit.includes("kbot")) {
        return "bot-factory";
    }
    if (unit.includes("veh")) {
        return "vehicle-factory";
    }
    if (unit.includes("air") || unit.includes("plane")) {
        return "air-factory";
    }
    if (unit.includes("ship") || unit.includes("sea")) {
        return "ship-factory";
    }
    if (unit.includes("hover")) {
        return "hover-factory";
    }
    
    return "other";
}

async function parseSingleDemo(demoPath: string, replayId: string): Promise<{ positions: PlayerPosition[], builds: PlayerBuildOrder[], gameData: GameData } | null> {
    const parser = new DemoParser({
        verbose: false,
        // Include packets we need for build orders and start positions
        includePackets: [
            DemoModel.Packet.ID.COMMAND,
            DemoModel.Packet.ID.AICOMMAND,
            DemoModel.Packet.ID.LUAMSG,
            DemoModel.Packet.ID.STARTPOS,  // Include start position packets
        ],
    });

    const buildOrders = new Map<number, BuildCommand[]>();
    let unitDefs: string[] = [];
    const timeLimit = config.analysis.time_window_seconds * 1000; // Convert to ms

    parser.onPacket.add((packet) => {
        if (isPacket(packet, DemoModel.Packet.ID.LUAMSG) && packet.data?.data?.name === "UNITDEFS") {
            unitDefs = packet.data.data.data || [];
            return;
        }

        if (isPacket(packet, DemoModel.Packet.ID.COMMAND)) {
            const cmd = packet.data.command;
            const playerNum = packet.data.playerNum;

            // Only process commands within time window
            if (packet.fullGameTime > timeLimit) {
                return;
            }

            if (cmd.cmdName === "BUILD" && cmd.unitDefId) {
                if (!buildOrders.has(playerNum)) {
                    buildOrders.set(playerNum, []);
                }

                const unitName = typeof cmd.unitDefId === 'string' ? cmd.unitDefId : unitDefs[cmd.unitDefId] || `unit_${cmd.unitDefId}`;
                const unitDisplayName = unitNames[unitName] || unitName;
                
                const builderUnitId = cmd.unitId;
                const builderUnitName = builderUnitId && unitDefs.length > 0 ? unitDefs[builderUnitId] : undefined;

                buildOrders.get(playerNum)!.push({
                    time: packet.fullGameTime,
                    unitName,
                    unitDisplayName,
                    builderType: getBuilderType(builderUnitName, unitName),
                });
            }
        }

        if (isPacket(packet, DemoModel.Packet.ID.AICOMMAND)) {
            const cmd = packet.data.command;
            const playerNum = packet.data.playerNum;

            // Only process commands within time window
            if (packet.fullGameTime > timeLimit) {
                return;
            }

            if (cmd.cmdName === "BUILD" && cmd.unitDefId) {
                if (!buildOrders.has(playerNum)) {
                    buildOrders.set(playerNum, []);
                }

                const unitName = typeof cmd.unitDefId === 'string' ? cmd.unitDefId : unitDefs[cmd.unitDefId] || `unit_${cmd.unitDefId}`;
                const unitDisplayName = unitNames[unitName] || unitName;
                
                const builderUnitId = cmd.unitId;
                const builderUnitName = builderUnitId && unitDefs.length > 0 ? unitDefs[builderUnitId] : undefined;

                buildOrders.get(playerNum)!.push({
                    time: packet.fullGameTime,
                    unitName,
                    unitDisplayName,
                    builderType: getBuilderType(builderUnitName, unitName),
                });
            }
        }
    });

    try {
        const demo = await parser.parseDemo(demoPath);
        
        // Extract game date from filename
        const fileName = path.basename(demoPath);
        const dateMatch = fileName.match(/^(\d{4}-\d{2}-\d{2})/);
        const gameDate = dateMatch ? dateMatch[1] : new Date().toISOString().split('T')[0];

        // Create game data
        const gameData: GameData = {
            replayId,
            fileName,
            gameDate,
            duration: demo.info.meta.durationMs,
            mapName: demo.info.meta.map,
            winningAllyTeamIds: demo.info.meta.winningAllyTeamIds,
            players: demo.info.players.map(p => ({
                name: p.name,
                playerId: p.playerId,
                teamId: p.teamId,
                allyTeamId: p.allyTeamId,
                skill: extractSkillFromString(p.skill),
                rank: p.rank,
                faction: p.faction,
                startPos: p.startPos ? { x: p.startPos.x, z: p.startPos.z } : undefined,
            })),
        };

        // Extract positions and builds
        const positions: PlayerPosition[] = [];
        const builds: PlayerBuildOrder[] = [];

        for (const player of demo.info.players) {
            if (!player.startPos) continue;

            const skill = extractSkillFromString(player.skill);
            const wonGame = demo.info.meta.winningAllyTeamIds.includes(player.allyTeamId);

            // Position data
            positions.push({
                replayId,
                fileName,
                gameDate,
                playerName: player.name,
                playerId: player.playerId,
                teamId: player.teamId,
                allyTeamId: player.allyTeamId,
                skill,
                rank: player.rank,
                faction: player.faction,
                startPos: { x: player.startPos.x, z: player.startPos.z },
                wonGame,
            });

            // Build order data
            const playerBuilds = buildOrders.get(player.playerId) || [];
            if (playerBuilds.length > 0) {
                builds.push({
                    replayId,
                    fileName,
                    gameDate,
                    playerName: player.name,
                    playerId: player.playerId,
                    teamId: player.teamId,
                    allyTeamId: player.allyTeamId,
                    skill,
                    rank: player.rank,
                    position: { x: player.startPos.x, z: player.startPos.z },
                    wonGame,
                    buildOrder: playerBuilds,
                });
            }
        }

        return { positions, builds, gameData };
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error(`❌ Error parsing ${path.basename(demoPath)}: ${errorMessage}`);
        return null;
    }
}

async function main() {
    console.log("\n=== BAR Demo Parser ===\n");

    const barAnalysisRoot = path.join(__dirname, "..");
    const replaysDir = path.join(barAnalysisRoot, config.paths.replays);
    const parsedDir = path.join(barAnalysisRoot, config.paths.parsed);

    // Ensure directories exist
    if (!fs.existsSync(parsedDir)) {
        fs.mkdirSync(parsedDir, { recursive: true });
    }
    
    if (!fs.existsSync(replaysDir)) {
        console.log("⚠ Replays directory not found:", replaysDir);
        console.log("  Run 1-download-replays.py first to download replays");
        console.log("  Or copy .sdfz files to:", replaysDir);
        return;
    }

    // Get all .sdfz files
    const replayFiles = fs.readdirSync(replaysDir).filter(f => f.endsWith(".sdfz"));
    
    if (replayFiles.length === 0) {
        console.log("⚠ No replay files found in", replaysDir);
        console.log("  Run 1-download-replays.py first to download replays");
        return;
    }

    console.log(`📂 Found ${replayFiles.length} replay files`);
    console.log(`⏱️  Analyzing first ${config.analysis.time_window_seconds / 60} minutes of each game\n`);

    // Open output streams
    const positionsStream = fs.createWriteStream(path.join(parsedDir, "positions.jsonl"));
    const buildsStream = fs.createWriteStream(path.join(parsedDir, "builds.jsonl"));

    let successCount = 0;
    let errorCount = 0;
    const allGameData: GameData[] = [];

    // Parse each replay
    for (let i = 0; i < replayFiles.length; i++) {
        const fileName = replayFiles[i];
        const replayPath = path.join(replaysDir, fileName);
        const replayId = fileName.replace(".sdfz", "");

        process.stdout.write(`\r[${i + 1}/${replayFiles.length}] Parsing ${fileName}...`);

        const result = await parseSingleDemo(replayPath, replayId);

        if (result) {
            successCount++;
            
            // Write positions
            for (const position of result.positions) {
                positionsStream.write(JSON.stringify(position) + "\n");
            }

            // Write builds
            for (const build of result.builds) {
                buildsStream.write(JSON.stringify(build) + "\n");
            }

            // Save game data
            allGameData.push(result.gameData);

            // Save individual game file if configured
            if (config.analysis) {
                const gameFilePath = path.join(parsedDir, `game-${replayId}.json`);
                fs.writeFileSync(gameFilePath, JSON.stringify(result.gameData, null, 2));
            }
        } else {
            errorCount++;
        }
    }

    // Close streams
    positionsStream.end();
    buildsStream.end();

    // Save summary
    const summary = {
        totalReplays: replayFiles.length,
        successfullyParsed: successCount,
        errors: errorCount,
        totalPositions: allGameData.reduce((sum, g) => sum + g.players.length, 0),
        parsedAt: new Date().toISOString(),
    };

    fs.writeFileSync(
        path.join(parsedDir, "parse-summary.json"),
        JSON.stringify(summary, null, 2)
    );

    console.log("\n\n=== Parsing Complete ===");
    console.log(`✓ Successfully parsed: ${successCount}`);
    console.log(`✗ Errors: ${errorCount}`);
    console.log(`📊 Total player positions: ${summary.totalPositions}`);
    console.log(`\n✓ Data saved to: ${parsedDir}`);
    console.log(`  - positions.jsonl: Player positions`);
    console.log(`  - builds.jsonl: Build orders`);
    console.log(`  - game-*.json: Individual game files`);
    console.log(`  - parse-summary.json: Summary statistics`);
}

main().catch(error => {
    console.error("\n❌ Fatal error:", error);
    process.exit(1);
});

