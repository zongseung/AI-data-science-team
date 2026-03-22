import { useEffect, useRef } from 'react'

// ── Types ──────────────────────────────────────────────────────────────────

interface StockChartProps {
  symbol: string
  color: string        // up candle color / accent
  bgColor: string      // panel background
  borderColor: string
  gridColor: string
  txtMutColor: string
  goldColor: string
  redColor: string
  height?: number
}

interface OHLCV {
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// ── Mock data generation ───────────────────────────────────────────────────

function generateOHLCV(symbol: string, count: number = 60): OHLCV[] {
  // Use symbol as a seed for deterministic-ish starting values
  const startPrice = symbol === 'KOSPI' ? 2612 : 73000
  const volatility = symbol === 'KOSPI' ? 30 : 800

  const candles: OHLCV[] = []
  let price = startPrice

  // Simple seeded pseudo-random using symbol chars
  let seed = symbol.split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0)
  function rand(): number {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff
    return (seed >>> 0) / 0xffffffff
  }

  for (let i = 0; i < count; i++) {
    const change = (rand() - 0.495) * volatility * 2
    const open = price
    price = Math.max(open + change, startPrice * 0.7)
    const close = price

    const range = volatility * (0.3 + rand() * 0.7)
    const high = Math.max(open, close) + rand() * range * 0.5
    const low = Math.min(open, close) - rand() * range * 0.5
    const volume = 5000000 + rand() * 20000000

    candles.push({ open, high, low, close, volume })
  }

  return candles
}

// ── Moving average ─────────────────────────────────────────────────────────

function calcMA(data: OHLCV[], period: number): (number | null)[] {
  return data.map((_, i) => {
    if (i < period - 1) return null
    const slice = data.slice(i - period + 1, i + 1)
    return slice.reduce((s, d) => s + d.close, 0) / period
  })
}

// ── Component ─────────────────────────────────────────────────────────────

export default function StockChart({
  symbol,
  color,
  bgColor,
  borderColor,
  gridColor,
  txtMutColor,
  goldColor,
  redColor,
  height = 120,
}: StockChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    // Size canvas to its layout width
    canvas.width = canvas.offsetWidth || 300
    canvas.height = height

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width
    const H = canvas.height

    const data = generateOHLCV(symbol, 60)
    const ma20 = calcMA(data, 20)

    // Layout regions
    const PADDING_LEFT = 4
    const PADDING_RIGHT = 50  // space for price axis labels
    const PADDING_TOP = 6
    const VOLUME_HEIGHT = Math.floor(H * 0.2)
    const CHART_HEIGHT = H - PADDING_TOP - VOLUME_HEIGHT - 4

    const chartW = W - PADDING_LEFT - PADDING_RIGHT
    const candleW = Math.max(1, Math.floor(chartW / data.length) - 1)
    const candleSpacing = chartW / data.length

    // Price range
    const prices = data.flatMap(d => [d.high, d.low])
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const priceRange = maxPrice - minPrice || 1

    // Volume range
    const maxVol = Math.max(...data.map(d => d.volume))

    // Helpers
    const priceToY = (p: number) =>
      PADDING_TOP + CHART_HEIGHT - ((p - minPrice) / priceRange) * CHART_HEIGHT

    const candleX = (i: number) => PADDING_LEFT + i * candleSpacing + candleSpacing * 0.1

    // ── Background ─────────────────────────────────────────────────────────
    ctx.fillStyle = bgColor
    ctx.fillRect(0, 0, W, H)

    // ── Grid lines ─────────────────────────────────────────────────────────
    ctx.strokeStyle = gridColor
    ctx.lineWidth = 0.5

    // Horizontal price grid (4 levels)
    for (let i = 0; i <= 3; i++) {
      const p = minPrice + (priceRange * i) / 3
      const y = priceToY(p)
      ctx.beginPath()
      ctx.moveTo(PADDING_LEFT, y)
      ctx.lineTo(W - PADDING_RIGHT, y)
      ctx.stroke()
    }

    // Vertical date grid (every ~10 candles)
    for (let i = 0; i < data.length; i += 10) {
      const x = candleX(i) + candleW / 2
      ctx.beginPath()
      ctx.moveTo(x, PADDING_TOP)
      ctx.lineTo(x, PADDING_TOP + CHART_HEIGHT)
      ctx.stroke()
    }

    // ── Volume bars ────────────────────────────────────────────────────────
    const volY = PADDING_TOP + CHART_HEIGHT + 4

    data.forEach((d, i) => {
      const x = candleX(i)
      const isUp = d.close >= d.open
      const barH = (d.volume / maxVol) * VOLUME_HEIGHT * 0.9
      ctx.fillStyle = isUp ? color + '66' : redColor + '66'
      ctx.fillRect(x, volY + VOLUME_HEIGHT - barH, Math.max(1, candleW), barH)
    })

    // ── Candlesticks ───────────────────────────────────────────────────────
    data.forEach((d, i) => {
      const x = candleX(i)
      const isUp = d.close >= d.open
      const candleColor = isUp ? color : redColor

      const openY = priceToY(d.open)
      const closeY = priceToY(d.close)
      const highY = priceToY(d.high)
      const lowY = priceToY(d.low)

      const bodyTop = Math.min(openY, closeY)
      const bodyH = Math.max(1, Math.abs(closeY - openY))
      const centerX = x + candleW / 2

      // Wick
      ctx.strokeStyle = candleColor
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(centerX, highY)
      ctx.lineTo(centerX, lowY)
      ctx.stroke()

      // Body
      ctx.fillStyle = candleColor
      ctx.fillRect(x, bodyTop, Math.max(1, candleW), bodyH)
    })

    // ── MA line ────────────────────────────────────────────────────────────
    ctx.strokeStyle = goldColor + 'cc'
    ctx.lineWidth = 1
    ctx.beginPath()
    let maStarted = false
    ma20.forEach((val, i) => {
      if (val === null) return
      const x = candleX(i) + candleW / 2
      const y = priceToY(val)
      if (!maStarted) {
        ctx.moveTo(x, y)
        maStarted = true
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // ── Border ─────────────────────────────────────────────────────────────
    ctx.strokeStyle = borderColor
    ctx.lineWidth = 1
    ctx.strokeRect(0.5, 0.5, W - 1, H - 1)

    // ── Price axis (right side) ─────────────────────────────────────────────
    ctx.font = '8px IBM Plex Mono,monospace'
    ctx.fillStyle = txtMutColor
    ctx.textAlign = 'left'

    for (let i = 0; i <= 3; i++) {
      const p = minPrice + (priceRange * i) / 3
      const y = priceToY(p)
      const label = p >= 1000
        ? p.toLocaleString('ko-KR', { maximumFractionDigits: 0 })
        : p.toFixed(2)
      ctx.fillText(label, W - PADDING_RIGHT + 4, y + 3)
    }

    // ── Latest price label ─────────────────────────────────────────────────
    const last = data[data.length - 1]
    const first = data[0]
    const pctChg = ((last.close - first.close) / first.close) * 100
    const pctStr = (pctChg >= 0 ? '+' : '') + pctChg.toFixed(2) + '%'
    const priceStr = last.close >= 1000
      ? Math.round(last.close).toLocaleString('ko-KR')
      : last.close.toFixed(2)

    const lastY = priceToY(last.close)

    // Horizontal line at last price
    ctx.strokeStyle = color + '88'
    ctx.lineWidth = 0.5
    ctx.setLineDash([3, 3])
    ctx.beginPath()
    ctx.moveTo(PADDING_LEFT, lastY)
    ctx.lineTo(W - PADDING_RIGHT, lastY)
    ctx.stroke()
    ctx.setLineDash([])

    // Label background
    ctx.fillStyle = color + '22'
    ctx.fillRect(W - PADDING_RIGHT, lastY - 7, PADDING_RIGHT - 1, 13)

    ctx.font = 'bold 7px IBM Plex Mono,monospace'
    ctx.fillStyle = color
    ctx.textAlign = 'left'
    ctx.fillText(pctStr, W - PADDING_RIGHT + 3, lastY + 3)

    // Small price above
    ctx.font = '7px IBM Plex Mono,monospace'
    ctx.fillStyle = color
    ctx.fillText(priceStr, W - PADDING_RIGHT + 3, lastY - 9)

  }, [symbol, color, bgColor, borderColor, gridColor, txtMutColor, goldColor, redColor, height])

  return (
    <canvas
      ref={canvasRef}
      style={{ display: 'block', width: '100%', height: `${height}px` }}
    />
  )
}
