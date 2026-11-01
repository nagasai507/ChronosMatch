
import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'

const API = 'http://127.0.0.1:8000'

// Reusable API request handler.
async function apiRequest(url, options = {}) {
  let response

  try {
    response = await fetch(url, options)
  } catch {
    throw new Error(
      'Cannot connect to the ChronosMatch API. Check whether the backend is running.',
    )
  }

  const contentType = response.headers.get('content-type') || ''
  let data

  if (contentType.includes('application/json')) {
    try {
      data = await response.json()
    } catch {
      throw new Error('The API returned an invalid JSON response.')
    }
  } else {
    const responseText = await response.text()
    data = responseText ? { detail: responseText } : null
  }

  if (!response.ok) {
    const detail = data?.detail

    const errorMessage = Array.isArray(detail)
      ? detail
          .map((item) => item.msg || JSON.stringify(item))
          .join(', ')
      : detail || `API request failed (${response.status})`

    throw new Error(errorMessage)
  }

  return data
}

function App() {
  const [health, setHealth] = useState('Checking...')

  const [book, setBook] = useState({
    bids: [],
    asks: [],
    best_bid: null,
    best_ask: null,
  })

  const [trades, setTrades] = useState([])

  const [side, setSide] = useState('BUY')
  const [price, setPrice] = useState('100')
  const [quantity, setQuantity] = useState('10')

  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [refreshError, setRefreshError] = useState('')

  const [simRunning, setSimRunning] = useState(false)
  const [simGenerated, setSimGenerated] = useState(0)
  const [simLoading, setSimLoading] = useState(false)

  // Prevent overlapping dashboard refresh requests.
  const refreshInFlight = useRef(false)

  // Refresh dashboard endpoints independently.
  const refresh = useCallback(async () => {
    if (refreshInFlight.current) return

    refreshInFlight.current = true

    try {
      const endpoints = [
        ['health', `${API}/health`],
        ['orderbook', `${API}/orderbook`],
        ['trades', `${API}/trades`],
        ['simulator', `${API}/simulator/status`],
      ]

      const results = await Promise.allSettled(
        endpoints.map(([, url]) => apiRequest(url)),
      )

      const failedEndpoints = []

      const [
        healthResult,
        bookResult,
        tradesResult,
        statusResult,
      ] = results

      // API health.
      if (healthResult.status === 'fulfilled') {
        setHealth(
          healthResult.value?.status === 'ok'
            ? 'Connected'
            : 'Offline',
        )
      } else {
        setHealth('Offline')
        failedEndpoints.push('health')
      }

      // Order book.
      if (bookResult.status === 'fulfilled') {
        const data = bookResult.value

        if (
          Array.isArray(data?.bids) &&
          Array.isArray(data?.asks)
        ) {
          setBook(data)
        } else {
          failedEndpoints.push('order book')
        }
      } else {
        failedEndpoints.push('order book')
      }

      // Recent trades.
      if (tradesResult.status === 'fulfilled') {
        if (Array.isArray(tradesResult.value)) {
          setTrades(tradesResult.value)
        } else {
          failedEndpoints.push('trades')
        }
      } else {
        failedEndpoints.push('trades')
      }

      // Simulator status.
      if (statusResult.status === 'fulfilled') {
        setSimRunning(Boolean(statusResult.value?.running))
        setSimGenerated(
          Number(statusResult.value?.generated) || 0,
        )
      } else {
        failedEndpoints.push('simulator status')
      }

      setRefreshError(
        failedEndpoints.length
          ? `Unable to refresh: ${failedEndpoints.join(', ')}`
          : '',
      )
    } finally {
      refreshInFlight.current = false
    }
  }, [])

  // Initial dashboard load and automatic refresh every 2 seconds.
  useEffect(() => {
    refresh()

    const interval = setInterval(refresh, 2000)

    return () => clearInterval(interval)
  }, [refresh])

  // Submit a BUY or SELL order.
  async function submitOrder(event) {
    event.preventDefault()

    const numericPrice = Number(price)
    const numericQuantity = Number(quantity)

    if (
      !Number.isSafeInteger(numericPrice) ||
      numericPrice <= 0
    ) {
      setMessage('Price must be a positive whole number.')
      return
    }

    if (
      !Number.isSafeInteger(numericQuantity) ||
      numericQuantity <= 0
    ) {
      setMessage('Quantity must be a positive whole number.')
      return
    }

    setLoading(true)
    setMessage('')

    try {
      const data = await apiRequest(`${API}/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          side,
          price: numericPrice,
          quantity: numericQuantity,
        }),
      })

      setMessage(
        data.trades?.length
          ? `Order executed! ${data.trades.length} trade(s) completed.`
          : 'Order accepted and added to the order book.',
      )

      // Refresh the order book and trade history immediately.
      await refresh()
    } catch (error) {
      setMessage(error.message || 'Order submission failed.')
    } finally {
      setLoading(false)
    }
  }

  // Start or stop the market simulator.
  async function controlSimulator(action) {
    setSimLoading(true)
    setMessage('')

    try {
      const data = await apiRequest(
        `${API}/simulator/${action}`,
        {
          method: 'POST',
        },
      )

      setMessage(
        action === 'start'
          ? data.status === 'already_running'
            ? 'The market simulator is already running.'
            : 'Market simulator started successfully.'
          : 'Market simulator stopped.',
      )

      await refresh()
    } catch (error) {
      setMessage(error.message || 'Simulator request failed.')
    } finally {
      setSimLoading(false)
    }
  }

  // Safely read order book data.
  const bids = Array.isArray(book.bids) ? book.bids : []
  const asks = Array.isArray(book.asks) ? book.asks : []

  // The API returns best_bid and best_ask as order objects.
  const bestBid =
    book.best_bid?.price != null &&
    Number.isFinite(Number(book.best_bid.price))
      ? Number(book.best_bid.price)
      : null

  const bestAsk =
    book.best_ask?.price != null &&
    Number.isFinite(Number(book.best_ask.price))
      ? Number(book.best_ask.price)
      : null

  const spread =
    bestBid !== null && bestAsk !== null
      ? bestAsk - bestBid
      : null

  const activeOrders = bids.length + asks.length

  // Consistent price formatting.
  const formatPrice = (value) => {
    if (
      value == null ||
      value === '' ||
      !Number.isFinite(Number(value))
    ) {
      return '—'
    }

    return Number(value).toLocaleString()
  }

  return (
    <main className="app">
      {/* Header */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">C</div>

          <div>
            <h1>ChronosMatch</h1>
            <p>High-Performance Matching Engine</p>
          </div>
        </div>

        <div className="connection">
          <span
            className={`status-dot ${
              health === 'Connected' ? 'online' : 'offline'
            }`}
          />

          <span>API {health}</span>
        </div>
      </header>

      {/* Hero */}
      <section className="hero">
        <div>
          <p className="eyebrow">
            TRADING ENGINE / LIVE CONSOLE
          </p>

          <h2>Market Operations</h2>

          <p className="subtitle">
            Monitor order flow, execute orders, and test the
            matching engine in real time.
          </p>
        </div>

        <div className="hero-status">
          <span className="status-dot online" />
          SIMULATION ENVIRONMENT
        </div>
      </section>

      {/* User notifications */}
      {message && (
        <div className="notice" role="status">
          <span>{message}</span>

          <button
            type="button"
            className="dismiss"
            onClick={() => setMessage('')}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}

      {refreshError && (
        <div className="notice" role="status">
          <span>{refreshError}</span>
        </div>
      )}

      {/* Market Simulator */}
      <section className="panel simulator-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">AUTOMATED ORDER FLOW</p>
            <h2>Market Simulator</h2>
          </div>

          <span
            className={`tag ${
              simRunning ? 'tag-running' : ''
            }`}
          >
            {simRunning ? 'RUNNING' : 'STOPPED'}
          </span>
        </div>

        <p className="subtitle">
          Generate simulated orders and send them through the
          Python matching engine.
        </p>

        <div className="simulator-controls">
          <button
            type="button"
            className="submit buy"
            disabled={
              simLoading ||
              simRunning ||
              health !== 'Connected'
            }
            onClick={() => controlSimulator('start')}
          >
            {simLoading && !simRunning
              ? 'Starting...'
              : '▶ Start Simulation'}
          </button>

          <button
            type="button"
            className="submit sell"
            disabled={simLoading || !simRunning}
            onClick={() => controlSimulator('stop')}
          >
            {simLoading && simRunning
              ? 'Stopping...'
              : '■ Stop Simulation'}
          </button>

          <div className="simulator-count">
            <span>ORDERS GENERATED</span>
            <strong>{simGenerated.toLocaleString()}</strong>
          </div>
        </div>
      </section>

      {/* Dashboard Metrics */}
      <section className="metrics">
        <article className="metric-card">
          <p>BEST BID</p>
          <strong className="green">
            {formatPrice(bestBid)}
          </strong>
          <span>Highest buy price</span>
        </article>

        <article className="metric-card">
          <p>BEST ASK</p>
          <strong className="red">
            {formatPrice(bestAsk)}
          </strong>
          <span>Lowest sell price</span>
        </article>

        <article className="metric-card">
          <p>ACTIVE ORDERS</p>
          <strong>{activeOrders}</strong>
          <span>Orders waiting in the book</span>
        </article>

        <article className="metric-card">
          <p>EXECUTED TRADES</p>
          <strong>{trades.length}</strong>
          <span>Recorded trade executions</span>
        </article>

        <article className="metric-card">
          <p>BID-ASK SPREAD</p>
          <strong>{formatPrice(spread)}</strong>
          <span>
            {spread === null
              ? 'Waiting for both sides'
              : 'Price difference in ticks'}
          </span>
        </article>
      </section>

      {/* Order Entry and Order Book */}
      <section className="main-grid">
        {/* Order Entry */}
        <div className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">ORDER ENTRY</p>
              <h2>Place an Order</h2>
            </div>

            <span className="tag">MANUAL</span>
          </div>

          <form onSubmit={submitOrder} className="order-form">
            <label htmlFor="side">Order Side</label>

            <div className="side-toggle">
              <button
                type="button"
                className={side === 'BUY' ? 'selected buy' : ''}
                onClick={() => setSide('BUY')}
                disabled={loading}
              >
                BUY
              </button>

              <button
                type="button"
                className={side === 'SELL' ? 'selected sell' : ''}
                onClick={() => setSide('SELL')}
                disabled={loading}
              >
                SELL
              </button>
            </div>

            <label htmlFor="price">Price (ticks)</label>

            <input
              id="price"
              type="number"
              min="1"
              step="1"
              value={price}
              onChange={(event) => setPrice(event.target.value)}
              disabled={loading}
              required
            />

            <label htmlFor="quantity">Quantity</label>

            <input
              id="quantity"
              type="number"
              min="1"
              step="1"
              value={quantity}
              onChange={(event) =>
                setQuantity(event.target.value)
              }
              disabled={loading}
              required
            />

            <button
              type="submit"
              className={`submit ${side.toLowerCase()}`}
              disabled={loading || health !== 'Connected'}
            >
              {loading
                ? 'Submitting...'
                : `Submit ${side} Order`}
            </button>
          </form>

          <p className="form-note">
            Orders are processed by the ChronosMatch matching
            engine.
          </p>
        </div>

        {/* Order Book */}
        <div className="panel orderbook-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">MARKET DEPTH</p>
              <h2>Order Book</h2>
            </div>

            <span className="tag">LIVE</span>
          </div>

          <div className="book-columns">
            {/* Asks */}
            <div className="book-side">
              <h3 className="red">ASKS / SELL</h3>

              <div className="table-header">
                <span>Price</span>
                <span>Remaining</span>
              </div>

              {asks.length === 0 ? (
                <p className="empty">
                  No open sell orders
                </p>
              ) : (
                [...asks].reverse().map((order, index) => (
                  <div
                    className="book-row ask-row"
                    key={order.order_id || `ask-${index}`}
                  >
                    <span>{formatPrice(order.price)}</span>

                    <span>
                      {order.remaining_quantity ??
                        order.quantity}
                    </span>
                  </div>
                ))
              )}
            </div>

            {/* Bids */}
            <div className="book-side">
              <h3 className="green">BIDS / BUY</h3>

              <div className="table-header">
                <span>Price</span>
                <span>Remaining</span>
              </div>

              {bids.length === 0 ? (
                <p className="empty">
                  No open buy orders
                </p>
              ) : (
                bids.map((order, index) => (
                  <div
                    className="book-row bid-row"
                    key={order.order_id || `bid-${index}`}
                  >
                    <span>{formatPrice(order.price)}</span>

                    <span>
                      {order.remaining_quantity ??
                        order.quantity}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Ring Buffer Performance */}
      <section className="panel performance-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">ENGINE BENCHMARKS</p>
            <h2>Ring Buffer Performance</h2>
          </div>

          <span className="tag">RECORDED RESULTS</span>
        </div>

        <p className="performance-note">
          Previously measured throughput comparison. These
          values are benchmark results, not live performance
          measurements.
        </p>

        <div className="benchmark-row">
          <div className="benchmark-label">
            <span>Individual writes</span>
            <strong>96,383 orders/sec</strong>
          </div>

          <div className="benchmark-track">
            <div className="benchmark-bar individual-bar" />
          </div>
        </div>

        <div className="benchmark-row">
          <div className="benchmark-label">
            <span>Batch writes</span>
            <strong>234,872 orders/sec</strong>
          </div>

          <div className="benchmark-track">
            <div className="benchmark-bar batch-bar" />
          </div>
        </div>

        <div className="benchmark-summary">
          <div>
            <span>Batch speedup</span>
            <strong>2.44×</strong>
          </div>

          <div>
            <span>Throughput improvement</span>
            <strong>+143.69%</strong>
          </div>
        </div>
      </section>

      {/* Recent Trades */}
      <section className="panel trades-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">EXECUTION LOG</p>
            <h2>Recent Trades</h2>
          </div>

          <span className="tag">
            {trades.length} RECORDS
          </span>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Trade ID</th>
                <th>Buy Order</th>
                <th>Sell Order</th>
                <th>Price</th>
                <th>Quantity</th>
                <th>Timestamp</th>
              </tr>
            </thead>

            <tbody>
              {trades.length === 0 ? (
                <tr>
                  <td colSpan="6" className="empty">
                    No trades executed yet. Submit matching
                    orders or start the market simulator.
                  </td>
                </tr>
              ) : (
                [...trades]
                  .reverse()
                  .slice(0, 20)
                  .map((trade, index) => (
                    <tr
                      key={
                        trade.trade_id ?? `trade-${index}`
                      }
                    >
                      <td>{trade.trade_id}</td>

                      <td className="green">
                        {trade.buy_order_id}
                      </td>

                      <td className="red">
                        {trade.sell_order_id}
                      </td>

                      <td>{formatPrice(trade.price)}</td>

                      <td>{trade.quantity}</td>

                      <td>{trade.timestamp ?? '—'}</td>
                    </tr>
                  ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <span>CHRONOSMATCH · DEVELOPMENT BUILD</span>

        <span>
          Educational trading simulation — not a live exchange
        </span>
      </footer>
    </main>
  )
}

export default App
