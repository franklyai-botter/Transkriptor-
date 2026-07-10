# PLAN_TRANSCRIPTOR — NN-Style-Finalisierung

Erstellt: 2026-05-26 · Status: FREIGEGEBEN (mit Brand-Korrektur 2026-05-26)

## Brand-Korrektur (Update nach Frank-Feedback)
**Quelle der Wahrheit:** `C:\Users\frank\OneDrive\Dokumente\Neuralnautic\Marketing\Corporate design\Corporate Design\`
Drei offizielle Logo-Varianten existieren — alle in Chrome/Silber-Optik:
1. **Stern-Kompass** (4-zackig) = aktuelles `logo-star.png` → wird **Favicon-only**
2. **NN-Monogramm scharf-spitz** = aktuelles `logo-monogram.png` → wird **zentrales Brand-Element**
3. NN-Schreibschrift kalligrafisch → vorerst ungenutzt

### Änderungen gegenüber dem Ursprungsplan
- **Header (Z. 604–610):** `logo-star.png` 48 px → ersetzen durch `logo-monogram.png` 48 px (chrome NN als Brand-Anker)
- **`.btn-upload` Icon (Z. 625):** `logo-star.png` 28 px → bleibt **Stern** als sekundärer Brand-Touch ODER ersetzen durch Mini-NN — Empfehlung: **Stern behalten** (kleines Detail-Branding, Größenkontrast zum Header-NN)
- **Favicon (Z. 7):** Bleibt `logo-star.png` (Stern als Browser-Tab-Identität)
- **Cyan-Akzent `#3FD4E0` bleibt erhalten** als zusätzliche Tech-Note (Frank's Entscheidung) — Brand-Hauptcharakter ist aber chrome-silber, cyan nur für aktive States / Buttons / Glows



## Executive Summary
- **Status:** Header, Drop-Zone, Body-BG, Canvas-Layer und Tokens sind bereits sauber NN — ca. 50 % des Frontends ist on-brand, 50 % trägt noch alte Cyberpunk-Cyans (`rgba(0,255,255,…)`), Off-Brand Editor-Farben (Export-Buttons in Violett/Grün/Blau) und 16-px-Card-Radius statt NN-Standard 8 px.
- **Größter Bruch:** Die 5 Export-Buttons (HTML/MD/PDF/DOCX/JSON) nutzen eine One-Dark-Editor-Palette — komplett off-brand, sollten zu einheitlichen Mono-Cyan-Pills werden.
- **Backend-relevant:** `backend.py::export_html` (Z. 350–394) produziert einen `transcript.html`-Download mit `#001428` BG, `#00ffff` Cyan, `Segoe UI` Font — muss NN-Tokens + Italiana/Inter/Mono tragen.
- **Refactor zu `nn-theme.css`:** **noch nicht jetzt** — erst aufräumen, dann ggf. extrahieren. Wispr Clone ist getrenntes Repo.
- **Aufwand:** 22 Schritte, davon 18 × S + 4 × M. Eine fokussierte Session ohne Backend-Pipeline-Änderung.

---

## 1. Status-Aufnahme

### 1.1 Was bereits NN-konform ist
| Bereich | Beleg (`frontend/index.html`) |
|---|---|
| CSS-Variablen-Set komplett mit korrekten Werten | Z. 16–55 |
| Google-Fonts (Italiana, Inter, JetBrains Mono) | Z. 10 |
| Body-BG mit `bg-neural-network.png` + Radial-Vignette | Z. 68–86 |
| Animated Neural Canvas (Layer 2, opacity 0.35, mix-blend screen) | Z. 89–97, 672–770 |
| Header (sticky, 72 px, blur, `rgba(10,32,40,0.78)`) | Z. 109–122 |
| Logo-Star 48 px im Header mit drop-shadow | Z. 124–136 |
| Brand-Typo (Italiana H1 + Mono uppercase Sublabel) | Z. 138–153 |
| Drop-Zone mit `logo-monogram.png` 72 px | Z. 165–215, 620–627 |
| Primary-Button mit Logo-Star Icon, cyan, uppercase | Z. 217–248 |
| Mini-Buttons (Reset/Eject) | Z. 540–557 |
| Favicon = `logo-star.png` | Z. 7 |
| Drop-Zone Headline & Results-H2 in Italiana | Z. 199–206, 362–368 |

### 1.2 Inkonsistenzen

**A) Hardcoded Cyans / Blues statt Tokens** (alte `rgba(0,255,255,…)` / `rgba(0,204,204,…)`):
- `.progress-panel`, `.progress-bar-bg`, `.progress-bar-fill`, `.step.*`, `.transcript-container`, Scrollbar, `.segment:hover`, `.segment.speech`, `.seg-slide img`, `.stat-card`, `.stat-value`, `.lightbox img`, `.btn-mini*`, `.btn-cancel`, `.banner`, Canvas-JS, Health-Status-Dot

**B) Card-Pattern verletzt:** `.progress-panel` & `.transcript-container` haben **radius 16 px**, `.stat-card` 10 px → NN-Spec ist 8 px. `backdrop-filter: blur(8px)` statt blur(20px).

**C) Export-Buttons off-brand:** One-Dark-Editor-Palette (React-Blau, Violett, Grün, Türkis) statt NN-Cyan-Pills.

**D) Inline-Styles in HTML statt Klassen:** Header-Rechts, Drop-Zone-Disclaimer, Server-Status, Stats-Innerhtml.

**E) Server-Status ist nur `<span>● …</span>`** — NN-Konvention wäre Mono-Status-Pill mit farbigem Dot.

**F) Emoji-Icons** (✓ ❌ ⏹ ⬇ ⚠ ✕ ⏻ ↻) brechen den High-Tech-Tide-Look.

**G) Step-Pills mit border-radius 20 px** — NN-Komponenten sind 8 px (Pills nur für Tags).

**H) Stat-Values in Inter statt Italiana oder Mono** — `font-variant-numeric: tabular-nums` fehlt überall außer Timestamps.

**I) `export_html()` im Backend:** `#001428` BG, `#00ffff`, `Segoe UI`, `#ffd700` — komplett alt.

**J) Ungenutzte Tokens:** `--ink-current`, `--ink-shoal`, `--glow-mist`, `--signal-ok` werden nirgends verwendet — Health-Status-Dot nutzt `#3dd68c` statt `--signal-ok`.

**K) Kein `:focus-visible`** — A11y-Lücke.

### 1.3 Asset-Inventar
| Asset | Vorhanden | NN-Verwendung |
|---|---|---|
| `logo-star.png` | Ja | Header 48 px ✓, btn-upload 28 px ✓, Favicon ✓ |
| `logo-monogram.png` | Ja | Drop-Zone 72 px ✓ |
| `bg-neural-network.png` | Ja (1.2 MB) | body::before opacity 0.18 ✓ |
| `nn-theme.css` extern | fehlt | siehe §2 |

### 1.4 Backend-relevant
- `backend.py:350–394` (`export_html`) — Stylesheet muss NN-konform werden
- `backend.py:397–422` (`export_pdf`) — optional Branding (Logo-Star + Header-Style)
- `backend.py:425–449` (`export_docx`) — optional Branding
- Endpoints `/upload`, `/status`, `/download`, `/slides`, `/cancel`, `/shutdown`, `/health` — **nicht anfassen**

---

## 2. Refactor-Empfehlung: `nn-theme.css` auslagern?

**Empfehlung: JA, aber nicht jetzt.**

| Pro | Contra |
|---|---|
| Single Source of Truth | Transkriptor ist Single-File-App — Auslagern = zusätzlicher HTTP-Request |
| Inline-CSS-Block ist 585 Zeilen | Wispr Clone hat eigenes Repo / eigene `dashboard/index.html` |
| Bessere Editor-Unterstützung | Refactor-Risiko erhöht bei gleichzeitigem Token-Cleanup |

**Reihenfolge:** Phase A jetzt — Inline-CSS bereinigen. Phase B später — extrahieren wenn Wispr-Dashboard auch HTML-basiert ist.

---

## 3. Konkrete Arbeitsschritte

### S1 — Hardcoded Cyans/Blues durch Tokens ersetzen [S]
- **WO:** `index.html:255–588, 723, 741, 752`
- **WIE:** Find&Replace tabellenweise:
  ```
  rgba(0,255,255,0.15)  → rgba(63,212,224,0.15)
  rgba(0,255,255,0.08)  → rgba(63,212,224,0.08)
  rgba(0,255,255,0.04)  → rgba(63,212,224,0.04)
  rgba(0,255,255,0.10)  → rgba(63,212,224,0.10)
  rgba(0,255,255,0.12)  → rgba(63,212,224,0.12)
  rgba(0,255,255,0.20)  → rgba(63,212,224,0.20)
  rgba(0,255,255,0.30)  → rgba(63,212,224,0.30)
  rgba(0,255,255,0.40)  → rgba(63,212,224,0.40)
  rgba(0,204,204,…)     → rgba(45,138,154,…)
  rgba(0,200,200,…)     → rgba(45,138,154,…)
  rgba(0,220,220,…)     → rgba(63,212,224,…)
  ```

### S2 — Alt-Navy auf `--ink-deep`/`--navy-card` [S]
- **WO:** `index.html:428, 486`
- **WIE:** `rgba(0,20,40,0.6)` → `var(--navy-card)` oder `rgba(10,32,40,0.6)`

### S3 — Card-Radius vereinheitlichen auf 8 px [S]
- **WO:** `.progress-panel` (257), `.transcript-container` (404), `.stat-card` (490), `.lightbox img` (525), `.banner` (584), `.segment` (418)

### S4 — Card-Backdrop-Blur auf 20 px [S]
- **WO:** `index.html:258, 405`

### S5 — Card-Borders auf `--border-1` [S]
- **WO:** `.progress-panel` (256), `.transcript-container` (402), `.stat-card` (488)

### S6 — Export-Buttons: One-Dark-Palette → NN-Cyan-Pills [S]
- **WO:** `index.html:376–396`
- **WIE:**
  ```css
  .btn-export {
    padding: 0.5rem 1.1rem; border-radius: 8px;
    font-family: var(--font-mono); font-size: 0.75rem;
    letter-spacing: 0.08em; text-transform: uppercase;
    border: 1px solid rgba(63,212,224,0.35);
    background: rgba(63,212,224,0.08);
    color: var(--glow-cyan);
  }
  .btn-export:hover { background: rgba(63,212,224,0.18);
    box-shadow: 0 0 16px rgba(63,212,224,0.25); color: var(--glow-aqua); }
  ```
  Per-Format-Color-Regeln (`.btn-html`, `.btn-md`, `.btn-pdf`, `.btn-docx`, `.btn-json`) komplett streichen.

### S7 — `.segment.silence` entgiften [S]
- **WO:** `index.html:430–433, 451–455`
- **WIE:** Border-Left `var(--signal-alert)`, BG `rgba(240,138,122,0.06)`, Text in Mono.

### S8 — `.segment.speech` Border auf Token-Cyan [S]
- **WO:** `index.html:425–428`
- **WIE:** Border-Left `var(--glow-faint)`, BG `rgba(14,43,54,0.5)`.

### S9 — Step-Indicators NN-konform [S]
- **WO:** `index.html:298–343`
- **WIE:** Mono uppercase, radius 6 px, Tokens. Done-State: `--signal-ok` statt Gold.

### S10 — Progress-Bar Glow auf Token-Cyan [S]
- **WO:** `index.html:289–296`. `.progress-pct` von Gold → Cyan (Z. 278).

### S11 — Stat-Cards: Italiana + tabular-nums + NN-Tokens [S]
- **WO:** `index.html:483–506, 991–1008`
- **WIE:** `.stat-value` in Italiana 2 rem cyan + text-shadow cyan. `.stat-label` Mono. JS-Inline-Colors auf Tokens.

### S12 — Mini-Buttons auf NN-Tokens [S]
- **WO:** `index.html:540–557`

### S13 — Banner / Cancel auf `--signal-alert` [S]
- **WO:** `index.html:559–588`

### S14 — Server-Status als richtige Pill [M]
- **WO:** `index.html:611–612, 967–976`
- **WIE:** HTML `.status-pill` mit `.status-dot` + `.status-label`. CSS: Mono uppercase, ok/error-Klassen. JS-Switch klassenbasiert.

### S15 — Emojis durch Mono-Glyphen [S]
- **WO:** `index.html:613–614, 647, 889, 952, 1019, 981`
- **WIE:** Variante A (schnell): kritische Emojis tauschen — `✓` → `▸▸`, `❌` → `× FEHLER`, `⚠` → `~ STILLE`, `⬇` → `↓`. `⏻ ↻ ✕` (Tech-Symbols) behalten.

### S16 — Drop-Zone Inline-Styles → Klassen [S]
- **WO:** `index.html:619–627`
- **WIE:** `.drop-icon` und `.drop-meta` als CSS-Klassen.

### S17 — `:focus-visible` für A11y [S]
- **WO:** Ende `<style>`
- **WIE:** Globale `outline: 2px solid var(--glow-cyan)` Regel.

### S18 — `export_html()` NN-konform [M]
- **WO:** `backend.py:350–394`
- **WIE:** Tokens-Block + Google-Fonts-CDN + Italiana-H1 + NN-Cards. Klassen `speech`/`silence` parallel zum Frontend.

### S19 — PDF / DOCX Branding (optional) [M]
- **WO:** `backend.py:397–449`
- **WIE:** Reportlab — Logo-Star oben (1.2 cm) + `NeuralNautic Transkript` in 20 pt + Meta in 8 pt Mono. DOCX dito.

### S20 — Ungenutzte Tokens nutzen [S, optional]
- `--ink-shoal` für Hover-States, `--glow-mist` für Hairline-Akzente, `--ink-current` für leichten Layer-BG.

### S21 — Alt-Aliase entfernen [S, optional]
- **WO:** `index.html:36–45`
- **WIE:** Find&Replace: `var(--cyan)` → `var(--glow-cyan)` usw. Aliase löschen.

### S22 — Smoke-Test Export [S]
- Kurze Test-MP4 → alle 5 Exporte öffnen & prüfen.

---

## 4. Risiken / Offene Fragen

### Risiken
1. **Find&Replace pro Alpha:** `rgba(0,255,255,…)` mit unterschiedlichen Alphas — pro Wert einzeln replacen, nicht global.
2. **Canvas-Performance** bei schwacher Hardware während Whisper-Run. Optional `requestAnimationFrame` pausieren beim Polling. **Nicht Teil dieser Phase.**
3. **Google-Fonts im Export** lädt nur online — akzeptabel für HTML-Export, PDF/DOCX brauchen kein Netz.
4. **Per-Format-Klassen `.btn-html` etc. in JS:** Klassen behalten, nur CSS-Regeln streichen.

### Offene Fragen für Frank
1. **Emojis komplett ersetzen (Variante A) oder Inline-SVG-Set (Variante B)?** Empfehlung: A.
2. **`nn-theme.css` auslagern jetzt oder später?** Empfehlung: später.
3. **Stat-Card-Zahlen Italiana (Hero) oder Mono (Tech)?**
4. **Alt-Token-Aliase entfernen oder behalten?**
5. **PDF/DOCX-Branding diese Phase oder eigene?**

---

## 5. Test-Strategie

### Smoke-Test (Browser auf `http://127.0.0.1:5678`)
1. **Header:** Logo-Star scharf, Italiana-Brand, Mono-Subtitle, Status-Pill grün mit Dot.
2. **Background:** `bg-neural-network.png` opacity 0.18, Canvas animiert, Radial-Vignette.
3. **Drop-Zone:** Monogram 72 px, Italiana-Headline, Mono-Disclaimer, Cyan-Button mit Logo-Star.
4. **Drag-Over:** Border cyan, glow.
5. **Upload + Progress:** Step-Pills Mono uppercase 6 px, aktive cyan + pulse, done = `--signal-ok` mint, Bar cyan-glow, Pct cyan.
6. **Cancel:** Banner alert-style (nicht mehr `#ff6b6b`).
7. **Results:** Stats 8 px-radius, Export-Buttons alle cyan Mono-Pills, Container 8 px-radius, Speech-Segments `--glow-faint`-Border, Silence-Segments `--signal-alert`-Border.
8. **Lightbox:** Modal mit cyan-glow.
9. **Downloads:** HTML zeigt NN-Brand (nicht Cyberpunk). PDF/DOCX mit Header (falls S19). MD/JSON neutral.
10. **Eject:** Confirm → Stop → red Pill pulse → NN-Alert-Banner.
11. **Tab-Nav:** `:focus-visible` zeigt cyan-Outline.

### Regression (darf NICHT brechen)
- Whisper-Pipeline läuft
- Polling 1.5 s
- Cancel/Shutdown-Endpoints
- XHR-Upload mit Progress
- Drag&Drop, Lightbox

---

## Datei-Referenzen

- `C:\Users\frank\First Try\transcriptor\start.bat`
- `C:\Users\frank\First Try\transcriptor\backend.py` (Z. 350–449 UI-relevant)
- `C:\Users\frank\First Try\transcriptor\frontend\index.html`
- `C:\Users\frank\First Try\transcriptor\frontend\logo-star.png`
- `C:\Users\frank\First Try\transcriptor\frontend\logo-monogram.png`
- `C:\Users\frank\First Try\transcriptor\frontend\bg-neural-network.png`
