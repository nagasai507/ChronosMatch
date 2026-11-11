import { useState } from 'react'

export default function Auth({ apiUrl, onAuthenticated, onClose }) {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setLoading(true)

    try {
      const isRegister = mode === 'register'

      const response = await fetch(
        `${apiUrl}/auth/${isRegister ? 'register' : 'login'}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            isRegister
              ? { username, email, password }
              : { email, password },
          ),
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed.')
      }

      if (isRegister) {
        setMode('login')
        setPassword('')
        setNotice('Registration successful. Please log in.')
        return
      }

      const profileResponse = await fetch(`${apiUrl}/auth/me`, {
        headers: {
          Authorization: `Bearer ${data.access_token}`,
        },
      })

      const user = await profileResponse.json()

      if (!profileResponse.ok) {
        throw new Error(user.detail || 'Could not load your profile.')
      }

      onAuthenticated({
        token: data.access_token,
        user,
      })
    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="auth-panel">
      <div className="auth-heading">
        <div>
          <p className="eyebrow">CHRONOSMATCH ACCOUNT</p>
          <h2>{mode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
          <p className="subtitle">
            {mode === 'login'
              ? 'Log in to access your trading account.'
              : 'Register to get started with ChronosMatch.'}
          </p>
        </div>

        <button type="button" className="auth-close" onClick={onClose}>
          Close
        </button>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        {mode === 'register' && (
          <label>
            Username
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              minLength={3}
              maxLength={100}
              required
              autoComplete="username"
              placeholder="Enter your username"
            />
          </label>
        )}

        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            placeholder="Enter your email"
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            maxLength={72}
            required
            autoComplete={
              mode === 'login' ? 'current-password' : 'new-password'
            }
            placeholder="Enter your password"
          />
        </label>

        {error && <p className="auth-error" role="alert">{error}</p>}
        {notice && <p className="auth-success" role="status">{notice}</p>}

        <button type="submit" className="auth-submit" disabled={loading}>
          {loading
            ? 'Please wait...'
            : mode === 'login'
              ? 'Log In'
              : 'Create Account'}
        </button>
      </form>

      <p className="auth-switch">
        {mode === 'login'
          ? "Don't have an account?"
          : 'Already have an account?'}{' '}
        <button
          type="button"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login')
            setError('')
            setNotice('')
          }}
        >
          {mode === 'login' ? 'Register' : 'Log In'}
        </button>
      </p>
    </section>
  )
}
