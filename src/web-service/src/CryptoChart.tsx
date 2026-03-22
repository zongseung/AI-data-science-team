import { useEffect, useRef, useCallback, useState } from 'react'
import { useHyperliquidMulti, type CoinData } from './hooks/useHyperliquidWS'
import type { CryptoCandle } from './types/crypto'

const COINS = ['BTC', 'ETH', 'SOL', 'HYPE'] as const
const INTERVALS = ['1m', '5m', '15m', '1h'] as const
const MONO = 'IBM Plex Mono, monospace'

interface Colors {
  bgColor: string; panelColor: string; borderColor: string; gridColor: string
  txtColor: string; txtSecColor: string; txtMutColor: string
  greenColor: string; redColor: string; goldColor: string
  blueColor: string; cyanColor: string
}

// ── Canvas renderer ─────────────────────────────────────────────────────

function drawMiniChart(
  canvas: HTMLCanvasElement,
  candles: CryptoCandle[],
  colors: Colors,
) {
  const ctx = canvas.getContext('2d')
  if (!ctx || candles.length === 0) return

  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  ctx.scale(dpr, dpr)

  const W = rect.width
  const H = rect.height
  const PL = 4, PR = 52, PT = 4, PB = 16
  const VOL_H = Math.floor(H * 0.12)
  const CH = H - PT - PB - VOL_H - 4

  const chartW = W - PL - PR
  const spacing = chartW / candles.length
  const cw = Math.max(1, Math.floor(spacing * 0.7))

  const prices = candles.flatMap(d => [d.high, d.low])
  const minP = Math.min(...prices)
  const maxP = Math.max(...prices)
  const pad = (maxP - minP || 1) * 0.05
  const adjMin = minP - pad
  const adjRange = (maxP + pad) - adjMin

  const maxVol = Math.max(...candles.map(d => d.volume))
  const pY = (p: number) => PT + CH - ((p - adjMin) / adjRange) * CH
  const cX = (i: number) => PL + i * spacing + (spacing - cw) / 2

  // Background
  ctx.fillStyle = colors.panelColor
  ctx.fillRect(0, 0, W, H)

  // Grid
  ctx.strokeStyle = colors.gridColor
  ctx.lineWidth = 0.4
  for (let i = 0; i <= 3; i++) {
    const p = adjMin + (adjRange * i) / 3
    const y = pY(p)
    ctx.beginPath(); ctx.setLineDash([1, 3])
    ctx.moveTo(PL, y); ctx.lineTo(W - PR, y)
    ctx.stroke(); ctx.setLineDash([])
  }

  // Volume bars
  const volY = PT + CH + 4
  const lastIdx = candles.length - 1
  candles.forEach((d, i) => {
    const x = cX(i)
    const isUp = d.close >= d.open
    const isLive = i === lastIdx
    const barH = (d.volume / maxVol) * VOL_H * 0.85
    ctx.fillStyle = (isUp ? colors.greenColor : colors.redColor) + (isLive ? '77' : '33')
    ctx.fillRect(x, volY + VOL_H - barH, cw, barH)
  })

  // Candlesticks
  candles.forEach((d, i) => {
    const x = cX(i)
    const isUp = d.close >= d.open
    const cc = isUp ? colors.greenColor : colors.redColor
    const oY = pY(d.open), cY2 = pY(d.close)
    const hY = pY(d.high), lY = pY(d.low)
    const cx = x + cw / 2
    const isLive = i === lastIdx

    if (isLive) { ctx.shadowColor = cc; ctx.shadowBlur = 6 }

    ctx.strokeStyle = cc; ctx.lineWidth = isLive ? 1.5 : 1
    ctx.beginPath(); ctx.moveTo(cx, hY); ctx.lineTo(cx, lY); ctx.stroke()

    ctx.fillStyle = isLive ? cc : cc + 'cc'
    ctx.fillRect(x, Math.min(oY, cY2), cw, Math.max(1, Math.abs(cY2 - oY)))

    if (isLive) { ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0 }
  })

  // MA20
  if (candles.length >= 20) {
    ctx.strokeStyle = colors.goldColor + 'aa'
    ctx.lineWidth = 1
    ctx.beginPath()
    let started = false
    for (let i = 19; i < candles.length; i++) {
      const avg = candles.slice(i - 19, i + 1).reduce((s, c) => s + c.close, 0) / 20
      const x = cX(i) + cw / 2, y = pY(avg)
      if (!started) { ctx.moveTo(x, y); started = true }
      else ctx.lineTo(x, y)
    }
    ctx.stroke()
  }

  // Price axis
  ctx.font = `9px ${MONO}`
  ctx.textAlign = 'left'
  for (let i = 0; i <= 3; i++) {
    const p = adjMin + (adjRange * i) / 3
    ctx.fillStyle = colors.txtMutColor
    const label = p >= 1000 ? p.toLocaleString('en-US', { maximumFractionDigits: 0 }) : p.toFixed(2)
    ctx.fillText(label, W - PR + 4, pY(p) + 3)
  }

  // Current price line + label
  const last = candles[lastIdx]
  const lastY = pY(last.close)
  const isLastUp = last.close >= last.open
  ctx.strokeStyle = (isLastUp ? colors.greenColor : colors.redColor) + '66'
  ctx.lineWidth = 1; ctx.setLineDash([3, 3])
  ctx.beginPath(); ctx.moveTo(PL, lastY); ctx.lineTo(W - PR, lastY); ctx.stroke()
  ctx.setLineDash([])

  const priceLabel = last.close >= 1000
    ? last.close.toLocaleString('en-US', { maximumFractionDigits: 1 })
    : last.close.toFixed(3)
  ctx.fillStyle = isLastUp ? colors.greenColor : colors.redColor
  ctx.fillRect(W - PR, lastY - 8, PR, 16)
  ctx.fillStyle = '#000'
  ctx.font = `bold 9px ${MONO}`
  ctx.fillText(priceLabel, W - PR + 3, lastY + 3)

  // Time labels
  const step = Math.max(1, Math.floor(candles.length / 4))
  ctx.font = `8px ${MONO}`
  ctx.fillStyle = colors.txtMutColor
  ctx.textAlign = 'center'
  for (let i = 0; i < candles.length; i += step) {
    const date = new Date(candles[i].openTime)
    const t = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
    ctx.fillText(t, cX(i) + cw / 2, H - PB + 10)
  }
}

// ── Single coin panel ───────────────────────────────────────────────────

function CoinPanel({
  coin, data, colors,
}: {
  coin: string
  data: CoinData
  colors: Colors
}) {
  const { candles, currentPrice, change24h } = data

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const prevPriceRef = useRef<number | null>(null)
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)

  // Price flash
  useEffect(() => {
    if (currentPrice === null || prevPriceRef.current === null) {
      prevPriceRef.current = currentPrice
      return
    }
    if (currentPrice !== prevPriceRef.current) {
      setFlash(currentPrice > prevPriceRef.current ? 'up' : 'down')
      prevPriceRef.current = currentPrice
      const t = setTimeout(() => setFlash(null), 300)
      return () => clearTimeout(t)
    }
  }, [currentPrice])

  // Canvas draw
  const draw = useCallback(() => {
    if (canvasRef.current && candles.length > 0) {
      drawMiniChart(canvasRef.current, candles, colors)
    }
  }, [candles, colors])

  useEffect(() => {
    draw()
    const h = () => draw()
    window.addEventListener('resize', h)
    return () => window.removeEventListener('resize', h)
  }, [draw])

  const last = candles[candles.length - 1]
  const first = candles[0]
  const price = currentPrice ?? last?.close ?? 0
  const pct = first && last ? ((last.close - first.open) / first.open) * 100 : 0
  const isUp = pct >= 0
  const loading = candles.length === 0

  const fmt = (p: number) => p >= 1000
    ? p.toLocaleString('en-US', { maximumFractionDigits: 2 })
    : p.toFixed(4)

  const fmtVol = (v: number) => {
    if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M'
    if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K'
    return v.toFixed(0)
  }

  const totalVol = candles.reduce((s, c) => s + c.volume, 0)

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      border: `1px solid ${colors.borderColor}`,
      borderRadius: 6, overflow: 'hidden',
      background: colors.panelColor, minHeight: 0,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 10px',
        borderBottom: `1px solid ${colors.borderColor}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontFamily: MONO, fontSize: 13, fontWeight: 800, color: colors.txtColor }}>
            {coin}
          </span>
          <span style={{ fontFamily: MONO, fontSize: 8, color: colors.txtMutColor }}>PERP</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
          <span style={{
            fontFamily: MONO, fontSize: 14, fontWeight: 700,
            color: isUp ? colors.greenColor : colors.redColor,
            background: flash === 'up' ? colors.greenColor + '33'
              : flash === 'down' ? colors.redColor + '33' : 'transparent',
            padding: '1px 4px', borderRadius: 3, transition: 'background 0.3s',
          }}>
            {loading ? '—' : fmt(price)}
          </span>
          {change24h !== null ? (
            <span style={{
              fontFamily: MONO, fontSize: 10, fontWeight: 600,
              color: change24h >= 0 ? colors.greenColor : colors.redColor,
            }}>
              24h {change24h >= 0 ? '+' : ''}{change24h.toFixed(2)}%
            </span>
          ) : (
            <span style={{
              fontFamily: MONO, fontSize: 10, fontWeight: 600,
              color: isUp ? colors.greenColor : colors.redColor,
            }}>
              {loading ? '' : `${isUp ? '+' : ''}${pct.toFixed(2)}%`}
            </span>
          )}
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
        {loading && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: MONO, fontSize: 10, color: colors.txtMutColor,
          }}>
            Loading...
          </div>
        )}
        <canvas ref={canvasRef} style={{ display: 'block', width: '100%', height: '100%' }} />
      </div>

      {/* Footer */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        padding: '3px 10px',
        borderTop: `1px solid ${colors.borderColor}`,
        fontFamily: MONO, fontSize: 8, color: colors.txtMutColor,
      }}>
        <span>VOL {loading ? '—' : fmtVol(totalVol)}</span>
        <span>{candles.length} candles</span>
      </div>
    </div>
  )
}

// ── Sentiment types ─────────────────────────────────────────────────────

interface SentimentArticle {
  coin: string; title: string; source: string; url: string
  sentiment_score: number; sentiment_label: string
  published_at: string | null; keywords: string[]
}

interface SentimentSummary {
  coin: string; avg_sentiment: number; sentiment_label: string
  article_count: number; positive_count: number; negative_count: number; neutral_count: number
  top_keywords: { keyword: string; score: number }[]
}

interface CoinSentiment {
  articles: SentimentArticle[]
  summary: SentimentSummary | null
}

const SENTIMENT_API = 'http://localhost:8090'

// ── Sentiment Panel ─────────────────────────────────────────────────────

function SentimentPanel({ colors }: { colors: Colors }) {
  const [data, setData] = useState<Record<string, CoinSentiment>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let dead = false
    async function load() {
      try {
        const results = await Promise.all(
          COINS.map(async coin => {
            const r = await fetch(`${SENTIMENT_API}/api/sentiment/${coin}?limit=20`)
            return { coin, data: await r.json() as CoinSentiment }
          })
        )
        if (dead) return
        const map: Record<string, CoinSentiment> = {}
        for (const { coin, data } of results) map[coin] = data
        setData(map)
      } catch { /* ignore */ }
      setLoading(false)
    }
    load()
    // 5분마다 갱신
    const iv = setInterval(load, 5 * 60_000)
    return () => { dead = true; clearInterval(iv) }
  }, [])

  const sentimentColor = (score: number, c: Colors) =>
    score >= 0.05 ? c.greenColor : score <= -0.05 ? c.redColor : c.txtMutColor

  const sentimentEmoji = (label: string) =>
    label === 'positive' ? '▲' : label === 'negative' ? '▼' : '—'

  const fmtTime = (s: string | null) => {
    if (!s) return ''
    const d = new Date(s)
    return `${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
  }

  if (loading) {
    return (
      <div style={{ padding: 12, fontFamily: MONO, fontSize: 10, color: colors.txtMutColor }}>
        Loading sentiment...
      </div>
    )
  }

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr 1fr',
      gap: 6, padding: '0',
    }}>
      {COINS.map(coin => {
        const cs = data[coin]
        const summary = cs?.summary
        const articles = cs?.articles ?? []

        return (
          <div key={coin} style={{
            border: `1px solid ${colors.borderColor}`,
            borderRadius: 6, overflow: 'hidden',
            background: colors.panelColor,
          }}>
            {/* Header: coin + sentiment bar */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '6px 10px',
              borderBottom: `1px solid ${colors.borderColor}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontFamily: MONO, fontSize: 11, fontWeight: 800, color: colors.txtColor }}>
                  {coin}
                </span>
                <span style={{ fontFamily: MONO, fontSize: 8, color: colors.txtMutColor }}>SENTIMENT</span>
              </div>
              {summary && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {/* Sentiment bar */}
                  <div style={{
                    width: 60, height: 6, borderRadius: 3,
                    background: colors.borderColor, overflow: 'hidden',
                    position: 'relative',
                  }}>
                    <div style={{
                      position: 'absolute',
                      left: '50%', top: 0, height: '100%',
                      width: `${Math.abs(summary.avg_sentiment) * 50}%`,
                      marginLeft: summary.avg_sentiment >= 0 ? 0 : `-${Math.abs(summary.avg_sentiment) * 50}%`,
                      background: sentimentColor(summary.avg_sentiment, colors),
                      borderRadius: 3,
                    }} />
                  </div>
                  <span style={{
                    fontFamily: MONO, fontSize: 11, fontWeight: 700,
                    color: sentimentColor(summary.avg_sentiment, colors),
                  }}>
                    {sentimentEmoji(summary.sentiment_label)} {summary.avg_sentiment.toFixed(2)}
                  </span>
                </div>
              )}
            </div>

            {/* Stats row */}
            {summary && (
              <div style={{
                display: 'flex', gap: 10, padding: '4px 10px',
                borderBottom: `1px solid ${colors.borderColor}`,
                fontFamily: MONO, fontSize: 8,
              }}>
                <span style={{ color: colors.greenColor }}>+{summary.positive_count}</span>
                <span style={{ color: colors.redColor }}>-{summary.negative_count}</span>
                <span style={{ color: colors.txtMutColor }}>{summary.neutral_count} neutral</span>
                <span style={{ color: colors.txtMutColor, marginLeft: 'auto' }}>
                  {summary.article_count} articles
                </span>
              </div>
            )}

            {/* Articles list */}
            <div style={{ maxHeight: 200, overflowY: 'auto', padding: '4px 0' }}>
              {articles.length === 0 && (
                <div style={{ padding: '8px 10px', fontFamily: MONO, fontSize: 9, color: colors.txtMutColor }}>
                  No articles
                </div>
              )}
              {articles.map((a, i) => (
                <a
                  key={i}
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 6,
                    padding: '3px 10px',
                    textDecoration: 'none',
                    borderBottom: i < articles.length - 1 ? `1px solid ${colors.borderColor}44` : 'none',
                  }}
                >
                  <span style={{
                    fontFamily: MONO, fontSize: 10, fontWeight: 700,
                    color: sentimentColor(a.sentiment_score, colors),
                    minWidth: 30, textAlign: 'right',
                  }}>
                    {a.sentiment_score >= 0 ? '+' : ''}{a.sentiment_score.toFixed(2)}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontFamily: MONO, fontSize: 9, color: colors.txtSecColor,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {a.title}
                    </div>
                    <div style={{ fontFamily: MONO, fontSize: 7, color: colors.txtMutColor }}>
                      {a.source} · {fmtTime(a.published_at)}
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Main: charts + sentiment ────────────────────────────────────────────

export default function CryptoChart(props: Colors) {
  const { coins, isConnected, interval, setInterval: setIv } = useHyperliquidMulti(
    ['BTC', 'ETH', 'SOL', 'HYPE'], '15m'
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 0, overflow: 'auto' }}>
      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0',
        borderBottom: `1px solid ${props.borderColor}`,
        flexShrink: 0,
      }}>
        <span style={{
          fontFamily: MONO, fontSize: 11, fontWeight: 700,
          color: props.cyanColor, letterSpacing: 1,
        }}>
          HYPERLIQUID
        </span>

        <div style={{ display: 'flex', gap: 2 }}>
          {INTERVALS.map(iv => (
            <button
              key={iv}
              onClick={() => setIv(iv)}
              style={{
                padding: '3px 8px',
                fontFamily: MONO, fontSize: 9,
                background: interval === iv ? props.txtMutColor + '33' : 'transparent',
                color: interval === iv ? props.txtColor : props.txtMutColor,
                border: 'none', borderRadius: 3, cursor: 'pointer',
              }}
            >
              {iv}
            </button>
          ))}
        </div>

        <div style={{
          marginLeft: 'auto',
          display: 'flex', alignItems: 'center', gap: 4,
          fontFamily: MONO, fontSize: 8,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: isConnected ? props.greenColor : props.redColor,
            display: 'inline-block',
          }} />
          <span style={{ color: isConnected ? props.greenColor : props.txtMutColor }}>
            {isConnected ? 'LIVE' : 'CONNECTING'}
          </span>
        </div>
      </div>

      {/* 2x2 Chart Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gridTemplateRows: '1fr 1fr',
        gap: 6, padding: '6px 0',
        minHeight: 400,
        flexShrink: 0,
      }}>
        {COINS.map(coin => (
          <CoinPanel
            key={coin}
            coin={coin}
            data={coins[coin] ?? { candles: [], currentPrice: null, change24h: null }}
            colors={props}
          />
        ))}
      </div>

      {/* Sentiment section header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 0 4px',
        borderTop: `1px solid ${props.borderColor}`,
        flexShrink: 0,
      }}>
        <span style={{
          fontFamily: MONO, fontSize: 10, fontWeight: 700,
          color: props.cyanColor, letterSpacing: 1,
        }}>
          NEWS SENTIMENT
        </span>
        <span style={{ fontFamily: MONO, fontSize: 8, color: props.txtMutColor }}>
          TF-IDF + VADER · 6h update
        </span>
      </div>

      {/* Sentiment panels */}
      <SentimentPanel colors={props} />
    </div>
  )
}
