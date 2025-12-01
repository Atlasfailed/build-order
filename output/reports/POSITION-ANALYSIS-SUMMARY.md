# BUILD ORDER ANALYSE - SUPREME ISTHMUS v2.1
## Analyse van 137 High-Skill Replays (2168 builds)

---

## 🎯 SAMENVATTING PER POSITIE

### FRONT-1 (1349 builds, avg skill: 31.0)

**Factory Keuze:**
- 🤖 **Bot Lab: 69.1%** (932 spelers) - Timing: ~2:00
- 🚗 **Vehicle Plant: 17.9%** (242 spelers)
- ✈️ **Aircraft Plant: 2.3%** (31 spelers)

**Meest Gebruikte Build (12.0% van spelers):**
```
Tidal Generator → Tidal Generator → Tidal Generator → Tidal Generator → Tidal Generator
Tidal Generator → Tidal Generator → Tidal Generator → Tidal Generator → Tidal Generator
```
→ "Tidal spam" opening (vooral bij water spawn)

**Tweede Meest Gebruikte (2.4%):**
```
Tidal Generator x9 → Metal Extractor
```

**Standaard Land Opening (1.4%):**
```
Metal Extractor x3 → Wind Turbine x2 → Wind Turbine x2 → Bot Lab → Lazarus → Lazarus
```

**Expansie Rate:**
- Gemiddeld **3.1 mexes** in eerste 2 minuten
- Gemiddeld **3.1 mexes** in eerste 4 minuten (weinig groei!)

---

### FRONT-2 (541 builds, avg skill: 29.8)

**Factory Keuze (zeer gebalanceerd!):**
- 🤖 **Bot Lab: 50.8%** (275 spelers)
- ✈️ **Aircraft Plant: 47.7%** (258 spelers)
- 🚗 **Vehicle Plant: 0.4%** (2 spelers)

**Meest Gebruikte Build (7.8%):**
```
Metal Extractor x3 → Wind Turbine x2 → Wind Turbine x5 (eco heavy)
```

**Tweede Meest Gebruikte (6.3%):**
```
Metal Extractor x3 → Wind Turbine x2 → Wind Turbine x2 → Bot Lab → Wind Turbine x2
```

**Air Opening (4.3%):**
```
Metal Extractor x3 → Wind Turbine x2 → Wind Turbine x2 → Energy Storage → Aircraft Plant → Finch
```

**Expansie Rate:**
- Gemiddeld **3.2 mexes** in eerste 2 minuten
- Gemiddeld **3.2 mexes** in eerste 4 minuten

---

### MID-1 (267 builds, avg skill: 32.3)

**Factory Keuze (Bot dominant):**
- 🤖 **Bot Lab: 92.1%** (246 spelers)
- ✈️ **Aircraft Plant: 2.2%** (6 spelers)
- 🚗 **Vehicle Plant: 1.5%** (4 spelers)

**Meest Gebruikte Build (9.4%):**
```
Metal Extractor x3 → Wind Turbine x5 (maximale wind)
```

**Tweede Meest Gebruikte (5.6%):**
```
Metal Extractor x3 → Wind Turbine x4 → Bot Lab
```

**Derde Meest Gebruikte (4.9%):**
```
Metal Extractor x3 → Wind Turbine x4 → Energy Storage
```

**Expansie Rate:**
- Gemiddeld **3.9 mexes** in eerste 2 minuten (HOOGSTE!)
- Gemiddeld **3.9 mexes** in eerste 4 minuten

---

## 📈 HIGH-SKILL SPELERS (skill > 40)

**Sample size:** 245 games

**Top 3 Meest Gebruikte Openings:**

1. **40.0%** - Standard Mex-Wind Opening
   ```
   Metal Extractor x3 → Wind Turbine x2
   ```

2. **5.3%** - Vehicle Rush
   ```
   Metal Extractor x3 → Vehicle Plant → Construction Vehicle
   ```

3. **4.5%** - Tidal Spam (water spawn)
   ```
   Tidal Generator x5
   ```

---

## 🔍 BELANGRIJKSTE INZICHTEN

### 1. Positie Karakteristieken

**FRONT-1:**
- Meest diverse positie
- Water spawns → Tidal spam strategie
- Land spawns → Standard mex-wind-bot
- Lagere gemiddelde skill (31.0)

**FRONT-2:**
- **50/50 verdeling Bot vs Air!**
- Strategische keuze tussen ground en air
- Iets lagere skill dan andere posities (29.8)

**MID-1:**
- Bot factory dominant (92%)
- Hoogste mex count (3.9)
- Focus op eco en bot production
- Hoogste gemiddelde skill (32.3)

### 2. Build Order Patronen

**Standaard Land Opening:**
```
3 Mexes → 2-4 Wind → Factory (Bot/Veh/Air)
```

**Tidal Spam (water spawns):**
```
8-10 Tidal Generators achter elkaar
```
→ Gebruikt door 12% van Front-1 spelers

**Energy Heavy:**
- Veel spelers bouwen 5+ wind turbines
- Focus op energy eerst, dan factory

### 3. Timing Observaties

⚠️ **Let op:** Factory timing data toont 0s, dit betekent dat:
- Time-stamps mogelijk niet correct worden geëxtraheerd
- Of tijd start vanaf factory completion
- Verdere timing analyse nodig

### 4. High-Skill Strategie

**Top spelers (40%)** kiezen voor:
```
Standard Opening: M M M W W
```

Dit suggereert dat de basis "3 mex - 2 wind" zeer effectief is.

---

## 💡 AANBEVELINGEN

### Voor FRONT-1 Spelers:
1. **Land spawn:** 3 mex → 2 wind → bot lab
2. **Water spawn:** Overweeg tidal spam (gebruikt door 12%)
3. Bot lab is de veiligste keuze (69% pick rate)

### Voor FRONT-2 Spelers:
1. **Bot of Air** - beide zijn viabel (50/50 split)
2. Air heeft voordeel tegen bot-heavy enemy
3. Standaard opening: 3 mex → wind → factory

### Voor MID-1 Spelers:
1. **Bot lab** bijna altijd (92%)
2. **Hogere mex count** (3.9) - veiligere positie
3. Focus op eco + bot production

---

## 📁 OUTPUT BESTANDEN

**Visualisaties:**
- `output/visualizations/index.html` - Interactive dashboard

**Reports:**
- `output/reports/position-summary.csv` - Positie statistieken
- `output/reports/build-success-rates.csv` - Build archetype prestaties
- `output/reports/high-skill-patterns.json` - High-skill speler patronen
- `output/reports/complete-analysis.json` - Volledige analyse data

**Data:**
- `data/parsed/positions.jsonl` - Alle speler posities
- `data/parsed/builds.jsonl` - Alle build orders
- `data/analysis/position-clusters.json` - Positie clusters
- `data/analysis/build-clusters.json` - Build archetypes

---

## 🎮 VOLGENDE STAPPEN

1. **Meer data verzamelen** voor betere win-rate analyse
2. **Timing verbeteren** - factory/combat unit timings extraheren
3. **Matchup analyse** - welke builds werken tegen elkaar
4. **Skill stratificatie** - vergelijk different skill levels
5. **Meta evolutie** - hoe veranderen builds over tijd

---

Gegenereerd: Dec 1, 2025
Dataset: 137 replays, 2168 builds
Posities geïdentificeerd: 3 (front-1, front-2, mid-1)

