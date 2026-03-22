import { createContext, useContext, useEffect, useRef, useState } from 'react'
import StockChart from './StockChart'
import CryptoChart from './CryptoChart'

// ── Types ──────────────────────────────────────────────────────────────────

type CharState = 'idle' | 'collecting' | 'eda' | 'feature' | 'analyzing' |
  'training' | 'optimizing' | 'backtesting' | 'risk' | 'writing' | 'reviewing' | 'celebrating' | 'error' | 'delivering'

interface Character {
  id: string; emoji: string; label: string; role: string
  state: CharState; progress: number; statusText: string
  x: number; y: number
  team: 'collection' | 'analysis' | 'ml' | 'report'
}
interface Particle { id:number; x:number; y:number; vx:number; vy:number; life:number; maxLife:number; symbol:string; color:string }
interface Delivery  { id:number; fromRoom:number; toRoom:number; progress:number; label:string; totalDist:number; isReturn:boolean }

// ── Theme palettes ─────────────────────────────────────────────────────────

const DARK = {
  dark:      true  as boolean,
  bg:        '#060a10', floor:     '#090e17', floorLine: '#0f1622',
  panel:     '#0d1117', border:    '#1c2333', borderBrt: '#2d3f5e',
  green:     '#00c076', greenDim:  '#00874f', red:       '#ff3b69',
  gold:      '#f0b429', blue:      '#388bfd', cyan:      '#39d0d8', purple:    '#a371f7',
  txt:       '#e6edf3', txtSec:    '#8b949e', txtMut:    '#484f58',
  deskFill:  '#1a2235', deskStroke:'#2d3f5e', monitorBg: '#0d1117',
  corridorBg:'#07090f', corridorLn:'#0f1218', shadow:    'rgba(0,0,0,0.35)',
  charHead:  '#d4a472', charEye:   '#111111', charStand: '#1e2d4a',
  teamBg: { collection:'#071510', analysis:'#071318', ml:'#0e0b18', report:'#141008' },
}

const LIGHT = {
  dark:      false as boolean,
  bg:        '#f0f4f8', floor:     '#e8eef5', floorLine: '#d4dde8',
  panel:     '#ffffff', border:    '#d0d9e6', borderBrt: '#aabbd0',
  green:     '#00874f', greenDim:  '#005c35', red:       '#cc2244',
  gold:      '#b08a00', blue:      '#1a6fd4', cyan:      '#1799a8', purple:    '#7c4dcc',
  txt:       '#1a2332', txtSec:    '#4a5568', txtMut:    '#8a98aa',
  deskFill:  '#dce6f0', deskStroke:'#aabbd0', monitorBg: '#e0e8f0',
  corridorBg:'#e4ecf4', corridorLn:'#c8d4e0', shadow:    'rgba(0,0,0,0.12)',
  charHead:  '#c9945a', charEye:   '#222222', charStand: '#8faabf',
  teamBg: { collection:'#e8f5ef', analysis:'#e8f2f5', ml:'#f0ecf8', report:'#f5f0e0' },
}

type Colors = typeof DARK

// ── Theme context ──────────────────────────────────────────────────────────

interface ThemeCtx { dark: boolean; toggle: () => void; c: Colors }
const ThemeContext = createContext<ThemeCtx>({ dark: true, toggle: () => {}, c: DARK })
const useTheme = () => useContext(ThemeContext)

// ── Team / state metadata (color-aware) ────────────────────────────────────

function getTeamMeta(c: Colors) {
  return {
    collection: { label:'COLLECTION',   short:'COL', color:c.green,  bg:c.teamBg.collection },
    analysis:   { label:'DATA SCIENCE', short:'DSC', color:c.cyan,   bg:c.teamBg.analysis   },
    ml:         { label:'ML ENG.',      short:'ML',  color:c.purple,  bg:c.teamBg.ml         },
    report:     { label:'REPORT',       short:'RPT', color:c.gold,   bg:c.teamBg.report     },
  }
}

const STATE_INFO: Record<string, { symbol: string; colorKey: keyof Colors }> = {
  collecting:  { symbol:'▲', colorKey:'green'  },
  eda:         { symbol:'◈', colorKey:'cyan'   },
  feature:     { symbol:'⚙', colorKey:'gold'   },
  analyzing:   { symbol:'≋', colorKey:'blue'   },
  training:    { symbol:'◉', colorKey:'purple' },
  optimizing:  { symbol:'⚡', colorKey:'gold'   },
  backtesting: { symbol:'◀', colorKey:'purple' },
  risk:        { symbol:'▲', colorKey:'red'    },
  writing:     { symbol:'✎', colorKey:'gold'   },
  reviewing:   { symbol:'✓', colorKey:'green'  },
  celebrating: { symbol:'★', colorKey:'gold'   },
  error:       { symbol:'✕', colorKey:'red'    },
  idle:        { symbol:'',  colorKey:'txtMut' },
  delivering:  { symbol:'📦', colorKey:'gold'  },
}

// ── Sprite cache ───────────────────────────────────────────────────────────
const spriteCache = new Map<string, HTMLImageElement | null>()
function getSprite(role: string): HTMLImageElement | null {
  if (spriteCache.has(role)) return spriteCache.get(role) ?? null
  spriteCache.set(role, null)
  const img = new Image()
  img.onload = () => spriteCache.set(role, img)
  img.src = `/assets/sprites/${role}.png`
  return null
}

// ── Characters ─────────────────────────────────────────────────────────────
const INITIAL_CHARS: Character[] = [
  { id:'c1', emoji:'🧑‍💻', label:'주가수집', role:'collector',        state:'collecting',  progress:0.65, statusText:'반도체',     x:0,y:0, team:'collection' },
  { id:'c2', emoji:'🧑‍💻', label:'주가수집', role:'collector',        state:'collecting',  progress:0.40, statusText:'자동차',     x:1,y:0, team:'collection' },
  { id:'c3', emoji:'🧑‍💻', label:'주가수집', role:'collector',        state:'idle',        progress:1.0,  statusText:'완료',       x:2,y:0, team:'collection' },
  { id:'c4', emoji:'🧑‍💻', label:'뉴스수집', role:'collector',        state:'collecting',  progress:0.30, statusText:'뉴스',       x:0,y:1, team:'collection' },
  { id:'c5', emoji:'🧑‍💻', label:'공시수집', role:'collector',        state:'collecting',  progress:0.55, statusText:'DART',      x:1,y:1, team:'collection' },
  { id:'c6', emoji:'📦', label:'서무',    role:'delivery',         state:'idle',        progress:1.0,  statusText:'대기',       x:2,y:1, team:'collection' },
  { id:'a1', emoji:'🧑‍🔬', label:'EDA',     role:'eda_analyst',      state:'eda',         progress:0.80, statusText:'ADF p=0.02', x:0,y:0, team:'analysis' },
  { id:'a2', emoji:'🧑‍🔧', label:'피처',    role:'feature_engineer', state:'feature',     progress:0.60, statusText:'RSI/MACD',  x:1,y:0, team:'analysis' },
  { id:'a3', emoji:'🧑‍💻', label:'통계',    role:'stat_analyst',     state:'analyzing',   progress:0.45, statusText:'회귀분석',   x:2,y:0, team:'analysis' },
  { id:'a4', emoji:'🧑‍💻', label:'감성NLP', role:'sentiment',        state:'analyzing',   progress:0.70, statusText:'TF-IDF',    x:0,y:1, team:'analysis' },
  { id:'a5', emoji:'🧑‍💻', label:'섹터',   role:'sector_cluster',   state:'idle',        progress:1.0,  statusText:'대기',       x:1,y:1, team:'analysis' },
  { id:'a6', emoji:'📦', label:'서무',    role:'delivery',         state:'idle',        progress:1.0,  statusText:'대기',       x:2,y:1, team:'analysis' },
  { id:'m1', emoji:'🤖',  label:'트레이너', role:'ml_engineer',      state:'training',    progress:0.70, statusText:'LSTM 35/50', x:0,y:0, team:'ml' },
  { id:'m2', emoji:'🧪',  label:'백테스터', role:'backtester',       state:'backtesting', progress:0.50, statusText:'Sharpe 1.42',x:1,y:0, team:'ml' },
  { id:'m3', emoji:'⚠️',  label:'리스크',   role:'risk_assessor',    state:'risk',        progress:0.30, statusText:'VaR',        x:2,y:0, team:'ml' },
  { id:'m4', emoji:'🤖',  label:'최적화',   role:'ml_engineer',      state:'optimizing',  progress:0.40, statusText:'Trial 12/30',x:0,y:1, team:'ml' },
  { id:'m5', emoji:'📦',  label:'서무',    role:'delivery',         state:'idle',        progress:1.0,  statusText:'대기',       x:2,y:1, team:'ml' },
  { id:'r1', emoji:'🧑‍💼', label:'종합리포터',role:'report_writer',   state:'writing',     progress:0.75, statusText:'작성중',     x:0,y:0, team:'report' },
  { id:'r2', emoji:'🧑‍💼', label:'투자메모', role:'invest_memo',      state:'reviewing',   progress:1.0,  statusText:'✓ Done',    x:1,y:0, team:'report' },
  { id:'r3', emoji:'🧑‍💼', label:'리스크노트',role:'risk_note',       state:'idle',        progress:0.0,  statusText:'대기',       x:2,y:0, team:'report' },
  { id:'r4', emoji:'🧑‍💼', label:'편집장',   role:'editor',          state:'reviewing',   progress:0.60, statusText:'최종검토',   x:0,y:1, team:'report' },
  { id:'r5', emoji:'📦', label:'서무',    role:'delivery',         state:'idle',        progress:1.0,  statusText:'대기',       x:2,y:1, team:'report' },
]

// ── Canvas draw helpers ────────────────────────────────────────────────────

// Team-specific floor texture
function drawRoomFloor(ctx: CanvasRenderingContext2D, x:number, y:number, w:number, h:number, teamKey: string, c:Colors) {
  // Base carpet/floor color per team
  const floorColors: Record<string, string> = {
    collection: c.dark ? '#071a10' : '#e8f5ef',
    analysis:   c.dark ? '#071318' : '#e8f2f7',
    ml:         c.dark ? '#0e0b1a' : '#f0ecf8',
    report:     c.dark ? '#141008' : '#f5f0e0',
  }
  const lineColors: Record<string, string> = {
    collection: c.dark ? '#0c2218' : '#d4eadf',
    analysis:   c.dark ? '#0c1a24' : '#d4e5ee',
    ml:         c.dark ? '#160d28' : '#e4daf5',
    report:     c.dark ? '#1e1608' : '#ece5cc',
  }
  ctx.fillStyle = floorColors[teamKey] ?? c.floor
  ctx.fillRect(x, y, w, h)

  // Tile grid
  ctx.strokeStyle = lineColors[teamKey] ?? c.floorLine
  ctx.lineWidth = 0.5
  const tile = 16
  for (let gx = x; gx <= x+w; gx += tile) { ctx.beginPath(); ctx.moveTo(gx, y); ctx.lineTo(gx, y+h); ctx.stroke() }
  for (let gy = y; gy <= y+h; gy += tile) { ctx.beginPath(); ctx.moveTo(x, gy); ctx.lineTo(x+w, gy); ctx.stroke() }

  // Diagonal carpet texture (subtle)
  ctx.strokeStyle = (lineColors[teamKey] ?? c.floorLine) + '55'
  ctx.lineWidth = 0.3
  for (let d = -h; d < w+h; d += 20) {
    ctx.beginPath(); ctx.moveTo(x+d, y); ctx.lineTo(x+d+h, y+h); ctx.stroke()
  }
}

// Ceiling light glow
function drawCeilingLight(ctx: CanvasRenderingContext2D, lx:number, ly:number, radius:number, color:string) {
  const grad = ctx.createRadialGradient(lx, ly, 0, lx, ly, radius)
  grad.addColorStop(0, color+'28')
  grad.addColorStop(0.4, color+'12')
  grad.addColorStop(1, 'transparent')
  ctx.fillStyle = grad
  ctx.beginPath(); ctx.arc(lx, ly, radius, 0, Math.PI*2); ctx.fill()
  // Fixture dot
  ctx.fillStyle = color+'99'
  ctx.beginPath(); ctx.arc(lx, ly, 3, 0, Math.PI*2); ctx.fill()
  ctx.fillStyle = color+'dd'
  ctx.beginPath(); ctx.arc(lx, ly, 1.5, 0, Math.PI*2); ctx.fill()
}

// Thick wall with door opening
function drawRoomWalls(ctx: CanvasRenderingContext2D, rx:number, ry:number, rw:number, rh:number, accentColor:string, c:Colors, doorSide:'right'|'bottom' = 'right') {
  const W = 5  // wall thickness
  ctx.fillStyle = c.dark ? '#0a1020' : '#c8d4e0'

  // Top wall
  ctx.fillRect(rx, ry, rw, W)
  // Left wall
  ctx.fillRect(rx, ry, W, rh)
  // Bottom wall (with optional door gap)
  if (doorSide === 'bottom') {
    const doorW = 22, doorX = rx + rw/2 - doorW/2
    ctx.fillRect(rx, ry+rh-W, doorX-rx, W)
    ctx.fillRect(doorX+doorW, ry+rh-W, rw-(doorX+doorW-rx), W)
  } else {
    ctx.fillRect(rx, ry+rh-W, rw, W)
  }
  // Right wall (with optional door gap)
  if (doorSide === 'right') {
    const doorW = 22, doorY = ry + rh*0.6
    ctx.fillRect(rx+rw-W, ry, W, doorY-ry)
    ctx.fillRect(rx+rw-W, doorY+doorW, W, rh-(doorY+doorW-ry))
    // Door arc
    ctx.strokeStyle = accentColor+'55'; ctx.lineWidth = 1
    ctx.beginPath(); ctx.arc(rx+rw-W, doorY+doorW, doorW, -Math.PI/2, 0); ctx.stroke()

    // Door frame — colored lines on both sides of the gap
    ctx.strokeStyle = accentColor+'88'; ctx.lineWidth = 2
    ctx.beginPath(); ctx.moveTo(rx+rw-W-1, doorY); ctx.lineTo(rx+rw+2, doorY); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(rx+rw-W-1, doorY+doorW); ctx.lineTo(rx+rw+2, doorY+doorW); ctx.stroke()

    // Door threshold — small horizontal line at bottom of door gap
    ctx.strokeStyle = c.gold+'44'; ctx.lineWidth = 1.5
    ctx.beginPath(); ctx.moveTo(rx+rw-W, doorY+doorW-1); ctx.lineTo(rx+rw+4, doorY+doorW-1); ctx.stroke()

    // Above door: small "DOOR" label in tiny text
    ctx.fillStyle = accentColor+'22'
    ctx.fillRect(rx+rw-W-15, doorY-11, 13, 8)
    ctx.strokeStyle = accentColor+'44'; ctx.lineWidth = 0.5
    ctx.strokeRect(rx+rw-W-15, doorY-11, 13, 8)
    ctx.font = '5px IBM Plex Mono,monospace'; ctx.fillStyle = accentColor+'bb'; ctx.textAlign = 'center'
    ctx.fillText('DOOR', rx+rw-W-8, doorY-5)
  } else {
    ctx.fillRect(rx+rw-W, ry, W, rh)
  }

  // Wall accent top strip
  ctx.fillStyle = accentColor+'44'
  ctx.fillRect(rx, ry, rw, 3)

  // Baseboard
  ctx.fillStyle = accentColor+'22'
  ctx.fillRect(rx+W, ry+rh-W-2, rw-W*2, 2)
  ctx.fillRect(rx+W, ry+W, 2, rh-W*2)

  // Windows on top wall — 2 per room, evenly spaced
  const winW = 18, winH = 12
  const winY = ry + W + 2
  const winPositions = [rx + Math.floor(rw*0.28), rx + Math.floor(rw*0.62)]
  winPositions.forEach(wx => {
    // Window frame
    ctx.fillStyle = c.border
    ctx.fillRect(wx, winY, winW, winH)

    // Glass — light blue tint (+ outside light in dark mode)
    ctx.fillStyle = c.cyan+'18'
    ctx.fillRect(wx+1, winY+1, winW-2, winH-3)
    if (c.dark) {
      ctx.fillStyle = 'rgba(80,120,160,0.10)'
      ctx.fillRect(wx+1, winY+1, winW-2, winH-3)
    }

    // Window cross frame
    ctx.strokeStyle = c.border; ctx.lineWidth = 0.8
    ctx.beginPath(); ctx.moveTo(wx+winW/2, winY+1); ctx.lineTo(wx+winW/2, winY+winH-3); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(wx+1, winY+(winH-2)/2); ctx.lineTo(wx+winW-1, winY+(winH-2)/2); ctx.stroke()

    // Light reflection diagonal inside glass
    ctx.strokeStyle = 'rgba(255,255,255,0.35)'; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(wx+3, winY+2); ctx.lineTo(wx+7, winY+5); ctx.stroke()

    // Windowsill — 2px bar below window
    ctx.fillStyle = c.deskStroke
    ctx.fillRect(wx-1, winY+winH-2, winW+2, 2)
  })
}

// Room-specific furniture props
function drawRoomProps(ctx: CanvasRenderingContext2D, rx:number, ry:number, rw:number, rh:number, teamKey:string, accentColor:string, c:Colors, tick:number) {
  const dark = c.dark

  if (teamKey === 'collection') {
    // Filing cabinet (right wall)
    const fx = rx+rw-22, fy = ry+8
    ctx.fillStyle = dark?'#1e2d4a':'#b8c8d8'
    ctx.fillRect(fx, fy, 14, 20)
    ctx.strokeStyle = dark?'#2d3f5e':'#8aabbb'; ctx.lineWidth = 0.5; ctx.strokeRect(fx, fy, 14, 20)
    ctx.fillStyle = dark?'#2d3f5e':'#a0bbc8'
    ctx.fillRect(fx+1, fy+3, 12, 1); ctx.fillRect(fx+1, fy+10, 12, 1); ctx.fillRect(fx+1, fy+16, 12, 1)
    ctx.fillStyle = dark?'#ffd700':'#b08a00'; ctx.fillRect(fx+5, fy+6, 4, 2); ctx.fillRect(fx+5, fy+13, 4, 2)

    // Plant (corner)
    drawPlant(ctx, rx+rw-10, ry+rh-14, accentColor, dark)

    // Network switch/router (wall-mounted look)
    ctx.fillStyle = dark?'#0d1117':'#dde8f0'
    ctx.fillRect(rx+8, ry+rh-16, 28, 8)
    ctx.strokeStyle = accentColor+'44'; ctx.lineWidth = 0.5; ctx.strokeRect(rx+8, ry+rh-16, 28, 8)
    for (let p=0; p<6; p++) {
      ctx.fillStyle = p%2===0 ? accentColor : (dark?'#484f58':'#9aa5b4')
      ctx.fillRect(rx+10+p*4, ry+rh-13, 2, 4)
    }
  }

  if (teamKey === 'analysis') {
    // Whiteboard (right wall)
    const wx = rx+rw-28, wy = ry+7
    ctx.fillStyle = dark?'#e8f0f8':'#ffffff'
    ctx.fillRect(wx, wy, 22, 16)
    ctx.strokeStyle = dark?'#2d3f5e':'#aac0d0'; ctx.lineWidth = 1; ctx.strokeRect(wx, wy, 22, 16)
    // Board content
    ctx.strokeStyle = dark?'#388bfd':'#1a6fd4'; ctx.lineWidth = 0.8
    ctx.beginPath(); ctx.moveTo(wx+3, wy+5); ctx.lineTo(wx+10, wy+10); ctx.lineTo(wx+14, wy+6); ctx.lineTo(wx+19, wy+12); ctx.stroke()
    ctx.fillStyle = dark?'#ff3b69':'#cc2244'; ctx.font = '5px monospace'; ctx.textAlign='left'
    ctx.fillText('ADF✓', wx+2, wy+14)
    // Board eraser tray
    ctx.fillStyle = dark?'#2d3f5e':'#c8d8e8'; ctx.fillRect(wx, wy+16, 22, 2)

    // Bookshelf (bottom-left)
    const bx = rx+6, by = ry+rh-20
    ctx.fillStyle = dark?'#1a2235':'#c8d4e4'; ctx.fillRect(bx, by, 24, 14)
    ctx.strokeStyle = dark?'#2d3f5e':'#aabbd0'; ctx.lineWidth=0.5; ctx.strokeRect(bx, by, 24, 14)
    const bookColors = [accentColor+'cc','#ff9800','#4caf50cc','#e91e63cc','#388bfdcc']
    bookColors.forEach((bc, i) => { ctx.fillStyle=bc; ctx.fillRect(bx+2+i*4, by+2, 3, 10) })

    // Plant
    drawPlant(ctx, rx+rw-8, ry+rh-12, accentColor, dark)
  }

  if (teamKey === 'ml') {
    // GPU Server rack (right wall) — animated LED blink
    const sx = rx+rw-24, sy = ry+6
    ctx.fillStyle = dark?'#0d1117':'#d0dce8'
    ctx.fillRect(sx, sy, 18, 30)
    ctx.strokeStyle = accentColor+'66'; ctx.lineWidth = 1; ctx.strokeRect(sx, sy, 18, 30)
    // Server units
    for (let u=0; u<4; u++) {
      ctx.fillStyle = dark?'#1a2235':'#c0cdd8'; ctx.fillRect(sx+1, sy+2+u*7, 16, 5)
      ctx.strokeStyle = dark?'#2d3f5e':'#aabbd0'; ctx.lineWidth=0.3; ctx.strokeRect(sx+1, sy+2+u*7, 16, 5)
      // LED blink
      const blink = Math.sin(tick*0.15 + u*1.3) > 0
      ctx.fillStyle = blink ? accentColor : (dark?'#484f58':'#9aa5b4')
      ctx.beginPath(); ctx.arc(sx+14, sy+4+u*7, 1.5, 0, Math.PI*2); ctx.fill()
      // Activity bars
      const barW = 4+Math.floor(Math.sin(tick*0.08+u)*3)
      ctx.fillStyle = accentColor+'88'; ctx.fillRect(sx+2, sy+4+u*7, barW, 2)
    }
    // Rack label
    ctx.font = '5px IBM Plex Mono,monospace'; ctx.fillStyle = accentColor; ctx.textAlign='center'
    ctx.fillText('GPU', sx+9, sy+33)

    // UPS / power strip (floor)
    ctx.fillStyle = dark?'#1e2d4a':'#c0ccd8'; ctx.fillRect(rx+6, ry+rh-12, 30, 6)
    ctx.strokeStyle = dark?'#2d3f5e':'#aabbd0'; ctx.lineWidth=0.5; ctx.strokeRect(rx+6, ry+rh-12, 30, 6)
    for (let p=0; p<4; p++) { ctx.fillStyle=dark?'#0d1117':'#d0dae4'; ctx.fillRect(rx+8+p*7, ry+rh-10, 4, 3) }
  }

  if (teamKey === 'report') {
    // Printer (right wall)
    const px2 = rx+rw-26, py2 = ry+7
    ctx.fillStyle = dark?'#1a2235':'#d0dce8'; ctx.fillRect(px2, py2, 20, 14)
    ctx.strokeStyle = dark?'#2d3f5e':'#aabbd0'; ctx.lineWidth=0.5; ctx.strokeRect(px2, py2, 20, 14)
    ctx.fillStyle = dark?'#0d1117':'#c0ccd8'; ctx.fillRect(px2+2, py2+4, 16, 6)
    // Paper output
    const paperOut = Math.floor((tick/40)%3)
    if (paperOut > 0) { ctx.fillStyle = '#e6edf3'; ctx.fillRect(px2+5, py2+9, 10, paperOut*1.5+1) }
    // Printer light
    ctx.fillStyle = Math.sin(tick*0.05)>0 ? c.green : c.txtMut
    ctx.beginPath(); ctx.arc(px2+16, py2+2, 2, 0, Math.PI*2); ctx.fill()

    // Plant
    drawPlant(ctx, rx+rw-8, ry+rh-12, accentColor, dark)
  }

  // ── OUTBOX tray (all teams, near door) ──
  const trayX = rx + rw - 18, trayY = ry + Math.floor(rh * 0.6) - 8
  // Small table
  ctx.fillStyle = dark ? '#1a2235' : '#c8d4e4'
  ctx.fillRect(trayX, trayY, 14, 10)
  ctx.strokeStyle = accentColor + '44'; ctx.lineWidth = 0.5
  ctx.strokeRect(trayX, trayY, 14, 10)
  // Table legs
  ctx.fillStyle = dark ? '#0d1117' : '#b0bfcc'
  ctx.fillRect(trayX+1, trayY+10, 2, 3); ctx.fillRect(trayX+11, trayY+10, 2, 3)
  // Document stack on tray
  for (let d2 = 2; d2 >= 0; d2--) {
    ctx.fillStyle = d2 === 0 ? '#e6edf3' : (dark ? '#c0ccd8' : '#f0f4f8')
    ctx.fillRect(trayX + 2 + d2*0.5, trayY + 1 - d2, 10, 7)
  }
  // Color tab on top document
  ctx.fillStyle = accentColor + 'cc'
  ctx.fillRect(trayX + 3, trayY + 2, 3, 5)
  // Text lines on document
  ctx.fillStyle = dark ? '#484f58' : '#9aa5b4'
  ctx.fillRect(trayX + 7, trayY + 2, 4, 1)
  ctx.fillRect(trayX + 7, trayY + 4, 3, 1)
  // "OUT" label
  ctx.font = '4px IBM Plex Mono,monospace'; ctx.fillStyle = accentColor + '88'
  ctx.textAlign = 'center'; ctx.fillText('OUT', trayX + 7, trayY + 15)
}

function drawPlant(ctx: CanvasRenderingContext2D, px:number, py:number, accentColor:string, dark:boolean) {
  // Pot
  ctx.fillStyle = dark?'#5d3a1a':'#a06030'
  ctx.beginPath(); ctx.moveTo(px-4, py); ctx.lineTo(px+4, py); ctx.lineTo(px+3, py+6); ctx.lineTo(px-3, py+6); ctx.closePath(); ctx.fill()
  // Soil
  ctx.fillStyle = dark?'#2d1a08':'#6b3d18'
  ctx.fillRect(px-3, py+1, 6, 2)
  // Leaves
  ctx.fillStyle = '#2d8a2a'
  ctx.beginPath(); ctx.ellipse(px-3, py-4, 4, 2, -0.5, 0, Math.PI*2); ctx.fill()
  ctx.beginPath(); ctx.ellipse(px+3, py-5, 4, 2, 0.5, 0, Math.PI*2); ctx.fill()
  ctx.beginPath(); ctx.ellipse(px, py-7, 3, 2, 0, 0, Math.PI*2); ctx.fill()
  ctx.fillStyle = '#3daa3a'
  ctx.beginPath(); ctx.ellipse(px-2, py-5, 2.5, 1.5, -0.3, 0, Math.PI*2); ctx.fill()
}

function drawPixelChar(ctx: CanvasRenderingContext2D, cx:number, cy:number, color:string, state:CharState, tick:number, xSlot:number, ySlot:number, sprite:HTMLImageElement|null, c:Colors) {
  const bounce = state !== 'idle' && state !== 'error' ? Math.sin(tick*0.09 + xSlot*1.4 + ySlot*2.3)*2.5 : 0
  const shake  = state === 'error' ? Math.sin(tick*0.6)*3 : 0
  const px = cx+shake, py = cy+bounce

  if (sprite) { ctx.drawImage(sprite, px-11, py-22, 22, 22); return }

  const headR = 5
  ctx.fillStyle = c.shadow
  ctx.beginPath(); ctx.ellipse(px, py+2, 8, 3, 0, 0, Math.PI*2); ctx.fill()
  ctx.fillStyle = color+'cc'; ctx.fillRect(px-5, py-10, 10, 12)
  ctx.fillStyle = c.charHead; ctx.beginPath(); ctx.arc(px, py-14, headR, 0, Math.PI*2); ctx.fill()
  ctx.fillStyle = color;      ctx.fillRect(px-headR, py-20, headR*2, 6)
  ctx.fillStyle = c.charEye;  ctx.fillRect(px-3, py-15, 2, 2); ctx.fillRect(px+1, py-15, 2, 2)
}

// Isometric 2.5D desk — top-down with depth illusion
function drawDesk(ctx: CanvasRenderingContext2D, dx:number, dy:number, dw:number, dh:number, teamColor:string, hasMonitor:boolean, c:Colors) {
  const depth = 5  // side depth in px

  // ── Desk top surface ──
  ctx.fillStyle = c.deskFill
  ctx.beginPath()
  ctx.moveTo(dx, dy)
  ctx.lineTo(dx+dw, dy)
  ctx.lineTo(dx+dw, dy+dh)
  ctx.lineTo(dx, dy+dh)
  ctx.closePath()
  ctx.fill()

  // Desk top highlight (wood grain illusion — lighter strip)
  ctx.fillStyle = 'rgba(255,255,255,0.07)'
  ctx.fillRect(dx+2, dy+2, dw-4, Math.floor(dh*0.35))

  // Desk front face (depth)
  ctx.fillStyle = c.deskStroke
  ctx.beginPath()
  ctx.moveTo(dx, dy+dh)
  ctx.lineTo(dx+dw, dy+dh)
  ctx.lineTo(dx+dw, dy+dh+depth)
  ctx.lineTo(dx, dy+dh+depth)
  ctx.closePath()
  ctx.fill()

  // Desk right side face
  ctx.fillStyle = 'rgba(0,0,0,0.18)'
  ctx.beginPath()
  ctx.moveTo(dx+dw, dy)
  ctx.lineTo(dx+dw+depth*0.6, dy-depth*0.5)
  ctx.lineTo(dx+dw+depth*0.6, dy+dh-depth*0.5)
  ctx.lineTo(dx+dw, dy+dh)
  ctx.closePath()
  ctx.fill()

  // Border
  ctx.strokeStyle = c.deskStroke; ctx.lineWidth = 0.8
  ctx.strokeRect(dx, dy, dw, dh)

  // Desk legs (2 visible front corners)
  ctx.fillStyle = c.charStand
  ctx.fillRect(dx+2, dy+dh, 3, depth+2)
  ctx.fillRect(dx+dw-5, dy+dh, 3, depth+2)

  if (hasMonitor) {
    const cx = dx+dw/2
    const my = dy - 18

    // Monitor shadow on desk
    ctx.fillStyle = 'rgba(0,0,0,0.15)'
    ctx.beginPath(); ctx.ellipse(cx, dy+3, 9, 3, 0, 0, Math.PI*2); ctx.fill()

    // Monitor stand base
    ctx.fillStyle = c.charStand
    ctx.fillRect(cx-5, dy-2, 10, 4)
    ctx.fillRect(cx-2, dy-6, 4, 6)

    // Monitor bezel (back face — right+bottom)
    ctx.fillStyle = 'rgba(0,0,0,0.4)'
    ctx.fillRect(cx-10, my-1, 21, 17)

    // Monitor bezel front
    ctx.fillStyle = c.monitorBg
    ctx.fillRect(cx-10, my, 20, 16)
    ctx.strokeStyle = c.deskStroke; ctx.lineWidth = 0.8
    ctx.strokeRect(cx-10, my, 20, 16)

    // Screen glow
    ctx.fillStyle = teamColor+'66'
    ctx.fillRect(cx-8, my+2, 16, 11)

    // Animated scan line
    ctx.fillStyle = 'rgba(255,255,255,0.12)'
    ctx.fillRect(cx-8, my+2, 16, 3)

    // Screen content: tiny chart bars
    ctx.fillStyle = teamColor+'cc'
    const barH = [4,6,3,7,5,4,8,5]
    barH.forEach((h, i) => {
      ctx.fillRect(cx-7+i*2, my+12-h, 1.5, h)
    })

    // Keyboard
    ctx.fillStyle = c.charStand
    ctx.fillRect(dx+4, dy+2, dw-8, 4)
    ctx.strokeStyle = c.border; ctx.lineWidth = 0.3
    ctx.strokeRect(dx+4, dy+2, dw-8, 4)
    // Key rows
    ctx.fillStyle = 'rgba(255,255,255,0.06)'
    for (let k=0; k<3; k++) ctx.fillRect(dx+5+k*6, dy+3, 5, 2)

    // Coffee cup (small, right corner of desk)
    const cupX = dx+dw-8, cupY = dy+2
    ctx.fillStyle = '#7a5230'
    ctx.fillRect(cupX, cupY, 5, 5)
    ctx.fillStyle = '#c8956a'
    ctx.fillRect(cupX+1, cupY+1, 3, 2)  // coffee surface
    ctx.fillStyle = c.deskStroke
    ctx.strokeRect(cupX, cupY, 5, 5)
  }
}

function roundRect(ctx: CanvasRenderingContext2D, x:number, y:number, w:number, h:number, r:number) {
  ctx.beginPath(); ctx.moveTo(x+r, y)
  ctx.lineTo(x+w-r, y); ctx.quadraticCurveTo(x+w, y, x+w, y+r)
  ctx.lineTo(x+w, y+h-r); ctx.quadraticCurveTo(x+w, y+h, x+w-r, y+h)
  ctx.lineTo(x+r, y+h); ctx.quadraticCurveTo(x, y+h, x, y+h-r)
  ctx.lineTo(x, y+r); ctx.quadraticCurveTo(x, y, x+r, y)
  ctx.closePath()
}

function drawPanel(ctx: CanvasRenderingContext2D, x:number, y:number, w:number, h:number, title:string, accent:string, tick:number, rows:Array<{label:string;right:string;color:string}>, c:Colors) {
  ctx.fillStyle = c.panel; roundRect(ctx, x, y, w, h, 4); ctx.fill()
  ctx.strokeStyle = accent+'44'; ctx.lineWidth = 1; roundRect(ctx, x+0.5, y+0.5, w-1, h-1, 4); ctx.stroke()
  ctx.fillStyle = accent+'22'; ctx.fillRect(x+1, y+1, w-2, 14)
  ctx.font = 'bold 9px IBM Plex Mono, monospace'; ctx.fillStyle = accent; ctx.textAlign = 'left'
  ctx.fillText(title, x+8, y+12)
  const scanY = y+14 + ((tick*0.5)%(h-14))
  ctx.fillStyle = accent+'12'; ctx.fillRect(x+1, scanY, w-2, 2)
  ctx.strokeStyle = accent+'22'; ctx.lineWidth = 0.5
  ctx.beginPath(); ctx.moveTo(x, y+16); ctx.lineTo(x+w, y+16); ctx.stroke()
  rows.forEach((row, i) => {
    const ry = y+30+i*20
    ctx.font = '9px IBM Plex Mono, monospace'; ctx.fillStyle = c.txtSec; ctx.textAlign = 'left'; ctx.fillText(row.label, x+8, ry)
    ctx.fillStyle = row.color; ctx.textAlign = 'right'; ctx.fillText(row.right, x+w-8, ry)
    ctx.strokeStyle = c.border; ctx.lineWidth = 0.3; ctx.beginPath(); ctx.moveTo(x+8, ry+4); ctx.lineTo(x+w-8, ry+4); ctx.stroke()
  })
}

// ── CEO Room ──────────────────────────────────────────────────────────────

function drawCEORoom(ctx: CanvasRenderingContext2D, cx:number, cy:number, cw:number, ch:number, c:Colors, tick:number) {
  const dark = c.dark

  // Floor — dark wood tone
  ctx.fillStyle = dark ? '#0c0806' : '#f0e8d8'
  ctx.fillRect(cx, cy, cw, ch)
  // Wood grain lines
  ctx.strokeStyle = dark ? '#14100a' : '#e0d4c0'
  ctx.lineWidth = 0.4
  for (let gy = cy; gy <= cy+ch; gy += 8) { ctx.beginPath(); ctx.moveTo(cx, gy); ctx.lineTo(cx+cw, gy); ctx.stroke() }

  // Walls
  const W2 = 5
  ctx.fillStyle = dark ? '#0a0e18' : '#c8d4e0'
  ctx.fillRect(cx, cy, cw, W2)       // top
  ctx.fillRect(cx, cy, W2, ch)       // left
  ctx.fillRect(cx+cw-W2, cy, W2, ch) // right
  // Bottom wall with door gap (opens to corridor)
  const doorW = 24, doorX = cx + cw*0.4
  ctx.fillRect(cx, cy+ch-W2, doorX-cx, W2)
  ctx.fillRect(doorX+doorW, cy+ch-W2, cw-(doorX+doorW-cx), W2)
  // Door frame
  ctx.strokeStyle = c.gold+'88'; ctx.lineWidth = 2
  ctx.beginPath(); ctx.moveTo(doorX, cy+ch-W2); ctx.lineTo(doorX, cy+ch); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(doorX+doorW, cy+ch-W2); ctx.lineTo(doorX+doorW, cy+ch); ctx.stroke()
  // Gold accent strip
  ctx.fillStyle = c.gold+'55'; ctx.fillRect(cx, cy, cw, 3)

  // Label badge
  ctx.fillStyle = (dark ? '#141008' : '#f5f0e0') + 'cc'
  ctx.fillRect(cx+6, cy+6, 80, 14)
  ctx.strokeStyle = c.gold+'66'; ctx.lineWidth = 0.5; ctx.strokeRect(cx+6.5, cy+6.5, 79, 13)
  ctx.font = 'bold 9px IBM Plex Mono, monospace'; ctx.fillStyle = c.gold; ctx.textAlign = 'left'
  ctx.fillText('[ CEO ] OFFICE', cx+10, cy+16)

  // ── Executive desk (bigger, centered) ──
  const deskW2 = Math.min(50, cw*0.4), deskH2 = 20
  const dx = cx + cw*0.5 - deskW2/2, dy = cy + ch*0.5
  drawDesk(ctx, dx, dy, deskW2, deskH2, c.gold, true, c)

  // CEO character
  drawPixelChar(ctx, dx+deskW2/2, dy-4, c.gold, 'reviewing', tick, 0, 0, null, c)

  // Nameplate on desk
  ctx.fillStyle = c.gold+'44'; ctx.fillRect(dx+deskW2/2-12, dy+2, 24, 6)
  ctx.font = '5px IBM Plex Mono, monospace'; ctx.fillStyle = c.gold; ctx.textAlign = 'center'
  ctx.fillText('CEO', dx+deskW2/2, dy+7)

  // Bookshelf (left wall)
  const bx = cx+W2+2, by = cy+W2+4
  ctx.fillStyle = dark ? '#1a1410' : '#d8c8a8'
  ctx.fillRect(bx, by, 18, ch-W2*2-8)
  ctx.strokeStyle = dark ? '#2a1e14' : '#c0b090'; ctx.lineWidth = 0.5; ctx.strokeRect(bx, by, 18, ch-W2*2-8)
  // Book spines
  const bkColors = [c.gold+'cc','#c04040','#4060a0','#40a060','#a06040','#6040a0']
  const shelfH = (ch-W2*2-10) / bkColors.length
  bkColors.forEach((bc, i) => { ctx.fillStyle = bc; ctx.fillRect(bx+2, by+2+i*shelfH, 14, shelfH-3) })

  // Trophy / award (right wall)
  const tx = cx+cw-W2-14, ty = cy+ch*0.3
  ctx.fillStyle = dark ? '#1a1410' : '#d8c8a8'
  ctx.fillRect(tx, ty, 10, 14)
  ctx.fillStyle = c.gold
  ctx.beginPath(); ctx.arc(tx+5, ty+4, 3, 0, Math.PI*2); ctx.fill()
  ctx.fillRect(tx+3, ty+7, 4, 5)
  ctx.font = '4px IBM Plex Mono, monospace'; ctx.fillStyle = c.gold+'88'; ctx.textAlign = 'center'
  ctx.fillText('MVP', tx+5, ty+16)

  // Window (top wall, panoramic)
  const ww = Math.min(40, cw*0.3), wx = cx + cw*0.5 - ww/2, wy = cy+W2
  ctx.fillStyle = c.border; ctx.fillRect(wx-1, wy-1, ww+2, 14)
  ctx.fillStyle = dark ? '#0a1828' : '#c8e0f8'
  ctx.fillRect(wx, wy, ww, 12)
  ctx.fillStyle = 'rgba(255,255,255,0.08)'; ctx.fillRect(wx+2, wy+1, ww*0.4, 5) // reflection
  ctx.fillStyle = c.deskStroke; ctx.fillRect(wx, wy+12, ww, 2) // sill
  ctx.strokeStyle = c.border; ctx.lineWidth = 0.5
  ctx.beginPath(); ctx.moveTo(wx+ww/2, wy); ctx.lineTo(wx+ww/2, wy+12); ctx.stroke() // divider

  // Ceiling light
  drawCeilingLight(ctx, cx+cw*0.5, cy+ch*0.2, cw*0.5, c.gold)
}

// ── Main draw ──────────────────────────────────────────────────────────────

function drawOffice(ctx: CanvasRenderingContext2D, W:number, H:number, chars:Character[], particles:Particle[], deliveries:Delivery[], tick:number, c:Colors, clickedCharId?: string|null, cData?: CollectorBubbleData, indResults?: Record<string,any>|null) {
  ctx.fillStyle = c.bg; ctx.fillRect(0, 0, W, H)

  const GAP = 4
  const roomW = Math.floor(W*0.38)
  const corrW = W - roomW - GAP
  const roomH = Math.floor((H - 3*GAP) / 4)
  const CEO_OFFSET = 16  // push CEO room down from top edge
  const ceoH = Math.floor(roomH * 0.7)
  const CEO_GAP = 14
  const corrTopY = CEO_OFFSET + ceoH + CEO_GAP
  const teamMeta = getTeamMeta(c)
  const teamKeys = ['collection','analysis','ml','report'] as const

  // ── Team rooms ──
  teamKeys.forEach((teamKey, idx) => {
    const rx = 0, ry = idx*(roomH+GAP)
    const meta = teamMeta[teamKey]

    drawRoomFloor(ctx, rx, ry, roomW, roomH, teamKey, c)
    drawRoomWalls(ctx, rx, ry, roomW, roomH, meta.color, c, 'right')
    drawCeilingLight(ctx, rx + roomW*0.3, ry + roomH*0.25, roomW*0.4, meta.color)
    drawCeilingLight(ctx, rx + roomW*0.72, ry + roomH*0.25, roomW*0.4, meta.color)
    drawRoomProps(ctx, rx, ry, roomW, roomH, teamKey, meta.color, c, tick)

    // 인접 방 사이 내부 문 (수집↔분석, 분석↔ML, ML↔리포트)
    if (idx < 3) {
      const doorX = roomW * 0.5 - 8
      const doorY = ry + roomH - 1
      ctx.fillStyle = c.dark ? '#1a2a3a' : '#c8d4e0'
      ctx.fillRect(doorX, doorY, 16, GAP + 2)
      ctx.strokeStyle = meta.color + '66'; ctx.lineWidth = 0.5
      ctx.strokeRect(doorX, doorY, 16, GAP + 2)
      // 문 손잡이
      ctx.fillStyle = meta.color + 'aa'
      ctx.beginPath(); ctx.arc(doorX + 12, doorY + (GAP + 2) / 2, 1.5, 0, Math.PI * 2); ctx.fill()
    }

    // Team label badge
    ctx.fillStyle = meta.bg; ctx.fillRect(rx+6, ry+5, 86, 14)
    ctx.strokeStyle = meta.color+'66'; ctx.lineWidth = 0.5; ctx.strokeRect(rx+6.5, ry+5.5, 85, 13)
    ctx.font = 'bold 9px IBM Plex Mono, monospace'; ctx.fillStyle = meta.color; ctx.textAlign = 'left'
    ctx.fillText(`[ ${meta.short} ] ${meta.label}`, rx+10, ry+15)

    const teamChars = chars.filter(ch => ch.team === teamKey)
    const cols = 3
    const deskW = Math.floor((roomW-20)/cols) - 8
    const deskH = 16
    const rowH2 = Math.floor((roomH-30)/2)

    teamChars.forEach(ch => {
      const colSpan = (roomW-20)/cols
      const deskX = rx+10 + ch.x*colSpan + (colSpan-deskW)/2
      const deskY = ry+28 + ch.y*rowH2 + rowH2*0.55
      const charX = deskX+deskW/2, charY = deskY-4
      const si = STATE_INFO[ch.state] ?? STATE_INFO.idle
      const siColor = c[si.colorKey] as string

      // 책상은 항상 그림
      drawDesk(ctx, deskX, deskY, deskW, deskH, meta.color, ch.state !== 'idle' && ch.state !== 'delivering', c)
      // 서무 배달 중이면 캐릭터만 안 그림 (책상은 유지)
      if (ch.state === 'delivering') {
        // 빈 의자 표시 — 이름만 남김
        ctx.font = '10px IBM Plex Mono, monospace'; ctx.fillStyle = c.txtMut; ctx.textAlign = 'center'
        ctx.fillText(ch.label, charX, deskY+deskH+9)
        return
      }
      drawPixelChar(ctx, charX, charY, meta.color, ch.state, tick, ch.x, ch.y, getSprite(ch.role), c)

      if (si.symbol) {
        ctx.font = 'bold 10px IBM Plex Mono, monospace'; ctx.fillStyle = siColor; ctx.textAlign = 'center'
        ctx.fillText(si.symbol, charX+8, charY-20)
      }
      ctx.font = '10px IBM Plex Mono, monospace'; ctx.fillStyle = c.txtSec; ctx.textAlign = 'center'
      ctx.fillText(ch.label, charX, deskY+deskH+9)

      if (ch.state !== 'idle') {
        const bw=deskW-2, bx=deskX+1, by=deskY+deskH+9
        ctx.fillStyle = c.border; ctx.fillRect(bx, by, bw, 2)
        ctx.fillStyle = siColor;  ctx.fillRect(bx, by, bw*ch.progress, 2)
      }

      // Speech bubble (cycling)
      if (ch.state !== 'idle' && ch.statusText && tick%240 < 80) {
        const bx=charX-24, by=charY-36
        ctx.fillStyle = c.panel+'ee'; roundRect(ctx, bx, by, 48, 13, 3); ctx.fill()
        ctx.strokeStyle = meta.color+'88'; ctx.lineWidth = 0.5; roundRect(ctx, bx, by, 48, 13, 3); ctx.stroke()
        ctx.font = '7px IBM Plex Mono, monospace'; ctx.fillStyle = c.txt; ctx.textAlign = 'center'
        ctx.fillText(ch.statusText, charX, by+9)
      }
    })

    // Team progress strip
    const active = teamChars.filter(ch => ch.state !== 'idle')
    if (active.length) {
      const avg = active.reduce((s,ch)=>s+ch.progress,0)/active.length
      ctx.fillStyle = c.border; ctx.fillRect(rx+6, ry+roomH-8, roomW-12, 3)
      ctx.fillStyle = meta.color; ctx.fillRect(rx+6, ry+roomH-8, (roomW-12)*avg, 3)
      ctx.font = '7px IBM Plex Mono, monospace'; ctx.fillStyle = meta.color; ctx.textAlign = 'right'
      ctx.fillText(`${Math.round(avg*100)}%`, rx+roomW-4, ry+roomH-10)
    }

    // Room number badge — just inside the door gap on the right wall
    const roomNums = ['R01','R02','R03','R04']
    const rnLabel = roomNums[idx]
    const rnDoorY = ry + roomH*0.6
    ctx.fillStyle = meta.color+'22'
    ctx.fillRect(roomW-14, rnDoorY+2, 12, 8)
    ctx.strokeStyle = meta.color+'44'; ctx.lineWidth = 0.5
    ctx.strokeRect(roomW-14, rnDoorY+2, 12, 8)
    ctx.font = '7px IBM Plex Mono,monospace'; ctx.fillStyle = c.txtMut; ctx.textAlign = 'center'
    ctx.fillText(rnLabel, roomW-8, rnDoorY+9)
  })

  // ── CEO Room (top-right, offset from top) ──
  const cx = roomW+GAP
  drawCEORoom(ctx, cx, CEO_OFFSET, corrW, ceoH, c, tick)

  // ── Corridor (below CEO room) ──
  ctx.fillStyle = c.corridorBg; ctx.fillRect(cx, corrTopY, corrW, H - corrTopY)

  // Corridor floor tile grid
  ctx.strokeStyle = c.corridorLn; ctx.lineWidth = 0.5
  for (let gy=corrTopY; gy<H; gy+=18) { ctx.beginPath(); ctx.moveTo(cx,gy); ctx.lineTo(cx+corrW,gy); ctx.stroke() }
  for (let gx=cx; gx<=cx+corrW; gx+=18) { ctx.beginPath(); ctx.moveTo(gx,corrTopY); ctx.lineTo(gx,H); ctx.stroke() }

  // Corridor left border wall
  ctx.strokeStyle = c.border; ctx.lineWidth = 1
  ctx.beginPath(); ctx.moveTo(cx, corrTopY); ctx.lineTo(cx, H); ctx.stroke()

  // Centerline stripe — dashed vertical line down middle of corridor
  const corrMidX = cx + corrW * 0.5
  ctx.strokeStyle = c.borderBrt+'44'; ctx.lineWidth = 2
  ctx.setLineDash([6, 8])
  ctx.beginPath(); ctx.moveTo(corrMidX, corrTopY); ctx.lineTo(corrMidX, H); ctx.stroke()
  ctx.setLineDash([])

  // Corridor ceiling lights
  for (let li = 0; li < 3; li++) {
    const lightY = corrTopY + li * roomH + roomH * 0.3
    // Light fixture rect
    ctx.fillStyle = c.dark ? '#1a2a3a' : '#d0dde8'
    ctx.fillRect(corrMidX - 12, lightY - 2, 24, 4)
    ctx.strokeStyle = c.borderBrt+'66'; ctx.lineWidth = 0.5
    ctx.strokeRect(corrMidX - 12, lightY - 2, 24, 4)
    // Glow beneath light
    const lgGrad = ctx.createRadialGradient(corrMidX, lightY+2, 0, corrMidX, lightY+2, corrW*0.6)
    lgGrad.addColorStop(0, c.dark ? 'rgba(180,220,255,0.10)' : 'rgba(255,255,240,0.18)')
    lgGrad.addColorStop(1, 'transparent')
    ctx.fillStyle = lgGrad
    ctx.fillRect(cx, lightY, corrW, roomH * 0.5)
  }

  // Exit sign markers on left corridor wall
  const exitPositions = [Math.floor(H*0.12), Math.floor(H*0.38), Math.floor(H*0.62), Math.floor(H*0.88)]
  exitPositions.forEach((ey, ei) => {
    if (ei % 2 === 0) {
      // Exit sign (green rectangle)
      ctx.fillStyle = c.green+'99'
      ctx.fillRect(cx+2, ey-4, 10, 6)
      ctx.font = '4px IBM Plex Mono,monospace'; ctx.fillStyle = '#ffffff'; ctx.textAlign = 'center'
      ctx.fillText('EXIT', cx+7, ey+1)
    } else {
      // Fire extinguisher marker (red dot)
      ctx.fillStyle = c.red+'88'
      ctx.beginPath(); ctx.arc(cx+5, ey, 4, 0, Math.PI*2); ctx.fill()
      ctx.strokeStyle = c.red+'44'; ctx.lineWidth = 0.5
      ctx.beginPath(); ctx.arc(cx+5, ey, 4, 0, Math.PI*2); ctx.stroke()
    }
  })

  // ── Corridor Facilities (right side of corridor) ──
  {
    const facW = Math.floor(corrW * 0.35)
    const facX = cx + corrW - facW - 4
    const facGap = 4
    const facH = Math.floor((H - corrTopY - facGap * 5) / 4)
    const facY0 = corrTopY + facGap
    const facY1 = facY0 + facH + facGap
    const facY2 = facY1 + facH + facGap
    const facY3 = facY2 + facH + facGap

    const facBg = c.dark ? '#0a1018' : '#dae4ee'
    const facBorder = c.dark ? '#1a2a3a' : '#b0c0d0'

    // ── 1. Meeting Room ──
    ctx.fillStyle = facBg; ctx.fillRect(facX, facY0, facW, facH)
    ctx.strokeStyle = c.blue + '55'; ctx.lineWidth = 0.5; ctx.strokeRect(facX, facY0, facW, facH)
    ctx.strokeStyle = c.blue + '33'; ctx.lineWidth = 1
    ctx.setLineDash([3, 3])
    ctx.beginPath(); ctx.moveTo(facX, facY0); ctx.lineTo(facX + facW, facY0); ctx.stroke()
    ctx.setLineDash([])
    const tblW = Math.floor(facW * 0.5), tblH = Math.floor(facH * 0.28)
    const tblX = facX + (facW - tblW) / 2, tblY = facY0 + (facH - tblH) / 2 + 2
    ctx.fillStyle = c.dark ? '#14202e' : '#c0ccd8'; ctx.fillRect(tblX, tblY, tblW, tblH)
    ctx.strokeStyle = facBorder; ctx.lineWidth = 0.5; ctx.strokeRect(tblX, tblY, tblW, tblH)
    const chairColor = c.dark ? '#2a3a4a' : '#9aa8b8'
    const chairR = 1.5
    const chairPositions: number[][] = [
      [tblX + tblW * 0.3, tblY - 3], [tblX + tblW * 0.7, tblY - 3],
      [tblX + tblW * 0.3, tblY + tblH + 3], [tblX + tblW * 0.7, tblY + tblH + 3],
      [tblX - 3, tblY + tblH * 0.5], [tblX + tblW + 3, tblY + tblH * 0.5],
    ]
    ctx.fillStyle = chairColor
    chairPositions.forEach(([chx, chy]) => { ctx.beginPath(); ctx.arc(chx, chy, chairR, 0, Math.PI * 2); ctx.fill() })
    ctx.fillStyle = c.dark ? '#1a2a3a' : '#e8f0f8'; ctx.fillRect(facX + facW - 5, facY0 + 4, 3, Math.floor(facH * 0.4))
    ctx.strokeStyle = c.blue + '44'; ctx.lineWidth = 0.5; ctx.strokeRect(facX + facW - 5, facY0 + 4, 3, Math.floor(facH * 0.4))
    ctx.font = '4px IBM Plex Mono,monospace'; ctx.fillStyle = c.blue + 'aa'; ctx.textAlign = 'center'
    ctx.fillText('MEETING', facX + facW / 2, facY0 + facH - 3)

    // ── 2. Break Room ──
    ctx.fillStyle = facBg; ctx.fillRect(facX, facY1, facW, facH)
    ctx.strokeStyle = c.green + '44'; ctx.lineWidth = 0.5; ctx.strokeRect(facX, facY1, facW, facH)
    const sofaW = Math.floor(facW * 0.45), sofaH = Math.floor(facH * 0.2)
    const sofaX = facX + 4, sofaY = facY1 + Math.floor(facH * 0.3)
    ctx.fillStyle = c.dark ? '#1a2e1a' : '#b8d8b8'; ctx.fillRect(sofaX, sofaY, sofaW, sofaH)
    ctx.strokeStyle = c.green + '44'; ctx.lineWidth = 0.5; ctx.strokeRect(sofaX, sofaY, sofaW, sofaH)
    const cmX = facX + facW - 12, cmY = facY1 + 5
    ctx.fillStyle = c.dark ? '#2a1a0a' : '#c8a878'; ctx.fillRect(cmX, cmY, 7, 9)
    ctx.strokeStyle = facBorder; ctx.lineWidth = 0.5; ctx.strokeRect(cmX, cmY, 7, 9)
    ctx.fillStyle = c.dark ? '#3a3a3a' : '#888888'; ctx.fillRect(cmX + 2, cmY - 2, 3, 2)
    const vmX = facX + facW - 12, vmY = facY1 + Math.floor(facH * 0.55)
    ctx.fillStyle = c.dark ? '#0a1a2e' : '#a0b8d0'; ctx.fillRect(vmX, vmY, 8, 12)
    ctx.strokeStyle = facBorder; ctx.lineWidth = 0.5; ctx.strokeRect(vmX, vmY, 8, 12)
    ctx.fillStyle = c.dark ? '#1a3a5a' : '#7098b8'; ctx.fillRect(vmX + 1, vmY + 1, 6, 6)
    ctx.fillStyle = c.green + '88'
    ctx.beginPath(); ctx.arc(facX + Math.floor(facW * 0.55), facY1 + Math.floor(facH * 0.65), 3, 0, Math.PI * 2); ctx.fill()
    ctx.fillStyle = c.dark ? '#2a1a0a' : '#8a6840'; ctx.fillRect(facX + Math.floor(facW * 0.55) - 2, facY1 + Math.floor(facH * 0.65) + 2, 4, 3)
    ctx.font = '4px IBM Plex Mono,monospace'; ctx.fillStyle = c.green + 'aa'; ctx.textAlign = 'center'
    ctx.fillText('BREAK', facX + facW / 2, facY1 + facH - 3)

    // ── 3. Restroom ──
    ctx.fillStyle = facBg; ctx.fillRect(facX, facY2, facW, facH)
    ctx.strokeStyle = c.txtMut + '44'; ctx.lineWidth = 0.5; ctx.strokeRect(facX, facY2, facW, facH)
    const doorX = facX + 3, doorY = facY2 + Math.floor(facH * 0.25)
    ctx.fillStyle = facBorder; ctx.fillRect(doorX, doorY, 5, 8)
    ctx.fillStyle = c.dark ? '#2a2a2a' : '#aaaaaa'
    ctx.beginPath(); ctx.arc(doorX + 4, doorY + 4, 0.8, 0, Math.PI * 2); ctx.fill()
    ctx.font = '5px IBM Plex Mono,monospace'; ctx.fillStyle = c.txtMut; ctx.textAlign = 'center'
    ctx.fillText('M', facX + Math.floor(facW * 0.35), facY2 + Math.floor(facH * 0.45))
    ctx.fillText('F', facX + Math.floor(facW * 0.6), facY2 + Math.floor(facH * 0.45))
    ctx.strokeStyle = c.txtMut + '44'; ctx.lineWidth = 0.5
    ctx.beginPath(); ctx.moveTo(facX + Math.floor(facW * 0.48), facY2 + Math.floor(facH * 0.3)); ctx.lineTo(facX + Math.floor(facW * 0.48), facY2 + Math.floor(facH * 0.55)); ctx.stroke()
    const sinkX = facX + Math.floor(facW * 0.3), sinkY = facY2 + Math.floor(facH * 0.6)
    ctx.fillStyle = c.dark ? '#1a2a3a' : '#c0d0e0'; ctx.fillRect(sinkX, sinkY, Math.floor(facW * 0.4), 4)
    ctx.strokeStyle = facBorder; ctx.lineWidth = 0.5; ctx.strokeRect(sinkX, sinkY, Math.floor(facW * 0.4), 4)
    ctx.font = '4px IBM Plex Mono,monospace'; ctx.fillStyle = c.txtMut + 'aa'; ctx.textAlign = 'center'
    ctx.fillText('WC', facX + facW / 2, facY2 + facH - 3)

    // ── 4. Elevator ──
    ctx.fillStyle = facBg; ctx.fillRect(facX, facY3, facW, facH)
    ctx.strokeStyle = c.txtSec + '44'; ctx.lineWidth = 0.5; ctx.strokeRect(facX, facY3, facW, facH)
    const elvMidX = facX + Math.floor(facW / 2)
    const elvDoorTop = facY3 + 4, elvDoorH = Math.floor(facH * 0.5)
    ctx.strokeStyle = c.txtSec + '88'; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(elvMidX - 1, elvDoorTop); ctx.lineTo(elvMidX - 1, elvDoorTop + elvDoorH); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(elvMidX + 1, elvDoorTop); ctx.lineTo(elvMidX + 1, elvDoorTop + elvDoorH); ctx.stroke()
    ctx.strokeStyle = facBorder; ctx.lineWidth = 0.5
    ctx.strokeRect(elvMidX - Math.floor(facW * 0.3), elvDoorTop, Math.floor(facW * 0.6), elvDoorH)
    ctx.fillStyle = c.txtSec
    ctx.font = '5px IBM Plex Mono,monospace'; ctx.textAlign = 'center'
    ctx.fillText('\u25B2', elvMidX - 4, elvDoorTop + elvDoorH + 8)
    ctx.fillText('\u25BC', elvMidX + 4, elvDoorTop + elvDoorH + 8)
    const dispX = elvMidX - 8, dispY = elvDoorTop - 6
    ctx.fillStyle = c.dark ? '#0a1a0a' : '#e0e8e0'; ctx.fillRect(dispX, dispY, 16, 5)
    ctx.strokeStyle = c.txtSec + '44'; ctx.lineWidth = 0.5; ctx.strokeRect(dispX, dispY, 16, 5)
    ctx.font = '3px IBM Plex Mono,monospace'; ctx.fillStyle = c.green; ctx.textAlign = 'center'
    ctx.fillText('B1-12F', elvMidX, dispY + 4)
    ctx.font = '4px IBM Plex Mono,monospace'; ctx.fillStyle = c.txtSec + 'aa'; ctx.textAlign = 'center'
    ctx.fillText('ELV', facX + facW / 2, facY3 + facH - 3)
  }

  // ── Deliveries (room-to-room path) ──
  deliveries.forEach(d => {
    const t = d.progress

    // ── Compute positions ──
    const corrX = corrMidX
    const cols2 = 3, colSpan2 = (roomW-20)/cols2, deskW2 = colSpan2-8
    const rowH3 = Math.floor((roomH-30)/2)

    // 서무 desk position (x:2, y:1 in room grid) — where the character sits
    const seomuDeskX = (rm: number) => 10 + 2*colSpan2 + (colSpan2-deskW2)/2 + deskW2/2
    const seomuDeskY = (rm: number) => rm*(roomH+GAP) + 28 + 1*rowH3 + rowH3*0.55 - 4

    // Source room positions
    const srcRy = d.fromRoom * (roomH + GAP)
    const srcDeskX = d.fromRoom < 4 ? seomuDeskX(d.fromRoom) : cx + corrW*0.5
    const srcDeskY = d.fromRoom < 4 ? seomuDeskY(d.fromRoom) : CEO_OFFSET + ceoH*0.45
    const srcTrayX = d.fromRoom < 4 ? roomW - 11 : cx + corrW*0.5
    const srcTrayY = d.fromRoom < 4 ? srcRy + Math.floor(roomH*0.6) - 3 : CEO_OFFSET + ceoH - 8
    const srcDoorX = d.fromRoom < 4 ? roomW + GAP/2 : cx + corrW*0.4 + 12
    const srcDoorY = d.fromRoom < 4 ? srcRy + roomH*0.6 + 11 : CEO_OFFSET + ceoH

    // Destination room positions
    let dstDoorX: number, dstDoorY: number, dstTrayX: number, dstTrayY: number, dstDeskX: number, dstDeskY: number
    if (d.toRoom === 4) {
      dstDoorX = cx + corrW*0.4 + 12
      dstDoorY = CEO_OFFSET + ceoH
      dstTrayX = cx + corrW*0.5
      dstTrayY = CEO_OFFSET + ceoH - 8
      dstDeskX = cx + corrW*0.5
      dstDeskY = CEO_OFFSET + ceoH*0.45
    } else {
      const dstRy = d.toRoom * (roomH + GAP)
      dstDoorX = roomW + GAP/2
      dstDoorY = dstRy + roomH*0.6 + 11
      dstTrayX = roomW - 11
      dstTrayY = dstRy + Math.floor(roomH*0.6) - 3
      dstDeskX = seomuDeskX(d.toRoom)
      dstDeskY = seomuDeskY(d.toRoom)
    }

    // Corridor Y bounds — NEVER walk above corrTopY (would go through CEO room)
    const corrEnterY = Math.max(corrTopY + 6, srcDoorY)
    const corrExitY  = Math.max(corrTopY + 6, dstDoorY)

    // Endpoints: delivery starts at desk, return ends at desk
    const startX = d.isReturn ? srcTrayX : srcDeskX
    const startY = d.isReturn ? srcTrayY : srcDeskY
    const endX   = d.isReturn ? dstDeskX : dstTrayX
    const endY   = d.isReturn ? dstDeskY : dstTrayY

    // Adjacent rooms (diff === 1) use internal door (short path)
    // Non-adjacent rooms go through corridor (long path)
    const isAdjacent = !d.isReturn
      && d.fromRoom < 4 && d.toRoom < 4
      && Math.abs(d.fromRoom - d.toRoom) === 1

    let waypoints: number[][]

    if (isAdjacent) {
      // Short path: desk → room bottom wall center → next room top wall center → tray
      const wallX = roomW * 0.5
      const srcBottom = d.fromRoom * (roomH + GAP) + roomH
      const dstTop = d.toRoom * (roomH + GAP)
      waypoints = [
        [startX, startY],
        [wallX, srcBottom - 5],    // walk to internal door
        [wallX, dstTop + 10],      // step through door
        [endX, endY],
      ]
    } else if (d.isReturn && Math.abs(d.fromRoom - d.toRoom) === 1 && d.fromRoom < 4 && d.toRoom < 4) {
      // Return trip for adjacent rooms
      const wallX = roomW * 0.5
      const srcBottom = Math.min(d.fromRoom, d.toRoom) * (roomH + GAP) + roomH
      const dstTop = Math.max(d.fromRoom, d.toRoom) * (roomH + GAP)
      waypoints = [
        [startX, startY],
        [wallX, d.fromRoom < d.toRoom ? srcBottom + 5 : dstTop + 10],
        [wallX, d.fromRoom < d.toRoom ? dstTop + 10 : srcBottom - 5],
        [endX, endY],
      ]
    } else {
      // Original long path through corridor
      waypoints = [
        [startX, startY],
        [srcTrayX, srcTrayY],
        [srcDoorX, srcDoorY],
        [corrX, corrEnterY],
        [corrX, corrExitY],
        [dstDoorX, dstDoorY],
        [dstTrayX, dstTrayY],
        [endX, endY],
      ]
    }

    // Compute segment distances
    const segDist: number[] = []
    for (let i = 0; i < waypoints.length - 1; i++) {
      segDist.push(Math.hypot(waypoints[i+1][0]-waypoints[i][0], waypoints[i+1][1]-waypoints[i][1]))
    }
    const totalWalkDist = segDist.reduce((s,d2) => s+d2, 0) || 1

    // Stand time: 3% at start, 3% at end
    const STAND = 0.03
    const walkRange = 1 - STAND*2

    // Compute phase boundaries proportional to distance (constant speed!)
    const phaseBounds = [STAND]  // first walk starts after standing
    let cumDist = 0
    for (let i = 0; i < segDist.length; i++) {
      cumDist += segDist[i]
      phaseBounds.push(STAND + walkRange * (cumDist / totalWalkDist))
    }

    // Interpolate position
    let x: number, y: number
    if (t < STAND) {
      // Standing at start
      x = startX; y = startY
    } else if (t >= 1 - STAND) {
      // Standing at end
      x = endX; y = endY
    } else {
      // Find which segment we're in
      let seg = 0
      for (let i = 0; i < phaseBounds.length - 1; i++) {
        if (t >= phaseBounds[i] && t < phaseBounds[i+1]) { seg = i; break }
      }
      const segStart = phaseBounds[seg]
      const segEnd = phaseBounds[seg+1] ?? 1
      const p = segEnd > segStart ? (t - segStart) / (segEnd - segStart) : 0
      x = waypoints[seg][0] + (waypoints[seg+1][0] - waypoints[seg][0]) * p
      y = waypoints[seg][1] + (waypoints[seg+1][1] - waypoints[seg][1]) * p
    }

    // Walking animation
    const bob = Math.sin(tick * 0.25) * 1.5
    const dy = y + bob

    // Facing direction: going out (right) or coming back (left)
    const goingOut = t < 0.50
    const movingRight = d.isReturn ? !goingOut : goingOut

    // Character color: for delivery = source team color, for return = destination team (= original source)
    const teamColors = [c.green, c.cyan, c.purple, c.gold]
    const origTeam = d.isReturn ? d.toRoom : d.fromRoom  // original source team
    const bodyColor = teamColors[origTeam] ?? c.gold

    // Shadow
    ctx.fillStyle = c.shadow; ctx.beginPath(); ctx.ellipse(x, dy+3, 7, 2, 0, 0, Math.PI*2); ctx.fill()
    // Body (team color)
    ctx.fillStyle = bodyColor+'cc'; ctx.fillRect(x-4, dy-14, 8, 10)
    // Head
    ctx.fillStyle = c.charHead; ctx.beginPath(); ctx.arc(x, dy-18, 4, 0, Math.PI*2); ctx.fill()
    // Hat/cap in team color
    ctx.fillStyle = bodyColor; ctx.fillRect(x-5, dy-22, 10, 5)
    // Eyes — face direction
    ctx.fillStyle = c.charEye
    if (movingRight) {
      ctx.fillRect(x+1, dy-19, 1.5, 1.5); ctx.fillRect(x+2.5, dy-19, 1.5, 1.5)
    } else {
      ctx.fillRect(x-4, dy-19, 1.5, 1.5); ctx.fillRect(x-2.5, dy-19, 1.5, 1.5)
    }

    if (!d.isReturn) {
      // Carrying document (only on delivery, not return)
      const docSide = movingRight ? 1 : -1
      const docX2 = x + docSide * 5 - 4
      ctx.fillStyle = c.txt; ctx.fillRect(docX2, dy-17, 8, 10)
      ctx.strokeStyle = c.border; ctx.lineWidth = 0.5; ctx.strokeRect(docX2, dy-17, 8, 10)
      ctx.fillStyle = c.border; ctx.fillRect(docX2+1,dy-16,6,1); ctx.fillRect(docX2+1,dy-14,6,1)
      // Label
      ctx.font = 'bold 7px IBM Plex Mono, monospace'; ctx.fillStyle = bodyColor; ctx.textAlign = 'center'
      ctx.fillText(d.label, x, dy-28)
    }
  })

  // (panels removed — now in React sidebar)

  // ── Particles ──
  particles.forEach(p => {
    ctx.globalAlpha = p.life/p.maxLife
    ctx.font = 'bold 9px IBM Plex Mono, monospace'; ctx.fillStyle = p.color; ctx.textAlign = 'center'
    ctx.fillText(p.symbol, p.x, p.y)
  })
  ctx.globalAlpha = 1

  // ── Clicked character speech bubble (collection + analysis) ──
  if (clickedCharId) {
    // 분석팀 캐릭터 말풍선 (지표 결과)
    const aCh = chars.find(c2 => c2.id === clickedCharId && c2.team === 'analysis')
    if (aCh && indResults) {
      const roomW2 = Math.floor(W * 0.38)
      const roomH2 = Math.floor((H - 3 * 4) / 4)
      const colsA = 3, colSpanA = (roomW2 - 20) / colsA, deskW2A = colSpanA - 8
      const rowH3A = Math.floor((roomH2 - 30) / 2)
      const deskXA = 10 + aCh.x * colSpanA + (colSpanA - deskW2A) / 2
      const deskYA = 1 * (roomH2 + 4) + 28 + aCh.y * rowH3A + rowH3A * 0.55
      const charXA = deskXA + deskW2A / 2
      const charYA = deskYA - 4

      const lines: string[] = []
      if (aCh.id === 'a1') { // EDA
        lines.push('[ EDA - 이동평균 ]')
        for (const coin of ['BTC', 'ETH', 'SOL', 'HYPE']) {
          const d = indResults[coin]
          if (d?.sma) lines.push(`${coin} SMA7=${d.sma.sma_7?.toFixed(0) ?? '—'}`)
        }
      } else if (aCh.id === 'a2') { // 피처
        lines.push('[ 피처 - RSI/MACD ]')
        for (const coin of ['BTC', 'ETH', 'SOL', 'HYPE']) {
          const d = indResults[coin]
          if (d) {
            const rsiVal = d.rsi_14?.toFixed(1) ?? '—'
            const macdDir = d.macd?.histogram > 0 ? '▲' : '▼'
            lines.push(`${coin} RSI=${rsiVal} MACD${macdDir}`)
          }
        }
      } else if (aCh.id === 'a3') { // 통계
        lines.push('[ 통계 - Bollinger/ATR ]')
        for (const coin of ['BTC', 'ETH', 'SOL', 'HYPE']) {
          const d = indResults[coin]
          if (d) lines.push(`${coin} BB=${d.bollinger_bands?.bandwidth?.toFixed(2) ?? '—'}% ATR=${d.atr_14?.toFixed(1) ?? '—'}`)
        }
      } else if (aCh.id === 'a4') { // 감성NLP
        lines.push('[ 감성NLP - OBV ]')
        for (const coin of ['BTC', 'ETH', 'SOL', 'HYPE']) {
          const d = indResults[coin]
          if (d?.obv) lines.push(`${coin} OBV ${d.obv.obv_trend ?? '—'}`)
        }
      } else if (aCh.id === 'a5') { // 섹터
        lines.push('[ 변동성 ]')
        for (const coin of ['BTC', 'ETH', 'SOL', 'HYPE']) {
          const d = indResults[coin]
          if (d) lines.push(`${coin} vol=${d.realized_volatility?.toFixed(2) ?? '—'}%`)
        }
      }

      if (lines.length > 0) {
        const bubbleW = 170, lineH = 13
        const bubbleH = lines.length * lineH + 10
        let bx = charXA - bubbleW / 2
        let by = charYA - bubbleH - 20
        if (bx < 4) bx = 4
        if (bx + bubbleW > W - 4) bx = W - bubbleW - 4
        if (by < 4) by = charYA + 30

        ctx.fillStyle = 'rgba(0,0,0,0.4)'
        roundRect(ctx, bx + 2, by + 2, bubbleW, bubbleH, 6); ctx.fill()
        ctx.fillStyle = c.panel + 'f0'
        roundRect(ctx, bx, by, bubbleW, bubbleH, 6); ctx.fill()
        ctx.strokeStyle = c.cyan + 'aa'; ctx.lineWidth = 1
        roundRect(ctx, bx, by, bubbleW, bubbleH, 6); ctx.stroke()

        const arrowX = Math.max(bx + 10, Math.min(charXA, bx + bubbleW - 10))
        if (by < charYA) {
          ctx.fillStyle = c.panel + 'f0'
          ctx.beginPath(); ctx.moveTo(arrowX - 5, by + bubbleH); ctx.lineTo(arrowX, by + bubbleH + 6); ctx.lineTo(arrowX + 5, by + bubbleH); ctx.fill()
        }

        ctx.font = 'bold 9px IBM Plex Mono, monospace'
        ctx.textAlign = 'left'
        lines.forEach((line, li) => {
          const ly = by + 12 + li * lineH
          if (li === 0) ctx.fillStyle = c.cyan
          else if (line.includes('▲')) ctx.fillStyle = c.green
          else if (line.includes('▼')) ctx.fillStyle = c.red
          else ctx.fillStyle = c.txtSec
          ctx.fillText(line, bx + 8, ly)
        })
      }
    }
  }

  if (clickedCharId && cData) {
    const ch = chars.find(c2 => c2.id === clickedCharId && c2.team === 'collection')
    if (ch) {
      const roomW2 = Math.floor(W * 0.38)
      const roomH2 = Math.floor((H - 3 * 4) / 4)
      const cols = 3, colSpan = (roomW2 - 20) / cols, deskW2 = colSpan - 8
      const rowH3 = Math.floor((roomH2 - 30) / 2)
      const deskX = 10 + ch.x * colSpan + (colSpan - deskW2) / 2
      const deskY = 0 + 28 + ch.y * rowH3 + rowH3 * 0.55
      const charX = deskX + deskW2 / 2
      const charY = deskY - 4

      // Build bubble text lines based on character
      const lines: string[] = []
      const p = cData.prices
      const s = cData.sentiment

      if (ch.id === 'c1') { // 주가수집 #1
        lines.push('[ BTC / ETH ]')
        if (p.BTC) lines.push(`BTC $${p.BTC.price.toLocaleString()} ${p.BTC.change}`)
        if (p.ETH) lines.push(`ETH $${p.ETH.price.toLocaleString()} ${p.ETH.change}`)
        lines.push(`15m봉 실시간 수집중`)
      } else if (ch.id === 'c2') { // 주가수집 #2
        lines.push('[ SOL / HYPE ]')
        if (p.SOL) lines.push(`SOL $${p.SOL.price.toFixed(2)} ${p.SOL.change}`)
        if (p.HYPE) lines.push(`HYPE $${p.HYPE.price.toFixed(2)} ${p.HYPE.change}`)
        lines.push(`15m봉 실시간 수집중`)
      } else if (ch.id === 'c3') { // 주가수집 #3
        lines.push('[ 전체 현황 ]')
        for (const coin of ['BTC','ETH','SOL','HYPE']) {
          if (p[coin]) lines.push(`${coin} $${p[coin].price >= 1000 ? p[coin].price.toLocaleString() : p[coin].price.toFixed(2)} ${p[coin].change}`)
        }
      } else if (ch.id === 'c4') { // 뉴스수집
        lines.push('[ 뉴스 감성분석 ]')
        for (const coin of ['BTC','ETH','SOL','HYPE']) {
          if (s[coin]) {
            const sc = s[coin].score
            const icon = sc >= 0.05 ? '▲' : sc <= -0.05 ? '▼' : '—'
            lines.push(`${coin} ${icon}${sc.toFixed(2)} (${s[coin].count}건)`)
          }
        }
      } else if (ch.id === 'c5') { // 공시수집
        lines.push('[ RSS 소스 현황 ]')
        lines.push(`CoinDesk: ${cData.sources.coindesk}건`)
        lines.push(`CoinTelegraph: ${cData.sources.cointelegraph}건`)
        lines.push(`6시간 주기 자동수집`)
      } else if (ch.id === 'c6') { // 서무
        lines.push('[ 시스템 상태 ]')
        lines.push(`WS: ${cData.wsConnected ? '● 연결됨' : '○ 끊김'}`)
        lines.push(`Supabase: ${cData.wsConnected ? '● 정상' : '○ 확인필요'}`)
        lines.push(`수집 파이프라인 가동중`)
      }

      if (lines.length > 0) {
        const bubbleW = 160, lineH = 13
        const bubbleH = lines.length * lineH + 10
        let bx = charX - bubbleW / 2
        let by = charY - bubbleH - 20

        // Clamp inside canvas
        if (bx < 4) bx = 4
        if (bx + bubbleW > W - 4) bx = W - bubbleW - 4
        if (by < 4) by = charY + 30 // flip below if too high

        // Shadow
        ctx.fillStyle = 'rgba(0,0,0,0.4)'
        roundRect(ctx, bx + 2, by + 2, bubbleW, bubbleH, 6); ctx.fill()

        // Background
        ctx.fillStyle = c.panel + 'f0'
        roundRect(ctx, bx, by, bubbleW, bubbleH, 6); ctx.fill()
        ctx.strokeStyle = c.cyan + 'aa'; ctx.lineWidth = 1
        roundRect(ctx, bx, by, bubbleW, bubbleH, 6); ctx.stroke()

        // Arrow pointing to character
        const arrowX = Math.max(bx + 10, Math.min(charX, bx + bubbleW - 10))
        if (by < charY) { // bubble above
          ctx.fillStyle = c.panel + 'f0'
          ctx.beginPath(); ctx.moveTo(arrowX - 5, by + bubbleH); ctx.lineTo(arrowX, by + bubbleH + 6); ctx.lineTo(arrowX + 5, by + bubbleH); ctx.fill()
        }

        // Text
        ctx.font = 'bold 9px IBM Plex Mono, monospace'
        ctx.textAlign = 'left'
        lines.forEach((line, li) => {
          const ly = by + 12 + li * lineH
          if (li === 0) {
            ctx.fillStyle = c.cyan
          } else if (line.includes('▲') || line.includes('+')) {
            ctx.fillStyle = c.green
          } else if (line.includes('▼') || line.includes('-')) {
            ctx.fillStyle = c.red
          } else {
            ctx.fillStyle = c.txtSec
          }
          ctx.fillText(line, bx + 8, ly)
        })
      }
    }
  }
}

// ── Office Canvas ──────────────────────────────────────────────────────────

// ── Collection team live data for speech bubbles ──
interface CollectorBubbleData {
  prices: Record<string, { price: number; change: string }> // BTC, ETH, SOL, HYPE
  sentiment: Record<string, { score: number; label: string; count: number }>
  sources: { coindesk: number; cointelegraph: number }
  wsConnected: boolean
  nextAnalysis: string
}

function useCollectorData(): CollectorBubbleData {
  const [data, setData] = useState<CollectorBubbleData>({
    prices: {}, sentiment: {}, sources: { coindesk: 0, cointelegraph: 0 },
    wsConnected: false, nextAnalysis: '',
  })

  useEffect(() => {
    let dead = false
    async function load() {
      try {
        // Prices from Hyperliquid
        const now = Date.now()
        const coins = ['BTC', 'ETH', 'SOL', 'HYPE']
        const prices: Record<string, { price: number; change: string }> = {}
        await Promise.all(coins.map(async coin => {
          const res = await fetch('https://api.hyperliquid.xyz/info', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'candleSnapshot', req: { coin, interval: '1d', startTime: now - 86400000 * 3, endTime: now } }),
          })
          const arr = await res.json()
          if (Array.isArray(arr) && arr.length >= 2) {
            const prev = parseFloat(arr[arr.length - 2].c)
            const curr = parseFloat(arr[arr.length - 1].c)
            const pct = ((curr - prev) / prev) * 100
            prices[coin] = { price: curr, change: `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%` }
          }
        }))

        // Sentiment from backend
        const sentiment: Record<string, { score: number; label: string; count: number }> = {}
        let cd = 0, ct = 0
        try {
          const sRes = await fetch('http://localhost:8090/api/sentiment/summary/all')
          const sData = await sRes.json()
          for (const s of (sData.summaries ?? [])) {
            sentiment[s.coin] = { score: s.avg_sentiment, label: s.sentiment_label, count: s.article_count }
          }
        } catch {}
        // Source counts from individual coin data
        try {
          const btcRes = await fetch('http://localhost:8090/api/sentiment/BTC?limit=50')
          const btcData = await btcRes.json()
          for (const a of (btcData.articles ?? [])) {
            if (a.source === 'CoinDesk') cd++
            if (a.source === 'CoinTelegraph') ct++
          }
        } catch {}

        // WS health check
        let wsOk = false
        try {
          const hRes = await fetch('http://localhost:8090/health')
          wsOk = hRes.ok
        } catch {}

        if (!dead) setData({ prices, sentiment, sources: { coindesk: cd, cointelegraph: ct }, wsConnected: wsOk, nextAnalysis: '' })
      } catch {}
    }
    load()
    const iv = window.setInterval(load, 30_000)
    return () => { dead = true; clearInterval(iv) }
  }, [])

  return data
}

function OfficeCanvas() {
  const { c } = useTheme()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef    = useRef<number>(0)
  const tickRef   = useRef(0)
  const colorsRef = useRef<Colors>(c)
  const [chars]   = useState<Character[]>(INITIAL_CHARS)
  const partRef   = useRef<Particle[]>([])
  const delRef    = useRef<Delivery[]>([])
  const delId = useRef(0), partId = useRef(0)

  // Clicked character for speech bubble
  const [clickedChar, setClickedChar] = useState<string | null>(null)
  const clickedCharRef = useRef<string | null>(null)
  const clickTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const collectorData = useCollectorData()
  const collectorDataRef = useRef(collectorData)
  collectorDataRef.current = collectorData
  useEffect(() => { clickedCharRef.current = clickedChar }, [clickedChar])

  // Keep colorsRef in sync without restarting the RAF loop
  useEffect(() => { colorsRef.current = c }, [c])

  // Canvas click → find character at position
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const W = canvas.offsetWidth, H = canvas.offsetHeight
    const roomW = Math.floor(W * 0.38)
    const GAP = 4
    const roomH = Math.floor((H - 3 * GAP) / 4)
    const teamKeys = ['collection', 'analysis', 'ml', 'report'] as const

    // Check collection team (0) + analysis team (1)
    let found: string | null = null
    const cols = 3
    const colSpan = (roomW - 20) / cols
    const deskW = colSpan - 8

    for (const teamIdx of [0, 1]) {
      const ry = teamIdx * (roomH + GAP)
      const rowH2 = Math.floor((roomH - 30) / 2)
      const teamChars = chars.filter(ch => ch.team === teamKeys[teamIdx])

      for (const ch of teamChars) {
        const deskX = 10 + ch.x * colSpan + (colSpan - deskW) / 2
        const deskY = ry + 28 + ch.y * rowH2 + rowH2 * 0.55
        const charX = deskX + deskW / 2
        const charY = deskY - 4
        if (Math.abs(mx - charX) < 25 && Math.abs(my - charY) < 25) {
          found = ch.id
          break
        }
      }
      if (found) break
    }

    if (found) {
      // 수집팀 캐릭터 클릭 → 말풍선 + 서무면 프롬프트도
      if (found === 'c6' && promptStage === 'ask') {
        setShowPrompt(true)
        setClickedChar(null)
        return
      }
      setClickedChar(prev => prev === found ? null : found)
      clearTimeout(clickTimerRef.current)
      clickTimerRef.current = setTimeout(() => setClickedChar(null), 8000)
    } else {
      // 빈 공간 클릭 시에도 프롬프트 체크: 수집팀 영역 클릭
      const roomW2 = Math.floor(W * 0.38)
      const roomH2 = Math.floor((H - 3 * GAP) / 4)
      if (mx < roomW2 && my < roomH2 && promptStage === 'ask') {
        setShowPrompt(true)
        return
      }
      setClickedChar(null)
    }
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const spawnDelivery = (fromIdx:number, toIdx:number, label:string) => {
      const W=canvas.offsetWidth, H=canvas.offsetHeight
      const roomW2=Math.floor(W*0.38), GAP2=4, roomH2=Math.floor((H-3*GAP2)/4)
      const corrW2 = W - roomW2 - GAP2
      const ceoH2 = Math.floor(roomH2 * 0.7)
      const ceoOffset2 = 16
      // Approximate total path distance (pixels) for constant speed
      const exitDist = Math.sqrt((roomW2*0.4)**2 + (roomH2*0.15)**2)
      const toCorrDist = corrW2 * 0.5
      const srcDoorY = fromIdx*(roomH2+GAP2) + roomH2*0.6 + 11
      const dstDoorY = toIdx===4 ? ceoOffset2+ceoH2 : toIdx*(roomH2+GAP2) + roomH2*0.6 + 11
      const corrDist = Math.abs(dstDoorY - srcDoorY)
      const totalDist = exitDist + toCorrDist + corrDist + toCorrDist + exitDist
      delRef.current.push({ id:++delId.current, fromRoom:fromIdx, toRoom:toIdx, progress:0, label, totalDist, isReturn:false })
    }
    const spawnParticle = (ch:Character) => {
      const si = STATE_INFO[ch.state]; if (!si?.symbol) return
      const W=canvas.offsetWidth, H=canvas.offsetHeight
      const roomW=Math.floor(W*0.38), GAP=4, roomH=Math.floor((H-3*GAP)/4)
      const teamIdx=['collection','analysis','ml','report'].indexOf(ch.team)
      const cols=3, colSpan=(roomW-20)/cols, deskW=colSpan-8
      const px = 10+ch.x*colSpan+(colSpan-deskW)/2+deskW/2
      const py = teamIdx*(roomH+GAP)+28+ch.y*Math.floor((roomH-30)/2)+Math.floor((roomH-30)/2)*0.45
      const sc = colorsRef.current[si.colorKey] as string
      partRef.current.push({ id:++partId.current, x:px, y:py, vx:(Math.random()-0.5)*1.5, vy:-1.2-Math.random(), life:55, maxLife:55, symbol:si.symbol, color:sc })
    }

    // Pipeline: sequential delivery stages
    const pipeline = { stage:0, stageStart:0 }
    const STAGES: {from:number;to:number;label:string;wait:number}[] = [
      { from:0, to:1, label:'분석 데이터',  wait:300 },  // 수집→분석
      { from:1, to:2, label:'피처 세트',    wait:350 },  // 분석→ML
      { from:2, to:3, label:'모델 결과',    wait:400 },  // ML→보고서
      { from:3, to:4, label:'최종 보고서',  wait:300 },  // 보고서→CEO
    ]

    const TEAM_KEYS = ['collection','analysis','ml','report'] as const

    const loop = () => {
      const tick = ++tickRef.current
      canvas.width  = canvas.offsetWidth
      canvas.height = canvas.offsetHeight

      // 자동 배달 없음 — 프롬프트 "보내기"로만 배달 시작
      if (tick%12===0) { const a=chars.filter(c=>c.state!=='idle'&&c.state!=='delivering'); if(a.length) spawnParticle(a[Math.floor(Math.random()*a.length)]) }
      partRef.current = partRef.current.map(p=>({...p,x:p.x+p.vx,y:p.y+p.vy,life:p.life-1})).filter(p=>p.life>0)
      const WALK_SPEED = 0.7  // pixels per tick — constant walking speed
      const returners: Delivery[] = []
      delRef.current = delRef.current.map(d => {
        const np = d.progress + WALK_SPEED / d.totalDist
        if (np >= 1 && !d.isReturn) {
          // Delivery done → spawn return trip (walk back, no document)
          returners.push({ id:++delId.current, fromRoom:d.toRoom, toRoom:d.fromRoom, progress:0, label:'', totalDist:d.totalDist, isReturn:true })
        }
        if (np >= 1 && d.isReturn) {
          // Return done → 서무 돌아와서 자리에 앉음
          const origTeam = TEAM_KEYS[d.toRoom]  // toRoom of return = original source
          if (origTeam) {
            const seomu = chars.find(ch => ch.team === origTeam && ch.role === 'delivery')
            if (seomu) seomu.state = 'idle'
          }
        }
        return { ...d, progress:np }
      }).filter(d => d.progress < 1)
      delRef.current.push(...returners)
      drawOffice(ctx, canvas.width, canvas.height, chars, partRef.current, delRef.current, tick, colorsRef.current, clickedCharRef.current, collectorDataRef.current, indicatorResultsRef.current)
      rafRef.current = requestAnimationFrame(loop)
    }
    rafRef.current = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(rafRef.current)
  }, [chars])

  // ── 수집 완료 프롬프트 ──
  const [showPrompt, setShowPrompt] = useState(false)
  const [promptStage, setPromptStage] = useState<'ask' | 'sending' | 'done' | 'analyzing' | 'analyzed'>('ask')
  const [indicatorResults, setIndicatorResults] = useState<Record<string, any> | null>(null)
  const indicatorResultsRef = useRef<Record<string, any> | null>(null)
  useEffect(() => { indicatorResultsRef.current = indicatorResults }, [indicatorResults])

  // 배달 완료 감지용 ref
  const manualDeliveryIdRef = useRef<number>(0)

  const handleSendToAnalysis = () => {
    setPromptStage('sending')
    const canvas = canvasRef.current
    if (canvas) {
      const W = canvas.offsetWidth, H = canvas.offsetHeight
      const roomW = Math.floor(W * 0.38), GAP = 4, roomH = Math.floor((H - 3 * GAP) / 4)
      const corrW = W - roomW - GAP
      const exitDist = Math.sqrt((roomW * 0.4) ** 2 + (roomH * 0.15) ** 2)
      const toCorrDist = corrW * 0.5
      const srcDoorY = 0 * (roomH + GAP) + roomH * 0.6 + 11
      const dstDoorY = 1 * (roomH + GAP) + roomH * 0.6 + 11
      const corrDist = Math.abs(dstDoorY - srcDoorY)
      const totalDist = exitDist + toCorrDist + corrDist + toCorrDist + exitDist
      const newId = ++delId.current
      manualDeliveryIdRef.current = newId
      delRef.current.push({ id: newId, fromRoom: 0, toRoom: 1, progress: 0, label: '수집 데이터', totalDist, isReturn: false })
      const seomu = chars.find(ch => ch.id === 'c6')
      if (seomu) seomu.state = 'delivering'
    }
    // 실제 배달 완료를 폴링으로 감지 (배달 progress >= 1일 때)
  }

  // 배달 완료 감지 → 분석팀 기술지표 계산 트리거
  useEffect(() => {
    if (promptStage !== 'sending') return
    const check = window.setInterval(() => {
      const id = manualDeliveryIdRef.current
      if (id === 0) return
      const still = delRef.current.find(d => d.id === id)
      if (!still) {
        // 배달 도착 → 분석팀 작업 시작
        manualDeliveryIdRef.current = 0
        setPromptStage('analyzing')

        // 분석팀 캐릭터 상태 변경
        const analysisChars = chars.filter(ch => ch.team === 'analysis')
        const featureChar = analysisChars.find(ch => ch.id === 'a2') // 피처
        const edaChar = analysisChars.find(ch => ch.id === 'a1') // EDA
        const statChar = analysisChars.find(ch => ch.id === 'a3') // 통계
        if (featureChar) { featureChar.state = 'feature'; featureChar.progress = 0.2; featureChar.statusText = 'RSI/MACD' }
        if (edaChar) { edaChar.state = 'eda'; edaChar.progress = 0.3; edaChar.statusText = 'SMA/EMA' }
        if (statChar) { statChar.state = 'analyzing'; statChar.progress = 0.1; statChar.statusText = 'Bollinger' }

        // API 호출: 기술지표 계산
        fetch('http://localhost:8090/api/indicators/all/1h')
          .then(r => r.json())
          .then(data => {
            setIndicatorResults(data.coins ?? data)

            // 계산 완료 → 캐릭터 상태 업데이트
            if (featureChar) { featureChar.progress = 1.0; featureChar.statusText = 'RSI 완료' }
            if (edaChar) { edaChar.progress = 1.0; edaChar.statusText = 'SMA 완료' }
            if (statChar) { statChar.progress = 1.0; statChar.statusText = 'BB 완료' }

            setPromptStage('analyzed')
            setTimeout(() => {
              setShowPrompt(false)
              setPromptStage('ask')
              // 분석팀 idle 복귀
              analysisChars.forEach(ch => {
                if (ch.role !== 'delivery') { ch.state = 'idle'; ch.progress = 1.0; ch.statusText = '대기' }
              })
            }, 8000)
          })
          .catch(() => {
            setPromptStage('done')
            setTimeout(() => { setShowPrompt(false); setPromptStage('ask') }, 3000)
          })

        clearInterval(check)
      }
    }, 100)
    return () => clearInterval(check)
  }, [promptStage])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <canvas ref={canvasRef} onClick={handleCanvasClick} style={{ width: '100%', height: '100%', display: 'block', cursor: 'pointer' }} />

      {/* 수집 완료 프롬프트 */}
      {showPrompt && (
        <div style={{
          position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)',
          background: c.panel + 'f5', border: `1px solid ${c.cyan}88`,
          borderRadius: 8, padding: '12px 20px',
          display: 'flex', alignItems: 'center', gap: 12,
          fontFamily: MONO, fontSize: 11,
          boxShadow: `0 4px 20px rgba(0,0,0,0.4)`,
          zIndex: 10,
        }}>
          {promptStage === 'ask' && (<>
            <span style={{ color: c.green, fontSize: 14 }}>●</span>
            <span style={{ color: c.txt }}>
              수집이 완료됐습니다. 분석팀에게 보낼까요?
            </span>
            <button
              onClick={handleSendToAnalysis}
              style={{
                padding: '4px 14px', fontFamily: MONO, fontSize: 10, fontWeight: 700,
                background: c.cyan + '22', color: c.cyan,
                border: `1px solid ${c.cyan}66`, borderRadius: 4, cursor: 'pointer',
              }}
            >
              보내기
            </button>
            <button
              onClick={() => setShowPrompt(false)}
              style={{
                padding: '4px 10px', fontFamily: MONO, fontSize: 10,
                background: 'transparent', color: c.txtMut,
                border: `1px solid ${c.border}`, borderRadius: 4, cursor: 'pointer',
              }}
            >
              닫기
            </button>
          </>)}
          {promptStage === 'sending' && (<>
            <span style={{ color: c.gold, fontSize: 14, animation: 'pulse-dot 1s infinite' }}>●</span>
            <span style={{ color: c.gold }}>서무가 분석팀에게 전달 중...</span>
          </>)}
          {promptStage === 'done' && (<>
            <span style={{ color: c.green, fontSize: 14 }}>✓</span>
            <span style={{ color: c.green }}>분석팀에게 전달 완료!</span>
          </>)}
          {promptStage === 'analyzing' && (<>
            <span style={{ color: c.cyan, fontSize: 14, animation: 'pulse-dot 1s infinite' }}>◈</span>
            <span style={{ color: c.cyan }}>분석팀 기술지표 연산 중... (RSI, MACD, SMA, Bollinger)</span>
          </>)}
          {promptStage === 'analyzed' && indicatorResults && (<>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: c.green, fontSize: 14 }}>✓</span>
                <span style={{ color: c.green, fontWeight: 700 }}>분석 완료!</span>
              </div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {Object.entries(indicatorResults).map(([coin, data]: [string, any]) => (
                  <div key={coin} style={{
                    padding: '4px 8px', borderRadius: 4,
                    border: `1px solid ${c.border}`, background: c.panel,
                    fontSize: 9, lineHeight: '14px',
                  }}>
                    <div style={{ color: c.cyan, fontWeight: 700 }}>{coin}</div>
                    <div style={{ color: data.rsi_14 < 30 ? c.green : data.rsi_14 > 70 ? c.red : c.txtSec }}>
                      RSI {data.rsi_14 ?? '—'}
                    </div>
                    <div style={{ color: data.macd?.histogram > 0 ? c.green : c.red }}>
                      MACD {data.macd?.histogram > 0 ? '▲' : '▼'}{Math.abs(data.macd?.histogram ?? 0).toFixed(2)}
                    </div>
                    <div style={{ color: c.txtMut }}>
                      BB {data.bollinger_bands?.bandwidth?.toFixed(2) ?? '—'}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>)}
        </div>
      )}
    </div>
  )
}

// ── Shared primitives ──────────────────────────────────────────────────────

const MONO = 'IBM Plex Mono,monospace'
const KR   = 'Noto Sans KR,sans-serif'

// ── Left: Agent Status Panel ────────────────────────────────────────────────

function AgentStatusPanel() {
  const { c } = useTheme()
  const teams = [
    { key:'collection', label:'수집팀',  short:'COL', color:c.green,  chars:INITIAL_CHARS.filter(ch=>ch.team==='collection') },
    { key:'analysis',   label:'분석팀',  short:'DSC', color:c.cyan,   chars:INITIAL_CHARS.filter(ch=>ch.team==='analysis')   },
    { key:'ml',         label:'ML팀',   short:'ML',  color:c.purple,  chars:INITIAL_CHARS.filter(ch=>ch.team==='ml')         },
    { key:'report',     label:'보고서팀', short:'RPT', color:c.gold,   chars:INITIAL_CHARS.filter(ch=>ch.team==='report')     },
  ]
  return (
    <div style={{ width:216, flexShrink:0, borderRight:`1px solid ${c.border}`, display:'flex', flexDirection:'column', overflow:'hidden', background:c.panel, transition:'background 0.3s' }}>
      <div style={{ padding:'8px 12px 7px', borderBottom:`1px solid ${c.border}`, flexShrink:0 }}>
        <span style={{ fontFamily:MONO, fontSize:9, letterSpacing:2, color:c.txtMut }}>AGENT STATUS</span>
      </div>

      <div style={{ flex:1, overflowY:'auto' }}>
        {teams.map(team => {
          const active = team.chars.filter(ch => ch.state !== 'idle')
          const avg = team.chars.reduce((s,ch) => s+ch.progress, 0) / team.chars.length
          return (
            <div key={team.key} style={{ borderBottom:`1px solid ${c.border}66` }}>
              {/* Team header row */}
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'6px 12px 4px', background:team.color+'10' }}>
                <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                  <div style={{ width:2.5, height:14, background:team.color, borderRadius:1 }}/>
                  <span style={{ fontFamily:MONO, fontSize:9, fontWeight:700, color:team.color, letterSpacing:1 }}>{team.short}</span>
                  <span style={{ fontFamily:KR, fontSize:11, color:c.txtSec }}>{team.label}</span>
                </div>
                <span style={{ fontFamily:MONO, fontSize:8, color:active.length>0?team.color:c.txtMut }}>
                  {active.length}<span style={{ color:c.txtMut }}>/{team.chars.length}</span>
                </span>
              </div>
              {/* Team progress bar */}
              <div style={{ height:2, background:c.border, margin:'0 12px 5px' }}>
                <div style={{ height:'100%', width:`${avg*100}%`, background:team.color, transition:'width 1s' }}/>
              </div>
              {/* Agent rows */}
              {team.chars.map(ch => {
                const si = STATE_INFO[ch.state] ?? STATE_INFO.idle
                const sc = c[si.colorKey] as string
                return (
                  <div key={ch.id} style={{ display:'flex', alignItems:'center', gap:6, padding:'2px 12px 2px 18px' }}>
                    <div style={{ width:5, height:5, borderRadius:'50%', background:ch.state==='idle'?c.txtMut:sc, flexShrink:0 }}/>
                    <span style={{ fontFamily:KR, fontSize:10, color:c.txtSec, flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{ch.label}</span>
                    <span style={{ fontFamily:MONO, fontSize:8, color:ch.state==='idle'?c.txtMut:sc, flexShrink:0 }}>
                      {ch.state==='idle' ? 'IDLE' : `${Math.round(ch.progress*100)}%`}
                    </span>
                  </div>
                )
              })}
              <div style={{ height:5 }}/>
            </div>
          )
        })}
      </div>

      {/* Pipeline chain */}
      <div style={{ borderTop:`1px solid ${c.border}`, padding:'8px 12px', flexShrink:0 }}>
        <div style={{ fontFamily:MONO, fontSize:8, color:c.txtMut, letterSpacing:1, marginBottom:6 }}>PIPELINE</div>
        {([
          ['수집 → 분석', c.green,  true ],
          ['분석 → ML',   c.cyan,   false],
          ['ML → 보고서', c.purple, false],
        ] as const).map(([label, color, done]) => (
          <div key={label} style={{ display:'flex', alignItems:'center', gap:7, marginBottom:4 }}>
            <div style={{ width:6, height:6, borderRadius:1, background:done?color:c.border, flexShrink:0 }}/>
            <span style={{ fontFamily:MONO, fontSize:8, color:done?color:c.txtMut }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Right: Activity Log ─────────────────────────────────────────────────────

type LogEntry = { time:string; team:string; colorKey:keyof Colors; msg:string }
const MOCK_LOG: LogEntry[] = [
  { time:'09:00:01', team:'COL', colorKey:'green',  msg:'삼성전자 일봉 수집 시작' },
  { time:'09:00:03', team:'COL', colorKey:'green',  msg:'SK하이닉스 수집 시작' },
  { time:'09:00:12', team:'COL', colorKey:'green',  msg:'DART 공시 45건 수집 완료' },
  { time:'09:01:05', team:'COL', colorKey:'green',  msg:'뉴스 NLP 피드 연결됨' },
  { time:'09:02:30', team:'DSC', colorKey:'cyan',   msg:'ADF 정상성 검정 통과 p=0.001' },
  { time:'09:03:14', team:'DSC', colorKey:'cyan',   msg:'RSI_14 피처 생성 완료' },
  { time:'09:04:00', team:'DSC', colorKey:'cyan',   msg:'이상치 23건 클리핑 처리' },
  { time:'09:04:52', team:'DSC', colorKey:'cyan',   msg:'감성분석 TF-IDF 완료' },
  { time:'09:05:22', team:'ML',  colorKey:'purple', msg:'Prophet 완료 MAE=0.031' },
  { time:'09:06:01', team:'ML',  colorKey:'purple', msg:'LSTM Ep 35/50 loss=0.0231' },
  { time:'09:07:45', team:'ML',  colorKey:'purple', msg:'XGBoost Trial 12/30 진행중' },
  { time:'09:08:10', team:'RPT', colorKey:'gold',   msg:'종합 리포트 초안 작성 시작' },
  { time:'09:09:00', team:'RPT', colorKey:'gold',   msg:'투자 메모 작성 완료 ✓' },
]

function ActivityLogPanel() {
  const { c } = useTheme()
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView() }, [])
  return (
    <div style={{ width:196, flexShrink:0, borderLeft:`1px solid ${c.border}`, display:'flex', flexDirection:'column', overflow:'hidden', background:c.panel, transition:'background 0.3s' }}>
      <div style={{ padding:'8px 12px 7px', borderBottom:`1px solid ${c.border}`, display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
        <span style={{ fontFamily:MONO, fontSize:9, letterSpacing:2, color:c.txtMut }}>ACTIVITY</span>
        <span style={{ fontFamily:MONO, fontSize:8, color:c.green }}>● LIVE</span>
      </div>
      <div style={{ flex:1, overflowY:'auto' }}>
        {MOCK_LOG.map((entry,i) => (
          <div key={i} style={{ padding:'4px 10px', borderBottom:`1px solid ${c.border}33` }}>
            <div style={{ display:'flex', alignItems:'center', gap:5, marginBottom:2 }}>
              <span style={{ fontFamily:MONO, fontSize:8, color:c.txtMut }}>{entry.time}</span>
              <span style={{ fontFamily:MONO, fontSize:8, color:c[entry.colorKey] as string, background:(c[entry.colorKey] as string)+'18', padding:'0 4px', borderRadius:2 }}>{entry.team}</span>
            </div>
            <span style={{ fontFamily:KR, fontSize:10, color:c.txtSec, lineHeight:1.4 }}>{entry.msg}</span>
          </div>
        ))}
        <div ref={endRef}/>
      </div>
    </div>
  )
}

// ── Center: Tab Panels ──────────────────────────────────────────────────────

function MarketPanel() {
  const { c } = useTheme()
  const stocks = [
    { name:'삼성전자',     code:'005930', price:'73,400',  chg:'+1.66%', up:true,  cap:'440조' },
    { name:'SK하이닉스',   code:'000660', price:'182,000', chg:'-1.73%', up:false, cap:'132조' },
    { name:'LG에너지솔루션',code:'373220', price:'360,000', chg:'+0.84%', up:true,  cap:'84조'  },
    { name:'삼성바이오',    code:'207940', price:'892,000', chg:'+1.82%', up:true,  cap:'59조'  },
    { name:'현대차',       code:'005380', price:'240,000', chg:'-0.62%', up:false, cap:'51조'  },
    { name:'NAVER',       code:'035420', price:'205,500', chg:'+2.14%', up:true,  cap:'34조'  },
  ]

  // 실제 KRX 뉴스 감성분석 데이터 fetch
  const [newsItems, setNewsItems] = useState<{time:string,tag:string,tagColor:string,title:string,sentiment:'positive'|'negative'|'neutral',sentimentIcon:string,score:number,url:string}[]>([])
  const [krxSummary, setKrxSummary] = useState<Record<string, {avg:number, label:string, count:number}>>({})

  useEffect(() => {
    let dead = false
    async function loadKrxNews() {
      try {
        // 종목별 뉴스 fetch
        const codes = ['005930','000660','035420','035720','005380']
        const names: Record<string,string> = {'005930':'삼성전자','000660':'SK하이닉스','035420':'NAVER','035720':'카카오','005380':'현대차'}
        const results = await Promise.all(
          codes.map(async code => {
            const r = await fetch(`http://localhost:8090/api/krx/sentiment/${code}?limit=5`)
            return { code, data: await r.json() }
          })
        )
        if (dead) return

        const items: typeof newsItems = []
        const summaryMap: typeof krxSummary = {}

        for (const { code, data } of results) {
          const name = names[code] ?? code
          if (data.summary) {
            summaryMap[code] = {
              avg: data.summary.avg_sentiment,
              label: data.summary.sentiment_label,
              count: data.summary.article_count,
            }
          }
          for (const a of (data.articles ?? [])) {
            const score = a.sentiment_score ?? 0
            const label = score >= 0.05 ? 'positive' : score <= -0.05 ? 'negative' : 'neutral'
            const icon = label === 'positive' ? '▲' : label === 'negative' ? '▼' : '—'
            const color = label === 'positive' ? c.green : label === 'negative' ? c.red : c.txtMut
            const pubDate = a.published_at ? new Date(a.published_at) : new Date()
            const timeStr = `${pubDate.getMonth()+1}/${pubDate.getDate()}`
            items.push({ time: timeStr, tag: name, tagColor: color, title: a.title, sentiment: label, sentimentIcon: icon, score, url: a.url ?? '' })
          }
        }

        // 최신순 정렬
        items.sort((a, b) => b.score - a.score) // 감성점수 높은 순
        setNewsItems(items.slice(0, 15))
        setKrxSummary(summaryMap)
      } catch { /* ignore */ }
    }
    loadKrxNews()
    const iv = window.setInterval(loadKrxNews, 5 * 60_000)
    return () => { dead = true; clearInterval(iv) }
  }, [])
  return (
    <div>
      {/* Index summary - compact row */}
      <div style={{ display:'flex', gap:6, marginBottom:10 }}>
        {([
          { label:'KOSPI',  value:'2,612.35', chg:'+0.48%', up:true  },
          { label:'KOSDAQ', value:'856.21',   chg:'-0.12%', up:false },
          { label:'원/달러', value:'1,328.50', chg:'-2.30',  up:false },
        ]).map(d => (
          <div key={d.label} style={{ flex:1, background:c.panel, border:`1px solid ${c.border}`, borderTop:`2px solid ${d.up?c.green:c.red}`, padding:'6px 10px' }}>
            <div style={{ fontFamily:MONO, fontSize:8, color:c.txtMut, letterSpacing:1 }}>{d.label}</div>
            <div style={{ fontFamily:MONO, fontSize:14, fontWeight:700, color:c.txt }}>{d.value}</div>
            <div style={{ fontFamily:MONO, fontSize:10, color:d.up?c.green:c.red }}>{d.chg}</div>
          </div>
        ))}
      </div>

      {/* Stock cards grid - 시총 대장 */}
      <div style={{ fontFamily:MONO, fontSize:8, color:c.txtMut, letterSpacing:2, marginBottom:6 }}>KOSPI 시총 TOP 6</div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:6 }}>
        {stocks.map(s => (
          <div key={s.code} style={{ background:c.panel, border:`1px solid ${c.border}`, borderLeft:`3px solid ${s.up?c.green:c.red}`, overflow:'hidden' }}>
            {/* Stock header */}
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', padding:'6px 8px 4px' }}>
              <div>
                <div style={{ fontFamily:KR, fontSize:11, fontWeight:700, color:c.txt }}>{s.name}</div>
                <div style={{ fontFamily:MONO, fontSize:8, color:c.txtMut }}>{s.code} · {s.cap}</div>
              </div>
              <div style={{ textAlign:'right' }}>
                <div style={{ fontFamily:MONO, fontSize:12, fontWeight:700, color:c.txt }}>{s.price}</div>
                <div style={{ fontFamily:MONO, fontSize:9, fontWeight:700, color:s.up?c.green:c.red }}>{s.chg}</div>
              </div>
            </div>
            {/* Chart */}
            <StockChart symbol={s.code} color={s.up?c.green:c.red} bgColor={c.panel} borderColor={c.border} gridColor={c.floorLine} txtMutColor={c.txtMut} goldColor={c.gold} redColor={c.red} height={70}/>
          </div>
        ))}
      </div>

      {/* Sentiment summary per stock */}
      {Object.keys(krxSummary).length > 0 && (<>
        <div style={{ fontFamily:MONO, fontSize:8, color:c.txtMut, letterSpacing:2, marginTop:10, marginBottom:6 }}>NEWS SENTIMENT (TF-IDF + VADER)</div>
        <div style={{ display:'flex', gap:6, marginBottom:8, flexWrap:'wrap' }}>
          {Object.entries(krxSummary).map(([code, s]) => {
            const name = {'005930':'삼성전자','000660':'SK하이닉스','035420':'NAVER','035720':'카카오','005380':'현대차'}[code] ?? code
            const sc = s.avg
            const color = sc >= 0.05 ? c.green : sc <= -0.05 ? c.red : c.txtMut
            const icon = sc >= 0.05 ? '▲' : sc <= -0.05 ? '▼' : '—'
            return (
              <div key={code} style={{ padding:'4px 8px', border:`1px solid ${c.border}`, borderRadius:4, background:c.panel, fontFamily:MONO, fontSize:9 }}>
                <span style={{ color:c.txtSec, fontWeight:700 }}>{name}</span>
                <span style={{ color, marginLeft:6 }}>{icon}{sc.toFixed(3)}</span>
                <span style={{ color:c.txtMut, marginLeft:4 }}>({s.count}건)</span>
              </div>
            )
          })}
        </div>
      </>)}

      {/* Latest news - 실제 데이터 */}
      <div style={{ fontFamily:MONO, fontSize:8, color:c.txtMut, letterSpacing:2, marginTop:4, marginBottom:6 }}>
        {newsItems.length > 0 ? 'LATEST NEWS (실시간)' : 'LATEST NEWS (로딩중...)'}
      </div>
      <div style={{ display:'flex', flexDirection:'column', gap:2, maxHeight:200, overflowY:'auto' }}>
        {newsItems.map((n, i) => (
          <a key={i} href={n.url} target="_blank" rel="noopener noreferrer" style={{
            display:'flex', alignItems:'center', gap:8,
            padding:'5px 8px', textDecoration:'none',
            background: i%2===0 ? 'transparent' : c.panel+'66',
            borderBottom: `1px solid ${c.border}33`,
          }}>
            <span style={{ fontFamily:MONO, fontSize:8, color:c.txtMut, flexShrink:0 }}>{n.time}</span>
            <span style={{ fontFamily:MONO, fontSize:8, color:n.tagColor, background:n.tagColor+'18', padding:'0 4px', borderRadius:2, flexShrink:0 }}>{n.tag}</span>
            <span style={{ fontFamily:'Noto Sans KR,sans-serif', fontSize:10, color:c.txtSec, flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{n.title}</span>
            <span style={{ fontFamily:MONO, fontSize:9, color:n.sentiment==='positive'?c.green:n.sentiment==='negative'?c.red:c.txtMut, flexShrink:0, minWidth:35, textAlign:'right' }}>
              {n.sentimentIcon}{n.score >= 0 ? '+' : ''}{n.score.toFixed(2)}
            </span>
          </a>
        ))}
      </div>
    </div>
  )
}

// ── Center: Main tabbed panel ───────────────────────────────────────────────

type MainTab = 'market' | 'crypto' | 'office'

function MainPanel() {
  const { c } = useTheme()
  const [tab, setTab] = useState<MainTab>('market')
  const tabs: { key:MainTab; label:string }[] = [
    { key:'market', label:'KRX 주식' },
    { key:'crypto', label:'CRYPTO' },
    { key:'office', label:'OFFICE' },
  ]
  return (
    <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden', background:c.bg, transition:'background 0.3s' }}>
      {/* Tab bar */}
      <div style={{ display:'flex', borderBottom:`1px solid ${c.border}`, background:c.panel, flexShrink:0 }}>
        {tabs.map(t => (
          <button key={t.key} onClick={()=>setTab(t.key)} style={{
            padding:'7px 20px',
            fontFamily:MONO, fontSize:10, letterSpacing:1,
            background:'transparent',
            color:tab===t.key ? c.txt : c.txtMut,
            border:'none', cursor:'pointer',
            borderBottom:tab===t.key ? `2px solid ${t.key==='crypto'?c.cyan:c.blue}` : '2px solid transparent',
            transition:'all 0.15s',
          }}>{t.label.toUpperCase()}</button>
        ))}
      </div>
      {/* Content */}
      <div style={{ flex:1, overflow:tab==='office'?'hidden':'auto', padding:tab==='office'?0:'10px 14px', display:'flex', flexDirection:'column' }}>
        {tab==='market' && <MarketPanel/>}
        {tab==='crypto' && <CryptoChart bgColor={c.panel} panelColor={c.panel} borderColor={c.border} gridColor={c.floorLine} txtColor={c.txt} txtSecColor={c.txtSec} txtMutColor={c.txtMut} greenColor={c.green} redColor={c.red} goldColor={c.gold} blueColor={c.blue} cyanColor={c.cyan}/>}
        {tab==='office' && <OfficeCanvas/>}
      </div>
    </div>
  )
}

// ── Root App ───────────────────────────────────────────────────────────────

export default function App() {
  const [dark, setDark] = useState(true)
  const [clock, setClock] = useState(new Date())
  const [cryptoTicker, setCryptoTicker] = useState<{name:string,chg:string,up:boolean}[]>([])
  const c = dark ? DARK : LIGHT

  useEffect(() => { const t=setInterval(()=>setClock(new Date()),1000); return()=>clearInterval(t) }, [])

  // Fetch crypto 24h changes for ticker
  useEffect(() => {
    let dead = false
    async function loadCrypto() {
      try {
        const coins = ['BTC','ETH','SOL','HYPE']
        const now = Date.now()
        const results = await Promise.all(coins.map(async coin => {
          const res = await fetch('https://api.hyperliquid.xyz/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'candleSnapshot', req: { coin, interval: '1d', startTime: now - 86400000 * 3, endTime: now } }),
          })
          const data = await res.json()
          if (Array.isArray(data) && data.length >= 2) {
            const prev = parseFloat(data[data.length - 2].c)
            const curr = parseFloat(data[data.length - 1].c)
            const pct = ((curr - prev) / prev) * 100
            return { name: coin, chg: `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`, up: pct >= 0 }
          }
          return null
        }))
        if (!dead) setCryptoTicker(results.filter((r): r is {name:string,chg:string,up:boolean} => r !== null))
      } catch { /* ignore */ }
    }
    loadCrypto()
    const iv = setInterval(loadCrypto, 60_000) // 1분마다 갱신
    return () => { dead = true; clearInterval(iv) }
  }, [])

  return (
    <ThemeContext.Provider value={{ dark, toggle:()=>setDark(d=>!d), c }}>
      <div style={{ display:'flex', flexDirection:'column', height:'100vh', overflow:'hidden', background:c.bg, transition:'background 0.3s' }}>

        {/* ── Header ── */}
        <header style={{ height:36, flexShrink:0, background:dark?'#050810':c.panel, borderBottom:`1px solid ${c.border}`, display:'flex', alignItems:'center', padding:'0 12px', gap:16, transition:'background 0.3s' }}>
          <div style={{ fontFamily:MONO, fontSize:13, fontWeight:700, color:c.gold, letterSpacing:3, flexShrink:0 }}>
            KRX<span style={{ color:c.txtMut }}>::</span>AI
          </div>
          <div style={{ width:1, height:14, background:c.border }}/>

          {/* Scrolling ticker */}
          <div style={{ flex:1, overflow:'hidden', height:'100%', display:'flex', alignItems:'center' }}>
            <div style={{ display:'flex', gap:0, animation:'ticker-scroll 36s linear infinite', whiteSpace:'nowrap' }}>
              {[...Array(2)].flatMap(()=>[
                ...['삼성전자+1.63%','SK하이닉스-1.73%','NAVER+2.12%','카카오-1.60%','현대차-0.61%','셀트리온-1.11%','POSCO+0.65%','KB금융+0.86%','LG에너지+1.30%','삼성바이오+1.81%'],
                ...cryptoTicker.map(ct => `${ct.name}${ct.chg}`),
              ]).map((s,i)=>{
                const up = s.includes('+') && !s.endsWith('+')
                const name = s.replace(/[+-][\d.]+%$/,'')
                const chg  = s.slice(name.length)
                const isCrypto = ['BTC','ETH','SOL','HYPE'].includes(name)
                return (
                  <span key={i} style={{ fontFamily:MONO, fontSize:10, padding:'0 14px', borderRight:`1px solid ${c.border}`, color: isCrypto ? c.cyan : c.txtSec }}>
                    {name} <span style={{ color:up?c.green:c.red }}>{chg}</span>
                  </span>
                )
              })}
            </div>
          </div>

          {/* Status dots + clock + toggle */}
          <div style={{ display:'flex', gap:12, flexShrink:0, alignItems:'center', fontFamily:MONO, fontSize:9 }}>
            {(['PREFECT','MLFLOW','GPU 78%'] as const).map(l => (
              <span key={l} style={{ color:l==='GPU 78%'?c.gold:c.green }}>
                <span style={{ marginRight:3 }}>●</span>{l}
              </span>
            ))}
            <span style={{ color:c.txtMut }}>{clock.toLocaleTimeString('ko-KR',{hour12:false})}</span>
            <button onClick={()=>setDark(d=>!d)} style={{ padding:'3px 10px', fontFamily:MONO, fontSize:9, background:c.border, color:c.txt, border:`1px solid ${c.borderBrt}`, borderRadius:3, cursor:'pointer', letterSpacing:1, transition:'all 0.2s' }}>
              {dark ? '☀ LIGHT' : '☾ DARK'}
            </button>
          </div>
        </header>

        {/* ── Body: 3-column ── */}
        <div style={{ flex:1, display:'flex', overflow:'hidden' }}>
          <AgentStatusPanel/>
          <MainPanel/>
          <ActivityLogPanel/>
        </div>

      </div>
    </ThemeContext.Provider>
  )
}
