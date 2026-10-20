
import { useCallback, useEffect, useState } from 'react'
import './App.css'

const API = 'http://127.0.0.1:8000'

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
  const [simRunning, setSimRunning] = useState(false)
  const [simGenerated, setSimGenerated] = useState(0)
  const [simLoading, setSimLoading] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [healthResponse, bookResponse, tradesResponse, statusResponse] =
        await Promise.all([
          fetch(`${API}/health`),
          fetch(`${API}/orderbook`),
          fetch(`${API}/trades`),
          fetch(`${API}/simulator/status`),
        ])

      if (
        !healthResponse.ok ||
        !bookResponse.ok ||
        !tradesResponse.ok ||
        !statusResponse.ok
      ) {
        throw new Error('One or more API requests failed')
      }

      const [healthData, bookData, tradesData, statusData] =
        await Promise.all([
          healthResponse.json(),
          bookResponse.json(),
          tradesResponse.json(),
          statusResponse.json(),
        ])

      setHealth(healthData.status === 'healthy' ? 'Connected' : 'Offline')
      setBook(bookData)
      setTrades(Array.isArray(tradesData) ? tradesData : [])
      setSimRunning(statusData.running)
      setSimGenerated(statusData.generated)
    } catch {
      setHealth('Offline')
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(refresh, 2000)

    return () => clearInterval(interval)
  }, [refresh])

  async function submitOrder(event) {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      const response = await fetch(`${API}/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          side,
          price: Number(price),
          quantity: Number(quantity),
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Order submission failed')
      }

      setMessage(
        data.trades?.length
          ? `Order executed! ${data.trades.length} trade(s) completed.`
          : 'Order accepted and added to the order book.',
      )

      await refresh()
    } catch (error) {
      setMessage(error.message || 'Could not connect to the API.')
    } finally {
      setLoading(false)
    }
  }

  async function controlSimulator(action) {
    setSimLoading(true)
    setMessage('')

    try {
      const response = await fetch(`${API}/simulator/${action}`, {
        method: 'POST',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `Could not ${action} simulator`)
      }

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

  const bids = book.bids || []
  const asks = book.asks || []
  
const spread =
  book.best_bid != null && book.best_ask != null
    ? book.best_ask - book.best_bid
    : null


  const activeOrders = bids.length + asks.length

  const formatPrice = (value) =>
    value == null ? '—' : Number(value).toLocaleString()

  return (
    <main className="app">
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

      <section className="hero">
        <div>
          <p className="eyebrow">TRADING ENGINE / LIVE CONSOLE</p>
          <h2>Market Operations</h2>
          <p className="subtitle">
            Monitor order flow, execute orders, and test the matching engine
            in real time.
          </p>
        </div>
        <div className="hero-status">
          <span className="status-dot online" />
          SIMULATION ENVIRONMENT
        </div>
      </section>

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

      <section className="panel simulator-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">AUTOMATED ORDER FLOW</p>
            <h2>Market Simulator</h2>
          </div>

          <span
            className={`tag ${simRunning ? 'tag-running' : ''}`}
          >
            {simRunning ? 'RUNNING' : 'STOPPED'}
          </span>
        </div>

        <p className="subtitle">
          Generate simulated orders and send them through the Python matching
          engine.
        </p>

        <div className="simulator-controls">
          <button
            type="button"
            className="submit buy"
            disabled={
              simLoading || simRunning || health !== 'Connected'
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

      <section className="metrics">
        <article className="metric-card">
          <p>BEST BID</p>
          <strong className="green">
            {formatPrice(book.best_bid)}
          </strong>
          <span>Highest buy price</span>
        </article>

        <article className="metric-card">
          <p>BEST ASK</p>
          <strong className="red">
            {formatPrice(book.best_ask)}
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
  <p>BID–ASK SPREAD</p>
  <strong>
    {spread == null ? '—' : spread.toLocaleString()}
  </strong>
  <span>
    {spread == null
      ? 'Waiting for both sides'
      : 'Price difference in ticks'}
  </span>
</article>

      </section>

      <section className="main-grid">
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
              >
                BUY
              </button>
              <button
                type="button"
                className={side === 'SELL' ? 'selected sell' : ''}
                onClick={() => setSide('SELL')}
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
              required
            />

            <label htmlFor="quantity">Quantity</label>
            <input
              id="quantity"
              type="number"
              min="1"
              step="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              required
            />

            <button
              type="submit"
              className={`submit ${side.toLowerCase()}`}
              disabled={loading || health !== 'Connected'}
            >
              {loading ? 'Submitting...' : `Submit ${side} Order`}
            </button>
          </form>

          <p className="form-note">
            Orders are processed by the ChronosMatch matching engine.
          </p>
        </div>

        <div className="panel orderbook-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">MARKET DEPTH</p>
              <h2>Order Book</h2>
            </div>
            <span className="tag">LIVE</span>
          </div>

          <div className="book-columns">
            <div className="book-side">
              <h3 className="red">ASKS / SELL</h3>
              <div className="table-header">
                <span>Price</span>
                <span>Remaining</span>
              </div>

              {asks.length === 0 ? (
                <p className="empty">No open sell orders</p>
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

            <div className="book-side">
              <h3 className="green">BIDS / BUY</h3>
              <div className="table-header">
                <span>Price</span>
                <span>Remaining</span>
              </div>

              {bids.length === 0 ? (
                <p className="empty">No open buy orders</p>
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

<section className="panel performance-panel">
  <div className="panel-heading">
    <div>
      <p className="eyebrow">ENGINE BENCHMARKS</p>
      <h2>Ring Buffer Performance</h2>
    </div>
    <span className="tag">RECORDED RESULTS</span>
  </div>

  <p className="performance-note">
    Previously measured throughput comparison. These values are
    benchmark results, not live performance measurements.
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

      <section className="panel trades-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">EXECUTION LOG</p>
            <h2>Recent Trades</h2>
          </div>
          <span className="tag">{trades.length} RECORDS</span>
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
                    No trades executed yet. Submit matching orders or start
                    the market simulator.
                  </td>
                </tr>
              ) : (
                [...trades].reverse().slice(0, 20).map((trade, index) => (
                  <tr key={trade.trade_id ?? `trade-${index}`}>
                    <td>{trade.trade_id}</td>
                    <td className="green">{trade.buy_order_id}</td>
                    <td className="red">{trade.sell_order_id}</td>
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

      <footer className="footer">
        <span>CHRONOSMATCH · DEVELOPMENT BUILD</span>
        <span>Educational trading simulation — not a live exchange</span>
      </footer>
    </main>
  )
}

export default App
