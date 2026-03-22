import { useEffect, useRef, useState } from 'react'
import type { CryptoCandle } from '../types/crypto'

const HL_WS_URL = 'wss://api.hyperliquid.xyz/ws'
const HL_INFO_URL = 'https://api.hyperliquid.xyz/info'
const MAX_CANDLES = 200

export interface CoinData {
  candles: CryptoCandle[]
  currentPrice: number | null
  change24h: number | null  // -2.6 = -2.6%
}

export interface UseHLReturn {
  coins: Record<string, CoinData>
  isConnected: boolean
  interval: string
  setInterval: (v: string) => void
}

async function fetch24hChange(coins: string[]): Promise<Record<string, number>> {
  const now = Date.now()
  const result: Record<string, number> = {}
  await Promise.all(coins.map(async coin => {
    try {
      const res = await fetch(HL_INFO_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'candleSnapshot',
          req: { coin, interval: '1d', startTime: now - 86400000 * 3, endTime: now },
        }),
      })
      const data = await res.json()
      if (Array.isArray(data) && data.length >= 2) {
        const prevClose = parseFloat(data[data.length - 2].c)
        const currClose = parseFloat(data[data.length - 1].c)
        result[coin] = ((currClose - prevClose) / prevClose) * 100
      }
    } catch { /* ignore */ }
  }))
  return result
}

async function fetchSnapshot(coin: string, interval: string): Promise<CryptoCandle[]> {
  const ms: Record<string, number> = {
    '1m': 60000, '5m': 300000, '15m': 900000, '1h': 3600000,
  }
  const now = Date.now()
  try {
    const res = await fetch(HL_INFO_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'candleSnapshot',
        req: { coin, interval, startTime: now - (ms[interval] ?? 900000) * 120, endTime: now },
      }),
    })
    const arr = await res.json()
    if (!Array.isArray(arr)) return []
    return arr.map((c: any) => ({
      coin: c.s || coin, interval: c.i || interval,
      openTime: c.t, closeTime: c.T,
      open: +c.o, high: +c.h, low: +c.l, close: +c.c, volume: +c.v,
    }))
  } catch { return [] }
}

export function useHyperliquidMulti(
  coinList: string[],
  initialInterval = '15m',
): UseHLReturn {
  const [interval, setIntervalState] = useState(initialInterval)
  const [isConnected, setIsConnected] = useState(false)
  const [coins, setCoins] = useState<Record<string, CoinData>>({})
  const coinsRef = useRef(coinList)
  const intervalRef = useRef(interval)
  intervalRef.current = interval

  // 초기 스냅샷 + 24h 변동률 로드
  useEffect(() => {
    let dead = false
    const load = async () => {
      const [results, changes] = await Promise.all([
        Promise.all(coinsRef.current.map(c => fetchSnapshot(c, interval))),
        fetch24hChange(coinsRef.current),
      ])
      if (dead) return
      const next: Record<string, CoinData> = {}
      coinsRef.current.forEach((coin, i) => {
        const candles = results[i].slice(-MAX_CANDLES)
        next[coin] = {
          candles,
          currentPrice: candles.length ? candles[candles.length - 1].close : null,
          change24h: changes[coin] ?? null,
        }
      })
      setCoins(next)
    }
    load()
    return () => { dead = true }
  }, [interval])

  // WS 연결
  useEffect(() => {
    let dead = false
    let ws: WebSocket | null = null
    let hb: any
    let reconn: any
    let raf = 0
    // 로컬 뮤터블 데이터 (ref 대신)
    let localData: Record<string, { candles: CryptoCandle[], currentPrice: number | null }> = {}
    // 초기 데이터 복사
    for (const c of coinsRef.current) {
      localData[c] = { candles: [], currentPrice: null, change24h: null }
    }

    function flush() {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        // 새 객체로 만들어야 React가 감지
        const snap: Record<string, CoinData> = {}
        for (const c of coinsRef.current) {
          const d = localData[c]
          snap[c] = { candles: [...d.candles], currentPrice: d.currentPrice, change24h: d.change24h }
        }
        setCoins(snap)
      })
    }

    function connect() {
      if (dead) return
      ws = new WebSocket(HL_WS_URL)

      ws.onopen = () => {
        if (dead) { ws?.close(); return }
        setIsConnected(true)
        for (const coin of coinsRef.current) {
          ws!.send(JSON.stringify({
            method: 'subscribe',
            subscription: { type: 'candle', coin, interval },
          }))
        }
        hb = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN)
            ws.send(JSON.stringify({ method: 'ping' }))
        }, 50000)
      }

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.channel !== 'candle') return
          const d = msg.data
          if (!d?.s || d.i !== intervalRef.current) return
          const coin: string = d.s
          if (!localData[coin]) return

          const candle: CryptoCandle = {
            coin, interval: d.i,
            openTime: d.t, closeTime: d.T,
            open: +d.o, high: +d.h, low: +d.l, close: +d.c, volume: +d.v,
          }

          const arr = localData[coin].candles
          if (arr.length > 0 && arr[arr.length - 1].openTime === candle.openTime) {
            arr[arr.length - 1] = candle  // 같은 봉 → 제자리 업데이트
          } else {
            arr.push(candle)  // 새 봉
            if (arr.length > MAX_CANDLES) arr.splice(0, arr.length - MAX_CANDLES)
          }
          localData[coin].currentPrice = candle.close
          flush()
        } catch {}
      }

      ws.onclose = () => {
        setIsConnected(false)
        clearInterval(hb)
        if (!dead) reconn = setTimeout(connect, 3000)
      }
      ws.onerror = () => ws?.close()
    }

    // 스냅샷이 로드된 후 WS 시작하기 위해 약간 딜레이
    const startTimer = setTimeout(() => {
      // 현재 React state에서 스냅샷 데이터 가져오기
      setCoins(prev => {
        for (const c of coinsRef.current) {
          if (prev[c]) localData[c] = { candles: [...prev[c].candles], currentPrice: prev[c].currentPrice, change24h: prev[c].change24h }
        }
        return prev
      })
      connect()
    }, 500)

    return () => {
      dead = true
      clearTimeout(startTimer)
      clearTimeout(reconn)
      clearInterval(hb)
      cancelAnimationFrame(raf)
      ws?.close()
    }
  }, [interval])

  return {
    coins,
    isConnected,
    interval,
    setInterval: (v: string) => { setIntervalState(v) },
  }
}
