import { useEffect, useState } from 'react'

type User = {
  id: number
  email: string
  full_name: string
  role: string
}

type LeaveRequest = {
  leave_type: string
  start_date: string
  end_date: string
  reason: string
}

const defaultLeaveForm: LeaveRequest = {
  leave_type: 'Medical',
  start_date: '2026-10-15',
  end_date: '2026-10-17',
  reason: 'Need a medical consultation and rest.',
}

const featureCards = [
  {
    title: 'Leave Desk',
    description: 'AI-assisted leave review with structured validation and staff oversight.',
  },
  {
    title: 'Lost & Found',
    description: 'Match campus items using similarity, category, and date proximity.',
  },
  {
    title: 'Marketplace',
    description: 'List and discover secondhand essentials across campus communities.',
  },
]

function App() {
  const [token, setToken] = useState('')
  const [user, setUser] = useState<User | null>(null)
  const [dashboard, setDashboard] = useState<any>(null)
  const [leaveForm, setLeaveForm] = useState<LeaveRequest>(defaultLeaveForm)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [registerForm, setRegisterForm] = useState({ email: 'student2@example.com', password: 'campus123', full_name: 'Ava Singh' })
  const [loginForm, setLoginForm] = useState({ email: 'student@campusos.edu', password: 'campus123' })
  const [listingForm, setListingForm] = useState({ title: 'Used Engineering Calculator', description: 'Working calculator with new battery.', category: 'Electronics', condition: 'Good', price: 1200 })

  const apiBase = 'http://localhost:8000'

  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }
    fetch(`${apiBase}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setUser(data))
      .catch(() => setUser(null))
    fetch(`${apiBase}/api/dashboard/summary`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setDashboard(data))
      .catch(() => setDashboard(null))
  }, [token])

  const handleLogin = async () => {
    setError('')
    const response = await fetch(`${apiBase}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(loginForm),
    })
    const data = await response.json()
    if (!response.ok) {
      setError(data.detail || 'Login failed')
      return
    }
    setToken(data.access_token)
    setStatus('Logged in successfully')
  }

  const handleRegister = async () => {
    setError('')
    const response = await fetch(`${apiBase}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(registerForm),
    })
    const data = await response.json()
    if (!response.ok) {
      setError(data.detail || 'Registration failed')
      return
    }
    setStatus(`Registered ${data.email} successfully`) 
  }

  const handleLeaveSubmit = async () => {
    setError('')
    const response = await fetch(`${apiBase}/api/leaves`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(leaveForm),
    })
    const data = await response.json()
    if (!response.ok) {
      setError(data.detail || 'Unable to create leave application')
      return
    }
    const validated = await fetch(`${apiBase}/api/leaves/${data.id}/validate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    const result = await validated.json()
    if (!validated.ok) {
      setError(result.detail || 'Validation failed')
      return
    }
    setStatus(`Leave validated: ${result.validation.status}`)
  }

  const handleListingSubmit = async () => {
    setError('')
    const response = await fetch(`${apiBase}/api/listings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(listingForm),
    })
    const data = await response.json()
    if (!response.ok) {
      setError(data.detail || 'Listing failed')
      return
    }
    setStatus(`Marketplace listing created: ${data.id}`)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="bg-white/80 backdrop-blur sticky top-0 z-20 border-b border-slate-200">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white">C</div>
            <div>
              <div className="text-lg font-semibold">CampusOS</div>
              <div className="text-xs text-slate-500">Your campus. Connected. Simplified.</div>
            </div>
          </div>
          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a href="#features">Features</a>
            <a href="#dashboard">Dashboard</a>
            <a href="#workflow">Workflow</a>
            <a href="#demo">Demo</a>
          </nav>
          <button className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500">
            {user ? `Hi, ${user.full_name}` : 'Get Started'}
          </button>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-7xl gap-10 px-6 py-16 md:grid-cols-2 md:py-20">
          <div className="space-y-8">
            <span className="inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.15em] text-indigo-700">Student Operations Suite</span>
            <div className="space-y-4">
              <h1 className="text-4xl font-bold tracking-tight text-slate-900 md:text-6xl">Campus life made easier with AI-assisted decisions.</h1>
              <p className="max-w-xl text-lg text-slate-600">CampusOS brings leave requests, lost-item matching, and student listings into one transparent workflow powered by deterministic validation and human oversight.</p>
            </div>
            <div className="flex flex-wrap gap-4">
              <button className="rounded-full bg-indigo-600 px-6 py-3 font-medium text-white shadow-lg shadow-indigo-200 hover:bg-indigo-500">Get Started</button>
              <button className="rounded-full border border-slate-300 bg-white px-6 py-3 font-medium text-slate-700 hover:border-slate-400">Explore Features</button>
            </div>
            <div className="flex gap-8 pt-2 text-sm text-slate-500">
              <div><span className="font-bold text-slate-900">3</span> modules</div>
              <div><span className="font-bold text-slate-900">24/7</span> visibility</div>
              <div><span className="font-bold text-slate-900">Human</span> review</div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <div className="text-sm text-slate-500">Overview</div>
                <div className="text-2xl font-semibold">Student dashboard</div>
              </div>
              <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">Live demo</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-2xl bg-indigo-50 p-4">
                <div className="text-sm text-slate-500">Leaves</div>
                <div className="mt-1 text-3xl font-bold text-indigo-700">{dashboard?.total_leaves ?? 6}</div>
              </div>
              <div className="rounded-2xl bg-violet-50 p-4">
                <div className="text-sm text-slate-500">Matches</div>
                <div className="mt-1 text-3xl font-bold text-violet-700">{dashboard?.total_items ?? 8}</div>
              </div>
              <div className="rounded-2xl bg-sky-50 p-4">
                <div className="text-sm text-slate-500">Listings</div>
                <div className="mt-1 text-3xl font-bold text-sky-700">{dashboard?.marketplace_listings ?? 12}</div>
              </div>
              <div className="rounded-2xl bg-amber-50 p-4">
                <div className="text-sm text-slate-500">Alerts</div>
                <div className="mt-1 text-3xl font-bold text-amber-700">{dashboard?.notifications ?? 3}</div>
              </div>
            </div>
            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="mb-3 flex items-center justify-between text-sm font-medium text-slate-600">
                <span>AI validation status</span>
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">Passed</span>
              </div>
              <div className="space-y-2 text-sm text-slate-600">
                <div className="flex justify-between"><span>Date consistency</span><span className="text-emerald-600">Passed</span></div>
                <div className="flex justify-between"><span>Reason quality</span><span className="text-emerald-600">Passed</span></div>
                <div className="flex justify-between"><span>Staff review</span><span className="text-amber-600">Required</span></div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-6 pb-16">
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold text-slate-900">Built for every campus workflow</h2>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {featureCards.map((feature) => (
              <div key={feature.title} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-100 text-xl text-indigo-700">✦</div>
                <h3 className="mb-2 text-xl font-semibold text-slate-900">{feature.title}</h3>
                <p className="text-slate-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="dashboard" className="mx-auto max-w-7xl px-6 py-10">
          <div className="grid gap-8 lg:grid-cols-3">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
              <h3 className="mb-4 text-2xl font-semibold text-slate-900">Smart Leave Desk</h3>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-sm font-medium text-slate-700">Leave type
                  <input value={leaveForm.leave_type} onChange={(e) => setLeaveForm({ ...leaveForm, leave_type: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2" />
                </label>
                <label className="text-sm font-medium text-slate-700">Emergency contact
                  <input value={leaveForm.reason} onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2" />
                </label>
                <label className="text-sm font-medium text-slate-700">Start date
                  <input type="date" value={leaveForm.start_date} onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2" />
                </label>
                <label className="text-sm font-medium text-slate-700">End date
                  <input type="date" value={leaveForm.end_date} onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2" />
                </label>
              </div>
              <label className="mt-4 block text-sm font-medium text-slate-700">Reason
                <textarea value={leaveForm.reason} onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })} className="mt-2 min-h-28 w-full rounded-xl border border-slate-300 px-3 py-2" />
              </label>
              <button onClick={handleLeaveSubmit} className="mt-4 rounded-full bg-indigo-600 px-5 py-3 font-medium text-white">Validate leave</button>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-2xl font-semibold text-slate-900">Demo Login</h3>
              {!token ? (
                <div className="space-y-3">
                  <div className="space-y-3 border-b border-slate-200 pb-3">
                    <input value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Email" />
                    <input value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Password" type="password" />
                    <button onClick={handleLogin} className="w-full rounded-xl bg-slate-900 px-4 py-2.5 font-medium text-white">Login</button>
                  </div>
                  <div className="space-y-3">
                    <input value={registerForm.full_name} onChange={(e) => setRegisterForm({ ...registerForm, full_name: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Full name" />
                    <input value={registerForm.email} onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="New email" />
                    <input value={registerForm.password} onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Password" type="password" />
                    <button onClick={handleRegister} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 font-medium text-slate-700">Register</button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 text-sm text-slate-600">
                  <div className="rounded-xl bg-indigo-50 p-3 text-indigo-700">Logged in as {user?.full_name}</div>
                  <div className="rounded-xl bg-slate-50 p-3">Role: {user?.role}</div>
                  <button onClick={() => setToken('')} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5">Logout</button>
                </div>
              )}
              {status && <div className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{status}</div>}
              {error && <div className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}
            </div>
          </div>
        </section>

        <section id="workflow" className="mx-auto max-w-7xl px-6 py-10">
          <div className="grid gap-8 md:grid-cols-2">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-2xl font-semibold text-slate-900">AI Lost & Found</h3>
              <div className="space-y-3">
                <input className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Item title" defaultValue="Black scientific calculator" />
                <input className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Category" defaultValue="Electronics" />
                <input className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Location" defaultValue="Library" />
                <button className="rounded-full bg-violet-600 px-5 py-3 font-medium text-white">Check potential matches</button>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-2xl font-semibold text-slate-900">ReUse Marketplace</h3>
              <div className="space-y-3">
                <input value={listingForm.title} onChange={(e) => setListingForm({ ...listingForm, title: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Listing title" />
                <input value={listingForm.category} onChange={(e) => setListingForm({ ...listingForm, category: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Category" />
                <input type="number" value={listingForm.price} onChange={(e) => setListingForm({ ...listingForm, price: Number(e.target.value) })} className="w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Price" />
                <button onClick={handleListingSubmit} className="rounded-full bg-emerald-600 px-5 py-3 font-medium text-white">List item</button>
              </div>
            </div>
          </div>
        </section>

        <section id="demo" className="mx-auto max-w-7xl px-6 py-16 pb-24">
          <div className="rounded-3xl border border-indigo-200 bg-indigo-600 p-8 text-white shadow-lg shadow-indigo-200/60">
            <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-sm uppercase tracking-[0.2em] text-indigo-100">Demo ready</div>
                <h3 className="mt-2 text-3xl font-bold">Test the full workflow using student and staff accounts.</h3>
              </div>
              <div className="flex gap-3">
                <button className="rounded-full bg-white px-5 py-3 font-medium text-indigo-700">Use student demo</button>
                <button className="rounded-full border border-indigo-300 bg-indigo-500 px-5 py-3 font-medium text-white">Use staff demo</button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-8 text-sm text-slate-500 md:flex-row md:items-center md:justify-between">
          <div>© 2026 CampusOS</div>
          <div className="flex gap-6">
            <span>About</span>
            <span>Help</span>
            <span>Privacy</span>
            <span>Contact</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
