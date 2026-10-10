import { useCallback, useEffect, useState } from 'react'

type ForecastResult = {
  expected_visitors: number
  peak_window: { from: string; to: string; expected_arrivals: number }
  arrival_curve: { time: string; expected_arrivals: number; estimated_wait_minutes: number }[]
  recommendations: { arrival_time: string; estimated_wait_minutes: number; reason: string }[]
  confidence: string
  data_label: string
}

type Teammate = {
  user_id: number
  name: string
  skills: string[]
  availability: string
  score: number
  reasons: string[]
  starter: string
}

type AgendaItem = { title: string; starts_at: string; ends_at: string }
type CampusEvent = {
  id: number
  title: string
  description?: string
  starts_at: string
  ends_at: string
  agenda: AgendaItem[]
}
type Gig = {
  id: number
  title: string
  description: string
  category: string
  location: string
  price: number
}
type User = { id: number; email: string; full_name: string; role: string }
type LeaveRecord = {
  id: number
  leave_type: string
  start_date: string
  end_date: string
  reason: string
  status: string
  reviewer_note?: string | null
  validation_report?: { checks?: { check_name: string; status: string; explanation: string }[] } | null
}
type CampusItem = {
  id: number
  title: string
  description: string
  category: string
  location: string
  item_type: 'lost' | 'found'
  status: string
  date_seen: string
}
type PossibleMatch = { title: string; category: string; location: string; score: number; reason: string }
type MarketplaceListing = {
  id: number
  user_id: number
  title: string
  description: string
  category: string
  condition: string
  price: number
  status: string
  seller_name?: string
}
type NotificationItem = {
  id: number
  title: string
  message: string
  type: string
  read: boolean
  created_at: string
}
type ItemClaim = { id: number; item_id: number; claimant_id: number; title: string; status: string }
type ListingReportItem = { id: number; listing_id: number; listing_title: string; reason: string; status: string }

const featureCards = [
  { name: 'SmartFlow', detail: 'Anticipate campus rushes and compare quieter arrival windows.', href: '#smartflow', tone: 'bg-indigo-100 text-indigo-700', icon: '↗' },
  { name: 'QuietCollab', detail: 'Meet project teammates by skills and shared interests, without cold networking.', href: '#quietcollab', tone: 'bg-violet-100 text-violet-700', icon: '◎' },
  { name: 'HackaSync', detail: 'Turn event timing into a practical agenda with buffers and milestones.', href: '#hackasync', tone: 'bg-sky-100 text-sky-700', icon: '◷' },
  { name: 'PocketPal', detail: 'Offer and find small campus gigs with clear terms and locations.', href: '#pocketpal', tone: 'bg-emerald-100 text-emerald-700', icon: '↔' },
  { name: 'Leave Desk', detail: 'Submit a leave request, review deterministic checks, and track staff decisions.', href: '#leave-desk', tone: 'bg-amber-100 text-amber-700', icon: '✓' },
  { name: 'Lost & Found', detail: 'Report lost or found belongings and explore possible matches safely.', href: '#lost-found', tone: 'bg-rose-100 text-rose-700', icon: '⌕' },
  { name: 'ReUse Market', detail: 'Browse student listings and manage interest or listing status.', href: '#reuse-market', tone: 'bg-cyan-100 text-cyan-700', icon: '↗' },
]

const initialForecast = {
  class_end_time: '13:00',
  students_finishing: 200,
  visit_probability: 0.7,
  average_walk_minutes: 6,
  walk_time_spread_minutes: 3,
  forecast_minutes: 30,
  counters: [
    { name: 'North counter', service_rate_per_minute: 0.8 },
    { name: 'Cafe counter', service_rate_per_minute: 0.7 },
    { name: 'Express counter', service_rate_per_minute: 0.9 },
  ],
}

const initialProfile = {
  skills: 'Python, Machine learning',
  interests: 'AI, Climate tech',
  availability: 'Weekends',
  project_goal: 'Build an AI campus assistant',
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('campusone-token') ?? '')
  const [user, setUser] = useState<User | null>(null)
  const [dashboard, setDashboard] = useState<{ total_leaves: number; approved_leaves: number; pending_reviews: number; total_items: number; marketplace_listings: number; notifications: number } | null>(null)
  const [loginForm, setLoginForm] = useState({ email: 'student@campusos.edu', password: 'campus123' })
  const [registration, setRegistration] = useState({ email: '', password: '', full_name: '' })
  const [forecastForm, setForecastForm] = useState(initialForecast)
  const [forecast, setForecast] = useState<ForecastResult | null>(null)
  const [profileForm, setProfileForm] = useState(initialProfile)
  const [teammates, setTeammates] = useState<Teammate[]>([])
  const [eventForm, setEventForm] = useState({
    title: 'Campus Build Weekend',
    description: 'A student hackathon and project showcase.',
    starts_at: '2026-11-14T09:00',
    ends_at: '2026-11-14T18:00',
    setup_minutes: 30,
    break_minutes: 20,
    judging_minutes: 60,
    submission_minutes_before_end: 30,
  })
  const [events, setEvents] = useState<CampusEvent[]>([])
  const [gigForm, setGigForm] = useState({
    title: 'Pick up printed notes',
    description: 'Collect a print order from the campus shop this afternoon.',
    category: 'Errand',
    location: 'Main quad',
    price: 40,
  })
  const [gigs, setGigs] = useState<Gig[]>([])
  const [leaves, setLeaves] = useState<LeaveRecord[]>([])
  const [items, setItems] = useState<CampusItem[]>([])
  const [possibleMatches, setPossibleMatches] = useState<PossibleMatch[]>([])
  const [listings, setListings] = useState<MarketplaceListing[]>([])
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [staffReviews, setStaffReviews] = useState<LeaveRecord[]>([])
  const [leaveForm, setLeaveForm] = useState({ leave_type: 'Medical', start_date: '', end_date: '', reason: '', emergency_contact: '' })
  const [itemForm, setItemForm] = useState({ title: '', description: '', category: 'Electronics', location: '', date_seen: '', item_type: 'lost' as 'lost' | 'found' })
  const [listingForm, setListingForm] = useState({ title: '', description: '', category: 'Books', condition: 'Good', price: 0 })
  const [marketCategory, setMarketCategory] = useState('All')
  const [reviewComments, setReviewComments] = useState<Record<number, string>>({})
  const [claimResponses, setClaimResponses] = useState<Record<number, string>>({})
  const [itemClaims, setItemClaims] = useState<ItemClaim[]>([])
  const [listingReports, setListingReports] = useState<ListingReportItem[]>([])
  const [listingEditId, setListingEditId] = useState<number | null>(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const requestJson = useCallback(async <T,>(
    path: string,
    options: { method?: string; body?: string } = {},
  ): Promise<T> => {
    const headers: Record<string, string> = {}
    if (options.body) headers['Content-Type'] = 'application/json'
    if (token) headers.Authorization = `Bearer ${token}`
    const response = await fetch(path, { ...options, headers })
    const data: unknown = await response.json()
    if (!response.ok) {
      const message = typeof data === 'object' && data !== null && 'detail' in data
        ? String(data.detail)
        : `Request failed (${response.status})`
      throw new Error(message)
    }
    return data as T
  }, [token])

  const perform = async (action: () => Promise<void>) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The request failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const requireSignIn = () => {
    if (!token) throw new Error('Sign in to a student or staff demo account to use this feature.')
  }

  useEffect(() => {
    if (!token) return
    requestJson<User>('/api/auth/me')
      .then(setUser)
      .catch((reason: Error) => {
        setError(reason.message)
        setUser(null)
        setToken('')
        localStorage.removeItem('campusone-token')
      })
  }, [token, requestJson])

  useEffect(() => {
    requestJson<CampusEvent[]>('/api/hackasync/events').then(setEvents).catch((reason: Error) => setError(reason.message))
    requestJson<Gig[]>('/api/pocketpal/gigs').then(setGigs).catch((reason: Error) => setError(reason.message))
    requestJson<CampusItem[]>('/api/items').then(setItems).catch((reason: Error) => setError(reason.message))
    requestJson<MarketplaceListing[]>('/api/listings').then(setListings).catch((reason: Error) => setError(reason.message))
  }, [requestJson])

  useEffect(() => {
    if (!token) {
      setLeaves([])
      setNotifications([])
      setStaffReviews([])
      return
    }
    requestJson<LeaveRecord[]>('/api/leaves').then(setLeaves).catch((reason: Error) => setError(reason.message))
    requestJson<NotificationItem[]>('/api/notifications').then(setNotifications).catch((reason: Error) => setError(reason.message))
    requestJson<{ total_leaves: number; approved_leaves: number; pending_reviews: number; total_items: number; marketplace_listings: number; notifications: number }>('/api/dashboard/summary')
      .then(setDashboard)
      .catch((reason: Error) => setError(reason.message))
  }, [token, requestJson])

  useEffect(() => {
    if (!token || user?.role !== 'staff') {
      setStaffReviews([])
      setItemClaims([])
      setListingReports([])
      return
    }
    requestJson<LeaveRecord[]>('/api/admin/reviews').then(setStaffReviews).catch((reason: Error) => setError(reason.message))
    requestJson<ItemClaim[]>('/api/admin/item-claims').then(setItemClaims).catch((reason: Error) => setError(reason.message))
    requestJson<ListingReportItem[]>('/api/admin/listing-reports').then(setListingReports).catch((reason: Error) => setError(reason.message))
  }, [token, user?.role, requestJson])

  const login = () => perform(async () => {
    const result = await requestJson<{ access_token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(loginForm),
    })
    localStorage.setItem('campusone-token', result.access_token)
    setToken(result.access_token)
    setNotice('Signed in to the student demo.')
  })

  const register = () => perform(async () => {
    await requestJson('/api/auth/register', { method: 'POST', body: JSON.stringify(registration) })
    setNotice('Account created. Sign in with your new account.')
    setLoginForm({ email: registration.email, password: registration.password })
  })

  const calculateForecast = () => perform(async () => {
    const result = await requestJson<ForecastResult>('/api/smartflow/forecast', {
      method: 'POST',
      body: JSON.stringify(forecastForm),
    })
    setForecast(result)
    setNotice('Forecast calculated using the assumptions shown.')
  })

  const saveProfile = () => perform(async () => {
    requireSignIn()
    await requestJson('/api/quietcollab/profile', {
      method: 'PUT',
      body: JSON.stringify({
        ...profileForm,
        skills: profileForm.skills.split(',').map((item) => item.trim()).filter(Boolean),
        interests: profileForm.interests.split(',').map((item) => item.trim()).filter(Boolean),
      }),
    })
    setNotice('Your teammate profile is saved.')
  })

  const findTeammates = () => perform(async () => {
    requireSignIn()
    const result = await requestJson<{ matches: Teammate[] }>('/api/quietcollab/matches')
    setTeammates(result.matches)
    setNotice(`Found ${result.matches.length} profile match${result.matches.length === 1 ? '' : 'es'}.`)
  })

  const createEvent = () => perform(async () => {
    requireSignIn()
    const result = await requestJson<CampusEvent>('/api/hackasync/events', {
      method: 'POST',
      body: JSON.stringify(eventForm),
    })
    setEvents((previous) => [...previous, result].sort((a, b) => a.starts_at.localeCompare(b.starts_at)))
    setNotice('Event saved with its generated schedule.')
  })

  const createGig = () => perform(async () => {
    requireSignIn()
    await requestJson('/api/pocketpal/gigs', { method: 'POST', body: JSON.stringify(gigForm) })
    setGigs(await requestJson<Gig[]>('/api/pocketpal/gigs'))
    setNotice('Your gig is now open to campus.')
  })

  const createLeave = () => perform(async () => {
    requireSignIn()
    const created = await requestJson<{ id: number }>('/api/leaves', { method: 'POST', body: JSON.stringify(leaveForm) })
    const validation = await requestJson<{ validation: { status: string } }>(`/api/leaves/${created.id}/validate`, { method: 'POST' })
    setLeaves(await requestJson<LeaveRecord[]>('/api/leaves'))
    setNotice(`Application checked. Current status: ${validation.validation.status}. Approval still requires staff review.`)
    setLeaveForm({ ...leaveForm, reason: '' })
  })

  const withdrawLeave = (leaveId: number) => perform(async () => {
    requireSignIn()
    await requestJson(`/api/leaves/${leaveId}/withdraw`, { method: 'POST' })
    setLeaves(await requestJson<LeaveRecord[]>('/api/leaves'))
    setNotice('Leave application withdrawn.')
  })

  const reviewLeave = (leaveId: number, decision: 'approved' | 'rejected') => perform(async () => {
    if (user?.role !== 'staff') throw new Error('Sign in with the authorized staff demo to review leave requests.')
    const comments = reviewComments[leaveId]?.trim()
    if (!comments) throw new Error('Add a review comment before recording this decision.')
    await requestJson(`/api/leaves/${leaveId}/review?decision=${decision}&comments=${encodeURIComponent(comments)}`, { method: 'POST' })
    setStaffReviews(await requestJson<LeaveRecord[]>('/api/admin/reviews'))
    setNotice(`Review recorded: ${decision}.`)
  })

  const reportCampusItem = () => perform(async () => {
    requireSignIn()
    const endpoint = itemForm.item_type === 'lost' ? '/api/items/lost' : '/api/items/found'
    const result = await requestJson<{ id: number; potential_matches?: PossibleMatch[] }>(endpoint, { method: 'POST', body: JSON.stringify(itemForm) })
    setItems(await requestJson<CampusItem[]>('/api/items'))
    setPossibleMatches(result.potential_matches ?? [])
    setNotice(itemForm.item_type === 'lost' ? `${result.potential_matches?.length ?? 0} possible match(es) checked. Similarity is not proof of ownership.` : 'Found item report submitted.')
    setItemForm({ ...itemForm, title: '', description: '' })
  })

  const createMarketplaceListing = () => perform(async () => {
    requireSignIn()
    if (listingEditId) {
      await requestJson(`/api/listings/${listingEditId}`, { method: 'PATCH', body: JSON.stringify(listingForm) })
      setListingEditId(null)
    } else {
      await requestJson('/api/listings', { method: 'POST', body: JSON.stringify(listingForm) })
    }
    setListings(await requestJson<MarketplaceListing[]>('/api/listings'))
    setNotice('Marketplace listing saved. Payment and exchange happen outside this demo.')
    setListingForm({ ...listingForm, title: '', description: '' })
  })

  const updateListingStatus = (listingId: number, status: 'active' | 'reserved' | 'sold') => perform(async () => {
    requireSignIn()
    await requestJson(`/api/listings/${listingId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) })
    setListings(await requestJson<MarketplaceListing[]>('/api/listings'))
  })

  const deleteListing = (listingId: number) => perform(async () => {
    requireSignIn()
    await requestJson(`/api/listings/${listingId}`, { method: 'DELETE' })
    setListings(await requestJson<MarketplaceListing[]>('/api/listings'))
    setNotice('Listing deleted.')
  })

  const reportListing = (listingId: number) => perform(async () => {
    requireSignIn()
    const reason = window.prompt('Why are you reporting this listing?')
    if (!reason) return
    await requestJson(`/api/listings/${listingId}/report`, { method: 'POST', body: JSON.stringify({ reason }) })
    setNotice('Report sent for moderator review.')
  })

  const submitItemClaim = (itemId: number) => perform(async () => {
    requireSignIn()
    const verification_response = claimResponses[itemId]?.trim()
    if (!verification_response) throw new Error('Add a private detail only the true owner would know.')
    await requestJson(`/api/items/${itemId}/claim`, { method: 'POST', body: JSON.stringify({ verification_response }) })
    setClaimResponses({ ...claimResponses, [itemId]: '' })
    setNotice('Claim submitted privately for staff verification.')
  })

  const resolveClaim = (itemId: number, claimId: number) => perform(async () => {
    if (user?.role !== 'staff') throw new Error('Staff access is required.')
    await requestJson(`/api/items/${itemId}/resolve?claim_id=${claimId}`, { method: 'POST' })
    setItems(await requestJson<CampusItem[]>('/api/items'))
    setItemClaims(await requestJson<ItemClaim[]>('/api/admin/item-claims'))
    setNotice('Claim verified and item marked returned.')
  })

  const moderateReport = (reportId: number, action: 'dismiss' | 'remove') => perform(async () => {
    if (user?.role !== 'staff') throw new Error('Staff access is required.')
    await requestJson(`/api/admin/listing-reports/${reportId}/moderate?action=${action}`, { method: 'POST' })
    setListingReports(await requestJson<ListingReportItem[]>('/api/admin/listing-reports'))
    setNotice(`Listing report ${action === 'remove' ? 'acted on' : 'dismissed'}.`)
  })

  const expressListingInterest = (listingId: number) => perform(async () => {
    requireSignIn()
    await requestJson(`/api/listings/${listingId}/interest?message=${encodeURIComponent('Interested in this item')}`, { method: 'POST' })
    setNotice('Interest sent to the seller.')
  })

  const markNotificationRead = (notificationId: number) => perform(async () => {
    requireSignIn()
    await requestJson(`/api/notifications/${notificationId}/read`, { method: 'PATCH' })
    setNotifications(await requestJson<NotificationItem[]>('/api/notifications'))
  })

  const setAuthToken = (value: string) => {
    setToken(value)
    if (!value) setUser(null)
    if (value) localStorage.setItem('campusone-token', value)
    else localStorage.removeItem('campusone-token')
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-5 py-4">
          <a href="#" className="flex shrink-0 items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white">C</span>
            <span><span className="block text-lg font-semibold leading-tight">CampusOne</span><span className="text-xs text-slate-500">Your campus, connected</span></span>
          </a>
          <nav className="hidden max-w-[58vw] items-center gap-4 overflow-x-auto text-sm font-medium text-slate-600 xl:flex">
            {featureCards.map((feature) => <a key={feature.name} href={feature.href} className="shrink-0 hover:text-indigo-700">{feature.name}</a>)}
          </nav>
          <a href="#account" className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">
            {user ? user.full_name : 'Demo sign in'}
          </a>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-7xl items-center gap-10 px-5 py-16 md:grid-cols-2 md:py-24">
          <div className="space-y-7">
            <span className="inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.15em] text-indigo-700">Intelligent campus life</span>
            <div className="space-y-4">
              <h1 className="text-4xl font-bold tracking-tight text-slate-950 md:text-6xl">Make your next campus move a better one.</h1>
              <p className="max-w-xl text-lg text-slate-600">CampusOne helps students navigate rush hour, find project teammates, stay on top of events, and lend a hand through campus gigs.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <a href="#smartflow" className="rounded-full bg-indigo-600 px-6 py-3 font-medium text-white shadow-lg shadow-indigo-200 hover:bg-indigo-500">Try SmartFlow</a>
              <a href="#features" className="rounded-full border border-slate-300 bg-white px-6 py-3 font-medium text-slate-700 hover:border-slate-400">Explore the ecosystem</a>
            </div>
            <p className="text-sm text-slate-500">Forecasts use explicit demo assumptions. Location access is not required.</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60">
            <div className="flex items-start justify-between gap-4">
              <div><p className="text-sm text-slate-500">SmartFlow • Cafeteria</p><h2 className="mt-1 text-2xl font-semibold text-slate-900">Plan around the rush</h2></div>
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">Illustrative</span>
            </div>
            <div className="mt-6 grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-indigo-50 p-4"><p className="text-sm text-slate-500">Expected visitors</p><p className="mt-1 text-3xl font-bold text-indigo-700">{forecast?.expected_visitors ?? '140'}</p></div>
              <div className="rounded-2xl bg-violet-50 p-4"><p className="text-sm text-slate-500">Class block ends</p><p className="mt-1 text-3xl font-bold text-violet-700">{forecastForm.class_end_time}</p></div>
            </div>
            <div className="mt-4 rounded-2xl border border-slate-200 p-4">
              <div className="mb-3 flex items-center justify-between text-sm"><span className="font-medium text-slate-700">Example arrival pattern</span><span className="text-xs text-slate-500">200 students × 70%</span></div>
              <div className="flex h-20 items-end gap-1.5" aria-label="Illustrative arrivals after a class block">
                {[18, 32, 54, 82, 100, 77, 55, 38, 26, 18, 12, 8].map((height, index) => <span key={index} className="flex-1 rounded-t bg-indigo-300" style={{ height: `${height}%` }} />)}
              </div>
              <div className="mt-2 flex justify-between text-xs text-slate-400"><span>1:00 PM</span><span>1:30 PM</span></div>
            </div>
            <p className="mt-4 text-xs text-slate-500">Sample values only—not live campus measurements.</p>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-5 pb-12">
          <div className="mb-7"><p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">One connected campus</p><h2 className="mt-2 text-3xl font-bold text-slate-950">Seven useful tools. Shared context.</h2></div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {featureCards.map((feature) => (
              <a href={feature.href} key={feature.name} className="rounded-2xl border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-md">
                <span className={`flex h-11 w-11 items-center justify-center rounded-xl text-xl font-semibold ${feature.tone}`}>{feature.icon}</span>
                <h3 className="mt-4 text-lg font-semibold text-slate-900">{feature.name}</h3><p className="mt-1 text-sm leading-6 text-slate-600">{feature.detail}</p>
              </a>
            ))}
          </div>
        </section>

        <section id="dashboard" className="mx-auto max-w-7xl px-5 pb-8">
          <div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">Your campus home</p><h2 className="mt-1 text-2xl font-bold text-slate-950">{user ? `Welcome, ${user.full_name.split(' ')[0]}` : 'A clearer view of campus life'}</h2></div><a href="#account" className="text-sm font-medium text-indigo-700 hover:underline">{user ? 'Account settings' : 'Sign in to personalize →'}</a></div>
              <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[['Leave requests', dashboard?.total_leaves ?? '—', 'text-amber-700'], ['Open items', dashboard?.total_items ?? items.length, 'text-rose-700'], ['Your listings', dashboard?.marketplace_listings ?? '—', 'text-cyan-700'], ['To review', user?.role === 'staff' ? staffReviews.length : dashboard?.pending_reviews ?? '—', 'text-violet-700']].map(([label, value, tone]) => <div key={label} className="rounded-2xl bg-slate-50 p-4"><p className="text-xs text-slate-500">{label}</p><p className={`mt-1 text-2xl font-bold ${tone}`}>{value}</p></div>)}
              </div>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between"><div><p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">Activity</p><h3 className="mt-1 text-lg font-bold text-slate-950">Recent notifications</h3></div><span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-800">{notifications.filter((item) => !item.read).length} unread</span></div>
              {!token && <p className="mt-4 text-sm text-slate-500">Sign in to view your notifications.</p>}
              <div className="mt-3 space-y-2">{notifications.slice(0, 3).map((item) => <button onClick={() => !item.read && markNotificationRead(item.id)} key={item.id} className="block w-full rounded-xl bg-slate-50 p-3 text-left hover:bg-indigo-50"><span className="flex items-center justify-between gap-2"><span className="text-sm font-medium text-slate-800">{item.title}</span>{!item.read && <span className="h-2 w-2 rounded-full bg-indigo-600" />}</span><span className="mt-1 block text-xs text-slate-600">{item.message}</span></button>)}</div>
              {token && !notifications.length && <p className="mt-3 text-sm text-slate-500">No notifications yet.</p>}
            </div>
          </div>
        </section>

        <section id="smartflow" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-10">
          <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">01 • Mobility</p><h2 className="mt-2 text-2xl font-bold text-slate-950">SmartFlow demand simulator</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">Use class end times, estimated visit share, walking time, and counter service rates. No GPS signals are collected by this demo.</p>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium text-slate-700">Class ends<input type="time" value={forecastForm.class_end_time} onChange={(e) => setForecastForm({ ...forecastForm, class_end_time: e.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="text-sm font-medium text-slate-700">Students finishing<input type="number" min="1" value={forecastForm.students_finishing} onChange={(e) => setForecastForm({ ...forecastForm, students_finishing: Number(e.target.value) })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="text-sm font-medium text-slate-700">Likely to visit (%)<input type="number" min="0" max="100" value={forecastForm.visit_probability * 100} onChange={(e) => setForecastForm({ ...forecastForm, visit_probability: Number(e.target.value) / 100 })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="text-sm font-medium text-slate-700">Average walk (min)<input type="number" min="1" value={forecastForm.average_walk_minutes} onChange={(e) => setForecastForm({ ...forecastForm, average_walk_minutes: Number(e.target.value) })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="text-sm font-medium text-slate-700">Walking-time spread (min)<input type="number" min="0" value={forecastForm.walk_time_spread_minutes} onChange={(e) => setForecastForm({ ...forecastForm, walk_time_spread_minutes: Number(e.target.value) })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="text-sm font-medium text-slate-700">Forecast horizon (min)<input type="number" min="10" value={forecastForm.forecast_minutes} onChange={(e) => setForecastForm({ ...forecastForm, forecast_minutes: Number(e.target.value) })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
              </div>
              <p className="mt-5 text-sm font-semibold text-slate-800">Service capacity per counter (visitors/min)</p>
              <div className="mt-2 grid gap-3 sm:grid-cols-3">
                {forecastForm.counters.map((counter, index) => (
                  <label key={counter.name} className="text-xs text-slate-600">{counter.name}<input type="number" min="0.1" step="0.1" value={counter.service_rate_per_minute} onChange={(e) => setForecastForm({ ...forecastForm, counters: forecastForm.counters.map((item, itemIndex) => itemIndex === index ? { ...item, service_rate_per_minute: Number(e.target.value) } : item) })} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm" /></label>
                ))}
              </div>
              <button onClick={calculateForecast} disabled={busy} className="mt-5 rounded-full bg-indigo-600 px-5 py-2.5 font-medium text-white hover:bg-indigo-500 disabled:opacity-50">{busy ? 'Calculating…' : 'Calculate forecast'}</button>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between"><div><p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">Forecast output</p><h3 className="mt-2 text-xl font-bold text-slate-950">Arrival windows and estimated waits</h3></div><span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">{forecast?.confidence ?? 'low confidence'}</span></div>
              {!forecast ? <div className="mt-6 rounded-2xl bg-slate-50 p-5 text-sm leading-6 text-slate-600">Run the simulator to see expected visitor arrivals and illustrative queue estimates. The numerical forecast is deterministic; the language model does not create its statistics.</div> : (
                <>
                  <p className="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">{forecast.data_label}</p>
                  <div className="mt-5 flex h-40 items-end gap-1.5 border-b border-slate-200 pb-2">
                    {forecast.arrival_curve.map((point) => {
                      const max = Math.max(1, ...forecast.arrival_curve.map((item) => item.expected_arrivals))
                      return <div key={point.time} className="flex h-full flex-1 flex-col justify-end" title={`${point.time}: ${point.expected_arrivals} expected arrivals, ${point.estimated_wait_minutes} min wait`}><span className="mb-1 text-center text-[10px] text-slate-500">{point.expected_arrivals}</span><span className="rounded-t bg-indigo-500" style={{ height: `${Math.max(4, point.expected_arrivals / max * 75)}%` }} /></div>
                    })}
                  </div>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {forecast.recommendations.map((item) => <div key={item.arrival_time} className="rounded-xl bg-emerald-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Suggested arrival</p><p className="mt-1 text-xl font-bold text-emerald-900">{item.arrival_time}</p><p className="mt-1 text-sm text-emerald-800">~{item.estimated_wait_minutes} min wait</p></div>)}
                  </div>
                </>
              )}
            </div>
          </div>
        </section>

        <section id="quietcollab" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-10">
          <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-widest text-violet-600">02 • People</p><h2 className="mt-2 text-2xl font-bold text-slate-950">QuietCollab teammate finder</h2><p className="mt-2 text-sm leading-6 text-slate-600">Match on complementary skills, common interests, and a shared project goal. Profiles in this demo are visible to other students looking for teammates.</p>
              <div className="mt-5 space-y-4">
                <label className="block text-sm font-medium text-slate-700">Your skills, comma-separated<input value={profileForm.skills} onChange={(e) => setProfileForm({ ...profileForm, skills: e.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="block text-sm font-medium text-slate-700">Interests<input value={profileForm.interests} onChange={(e) => setProfileForm({ ...profileForm, interests: e.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="block text-sm font-medium text-slate-700">Project goal<input value={profileForm.project_goal} onChange={(e) => setProfileForm({ ...profileForm, project_goal: e.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="block text-sm font-medium text-slate-700">Availability<input value={profileForm.availability} onChange={(e) => setProfileForm({ ...profileForm, availability: e.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <div className="flex flex-wrap gap-3"><button onClick={saveProfile} disabled={busy} className="rounded-full bg-violet-600 px-5 py-2.5 font-medium text-white hover:bg-violet-500 disabled:opacity-50">Save profile</button><button onClick={findTeammates} disabled={busy} className="rounded-full border border-slate-300 px-5 py-2.5 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50">Find teammates</button></div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="rounded-3xl border border-violet-100 bg-violet-50 p-6"><p className="text-sm font-medium text-violet-800">Low-pressure by design</p><p className="mt-2 text-lg font-semibold text-slate-900">Browse suggestions first. Start a conversation only when you feel ready.</p><p className="mt-2 text-sm text-slate-600">Match scores are deterministic profile comparisons, not judgments about a person.</p></div>
              {teammates.map((person) => <article key={person.user_id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-start justify-between gap-3"><div><h3 className="font-semibold text-slate-900">{person.name}</h3><p className="mt-1 text-sm text-slate-500">Availability: {person.availability}</p></div><span className="rounded-full bg-violet-100 px-3 py-1 text-sm font-semibold text-violet-800">{person.score}% fit</span></div><div className="mt-3 flex flex-wrap gap-2">{person.skills.map((skill) => <span key={skill} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">{skill}</span>)}</div><ul className="mt-3 list-inside list-disc text-sm text-slate-600">{person.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul><p className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600">Optional opener: “{person.starter}”</p></article>)}
              {!teammates.length && <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">Save your profile, then discover sample teammates with complementary strengths.</div>}
            </div>
          </div>
        </section>

        <section id="hackasync" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-10">
          <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-widest text-sky-600">03 • Events</p><h2 className="mt-2 text-2xl font-bold text-slate-950">HackaSync event planner</h2><p className="mt-2 text-sm leading-6 text-slate-600">Create a schedule with setup, a kickoff, work blocks, a break, submission, and judging. Review the generated timings before sharing.</p>
              <div className="mt-5 space-y-3">
                <label className="block text-sm font-medium text-slate-700">Event name<input value={eventForm.title} onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="block text-sm font-medium text-slate-700">Description<input value={eventForm.description} onChange={(e) => setEventForm({ ...eventForm, description: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <div className="grid grid-cols-2 gap-3"><label className="text-sm font-medium text-slate-700">Starts<input type="datetime-local" value={eventForm.starts_at} onChange={(e) => setEventForm({ ...eventForm, starts_at: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-2 py-2" /></label><label className="text-sm font-medium text-slate-700">Ends<input type="datetime-local" value={eventForm.ends_at} onChange={(e) => setEventForm({ ...eventForm, ends_at: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-2 py-2" /></label></div>
                <button onClick={createEvent} disabled={busy} className="rounded-full bg-sky-600 px-5 py-2.5 font-medium text-white hover:bg-sky-500 disabled:opacity-50">Generate & save agenda</button>
              </div>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-widest text-sky-600">Event schedule</p><h3 className="mt-2 text-xl font-bold text-slate-950">Upcoming campus events</h3>
              <div className="mt-5 space-y-4">
                {events.map((event) => <article key={event.id} className="rounded-2xl border border-slate-200 p-4"><div className="flex flex-wrap items-baseline justify-between gap-2"><h4 className="font-semibold text-slate-900">{event.title}</h4><span className="text-sm text-slate-500">{new Date(event.starts_at).toLocaleDateString()}</span></div><div className="mt-4 space-y-2">{event.agenda.map((item) => <div key={`${event.id}-${item.title}`} className="flex gap-3 border-l-2 border-sky-200 pl-3"><span className="w-24 shrink-0 text-xs font-medium text-slate-500">{formatTime(item.starts_at)}–{formatTime(item.ends_at)}</span><span className="text-sm text-slate-700">{item.title}</span></div>)}</div></article>)}
                {!events.length && <p className="rounded-xl bg-slate-50 p-5 text-sm text-slate-500">No events scheduled yet. Create one to generate its timeline.</p>}
              </div>
            </div>
          </div>
        </section>

        <section id="pocketpal" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-10">
          <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-widest text-emerald-600">04 • Student services</p><h2 className="mt-2 text-2xl font-bold text-slate-950">PocketPal campus gigs</h2><p className="mt-2 text-sm leading-6 text-slate-600">Post small, permitted campus tasks or find someone offering help. Agree on details directly; this demo does not process payments.</p>
              <div className="mt-5 space-y-3">
                <label className="block text-sm font-medium text-slate-700">Gig title<input value={gigForm.title} onChange={(e) => setGigForm({ ...gigForm, title: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="block text-sm font-medium text-slate-700">Description<textarea value={gigForm.description} onChange={(e) => setGigForm({ ...gigForm, description: e.target.value })} className="mt-1 min-h-20 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <div className="grid grid-cols-2 gap-3"><label className="text-sm font-medium text-slate-700">Category<input value={gigForm.category} onChange={(e) => setGigForm({ ...gigForm, category: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label><label className="text-sm font-medium text-slate-700">Location<input value={gigForm.location} onChange={(e) => setGigForm({ ...gigForm, location: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label></div>
                <label className="block text-sm font-medium text-slate-700">Agreed fee (₹)<input type="number" min="0" value={gigForm.price} onChange={(e) => setGigForm({ ...gigForm, price: Number(e.target.value) })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <button onClick={createGig} disabled={busy} className="rounded-full bg-emerald-600 px-5 py-2.5 font-medium text-white hover:bg-emerald-500 disabled:opacity-50">Post campus gig</button>
              </div>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex items-center justify-between gap-4"><div><p className="text-sm font-semibold uppercase tracking-widest text-emerald-600">Campus board</p><h3 className="mt-2 text-xl font-bold text-slate-950">Open gigs</h3></div><span className="rounded-full bg-emerald-50 px-3 py-1 text-sm text-emerald-800">{gigs.length} open</span></div>
              <div className="mt-5 space-y-3">{gigs.map((gig) => <article key={gig.id} className="rounded-2xl border border-slate-200 p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><h4 className="font-semibold text-slate-900">{gig.title}</h4><p className="mt-1 text-sm text-slate-600">{gig.description}</p></div><span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-800">₹{gig.price}</span></div><div className="mt-3 flex gap-2 text-xs text-slate-500"><span>{gig.category}</span><span>•</span><span>{gig.location}</span></div></article>)}{!gigs.length && <p className="rounded-xl bg-slate-50 p-5 text-sm text-slate-500">No open gigs yet. Add the first campus task.</p>}</div>
            </div>
          </div>
        </section>

        <section id="leave-desk" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-10">
          <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-widest text-amber-600">05 • Student services</p>
              <h2 className="mt-2 text-2xl font-bold text-slate-950">Smart Leave Desk</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">Submit a request, run deterministic field/date checks, and track the designated human reviewer. Validation is not approval.</p>
              <div className="mt-5 space-y-3">
                <label className="block text-sm font-medium text-slate-700">Leave type<select value={leaveForm.leave_type} onChange={(e) => setLeaveForm({ ...leaveForm, leave_type: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2"><option>Medical</option><option>Personal</option><option>Academic</option><option>Emergency</option></select></label>
                <div className="grid grid-cols-2 gap-3"><label className="text-sm font-medium text-slate-700">Start date<input type="date" required value={leaveForm.start_date} onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label><label className="text-sm font-medium text-slate-700">End date<input type="date" required value={leaveForm.end_date} onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label></div>
                <label className="block text-sm font-medium text-slate-700">Reason<textarea minLength={10} required value={leaveForm.reason} onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })} className="mt-1 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Share the context needed to review your request" /></label>
                <label className="block text-sm font-medium text-slate-700">Emergency contact (optional)<input value={leaveForm.emergency_contact} onChange={(e) => setLeaveForm({ ...leaveForm, emergency_contact: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Phone or contact name" /></label>
                <button onClick={createLeave} disabled={busy} className="rounded-full bg-amber-600 px-5 py-2.5 font-medium text-white hover:bg-amber-500 disabled:opacity-50">Submit & validate</button>
              </div>
            </div>
            <div className="space-y-4">
              <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4 text-sm leading-6 text-amber-950"><strong>Human decision required.</strong> Demo policies and calendar data are simulated. AI or validation output cannot approve or reject leave.</div>
              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-center justify-between"><div><p className="text-sm font-semibold uppercase tracking-widest text-amber-600">Your applications</p><h3 className="mt-1 text-xl font-bold text-slate-950">Leave activity</h3></div><span className="rounded-full bg-amber-50 px-3 py-1 text-sm text-amber-800">{leaves.length} requests</span></div>
                {!token && <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">Sign in to see your private leave history and submit a request.</p>}
                <div className="mt-4 space-y-3">{leaves.map((leave) => <article key={leave.id} className="rounded-2xl border border-slate-200 p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><h4 className="font-semibold text-slate-900">{leave.leave_type} leave</h4><p className="mt-1 text-sm text-slate-500">{leave.start_date} to {leave.end_date}</p></div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">{leave.status}</span></div><p className="mt-3 text-sm text-slate-600">{leave.reason}</p>{leave.validation_report?.checks && <ul className="mt-3 space-y-1 text-xs text-slate-600">{leave.validation_report.checks.map((check) => <li key={check.check_name} className="flex justify-between gap-3"><span>{check.explanation}</span><span className="shrink-0 font-medium">{check.status}</span></li>)}</ul>}{leave.reviewer_note && <p className="mt-3 rounded-lg bg-slate-50 p-2 text-sm text-slate-600">Reviewer: {leave.reviewer_note}</p>}{!['Approved', 'Rejected', 'Withdrawn'].includes(leave.status) && <button onClick={() => withdrawLeave(leave.id)} className="mt-3 text-sm font-medium text-rose-700 hover:underline">Withdraw request</button>}</article>)}</div>
                {token && leaves.length === 0 && <p className="mt-4 text-sm text-slate-500">No requests yet. Your submitted applications will appear here.</p>}
              </div>
              {user?.role === 'staff' && <div className="rounded-3xl border border-indigo-200 bg-indigo-50 p-6"><p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">Staff review queue</p><h3 className="mt-1 text-xl font-bold text-slate-950">Human approval actions</h3><div className="mt-4 space-y-3">{staffReviews.map((leave) => <article key={leave.id} className="rounded-xl border border-indigo-100 bg-white p-4"><p className="font-semibold">{leave.leave_type} request · {leave.status}</p><p className="mt-1 text-sm text-slate-600">{leave.reason}</p><textarea aria-label={`Reviewer note for request ${leave.id}`} value={reviewComments[leave.id] ?? ''} onChange={(e) => setReviewComments({ ...reviewComments, [leave.id]: e.target.value })} placeholder="Required decision reason" className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /><div className="mt-2 flex gap-2"><button onClick={() => reviewLeave(leave.id, 'approved')} className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-medium text-white">Approve</button><button onClick={() => reviewLeave(leave.id, 'rejected')} className="rounded-full bg-rose-600 px-4 py-2 text-sm font-medium text-white">Reject</button></div></article>)}</div>{!staffReviews.length && <p className="mt-3 text-sm text-slate-600">No leave requests awaiting review.</p>}</div>}
            </div>
          </div>
        </section>

        <section id="lost-found" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-10">
          <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-widest text-rose-600">06 • Campus community</p><h2 className="mt-2 text-2xl font-bold text-slate-950">Lost & Found</h2><p className="mt-2 text-sm leading-6 text-slate-600">Post a report with approximate details. Potential matches are suggestions only; ownership requires a separate verification step.</p>
              <div className="mt-5 space-y-3">
                <label className="block text-sm font-medium text-slate-700">Report type<select value={itemForm.item_type} onChange={(e) => setItemForm({ ...itemForm, item_type: e.target.value as 'lost' | 'found' })} className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2"><option value="lost">I lost something</option><option value="found">I found something</option></select></label>
                <label className="block text-sm font-medium text-slate-700">Item title<input required value={itemForm.title} onChange={(e) => setItemForm({ ...itemForm, title: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="e.g. Black calculator" /></label>
                <label className="block text-sm font-medium text-slate-700">Description<textarea required minLength={10} value={itemForm.description} onChange={(e) => setItemForm({ ...itemForm, description: e.target.value })} className="mt-1 min-h-20 w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Visible characteristics only; keep private verification details private" /></label>
                <div className="grid grid-cols-2 gap-3"><label className="text-sm font-medium text-slate-700">Category<input value={itemForm.category} onChange={(e) => setItemForm({ ...itemForm, category: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label><label className="text-sm font-medium text-slate-700">Approx. location<input required value={itemForm.location} onChange={(e) => setItemForm({ ...itemForm, location: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" placeholder="Library" /></label></div>
                <label className="block text-sm font-medium text-slate-700">Approx. date<input type="date" required value={itemForm.date_seen} onChange={(e) => setItemForm({ ...itemForm, date_seen: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <button onClick={reportCampusItem} disabled={busy} className="rounded-full bg-rose-600 px-5 py-2.5 font-medium text-white hover:bg-rose-500 disabled:opacity-50">Submit report</button>
              </div>
              {possibleMatches.length > 0 && <div className="mt-5 rounded-2xl border border-rose-100 bg-rose-50 p-4"><h3 className="font-semibold text-rose-950">Possible matches — not proof of ownership</h3><div className="mt-3 space-y-2">{possibleMatches.map((match, index) => <div key={`${match.title}-${index}`} className="rounded-xl bg-white p-3"><div className="flex justify-between gap-3"><span className="font-medium text-slate-900">{match.title}</span><span className="text-sm text-rose-700">{match.score}%</span></div><p className="mt-1 text-sm text-slate-600">{match.reason}</p></div>)}</div></div>}
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-sm font-semibold uppercase tracking-widest text-rose-600">Campus board</p><h3 className="mt-1 text-xl font-bold text-slate-950">Recent reports</h3></div><span className="rounded-full bg-rose-50 px-3 py-1 text-sm text-rose-800">{items.length} reports</span></div>
              <div className="mt-4 space-y-3">{items.map((item) => <article key={item.id} className="rounded-2xl border border-slate-200 p-4"><div className="flex items-start justify-between gap-3"><div><h4 className="font-semibold text-slate-900">{item.title}</h4><p className="mt-1 text-sm text-slate-600">{item.description}</p></div><span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${item.item_type === 'lost' ? 'bg-rose-100 text-rose-800' : 'bg-sky-100 text-sky-800'}`}>{item.item_type}</span></div><div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500"><span>{item.category}</span><span>•</span><span>{item.location}</span><span>•</span><span>{item.date_seen}</span><span>•</span><span>{item.status}</span></div>{item.item_type === 'found' && item.status === 'open' && <div className="mt-3 rounded-xl bg-slate-50 p-3"><label className="block text-xs font-medium text-slate-700">Private ownership detail for staff verification<textarea value={claimResponses[item.id] ?? ''} onChange={(e) => setClaimResponses({ ...claimResponses, [item.id]: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Do not enter a serial number that was visible in the public report" /></label><button onClick={() => submitItemClaim(item.id)} disabled={busy || !token} className="mt-2 rounded-full border border-rose-600 px-4 py-2 text-sm font-medium text-rose-800 disabled:opacity-50">{token ? 'Request mediated handover' : 'Sign in to request a handover'}</button></div>}</article>)}</div>
              {!items.length && <p className="mt-4 text-sm text-slate-500">No reports available. Submit the first lost or found item.</p>}
            </div>
          </div>
        </section>

        <section id="reuse-market" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-10">
          <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-widest text-cyan-700">07 • Reuse</p><h2 className="mt-2 text-2xl font-bold text-slate-950">ReUse student marketplace</h2><p className="mt-2 text-sm leading-6 text-slate-600">List permitted secondhand items. Buyers express interest; payment and exchange happen outside the app.</p>
              <div className="mt-5 space-y-3">
                <label className="block text-sm font-medium text-slate-700">Listing title<input required value={listingForm.title} onChange={(e) => setListingForm({ ...listingForm, title: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="block text-sm font-medium text-slate-700">Description<textarea required minLength={10} value={listingForm.description} onChange={(e) => setListingForm({ ...listingForm, description: e.target.value })} className="mt-1 min-h-20 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <div className="grid grid-cols-2 gap-3"><label className="text-sm font-medium text-slate-700">Category<select value={listingForm.category} onChange={(e) => setListingForm({ ...listingForm, category: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2"><option>Books</option><option>Electronics</option><option>Lab equipment</option><option>Hostel supplies</option><option>Other permitted item</option></select></label><label className="text-sm font-medium text-slate-700">Condition<select value={listingForm.condition} onChange={(e) => setListingForm({ ...listingForm, condition: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2"><option>New</option><option>Like new</option><option>Good</option><option>Fair</option></select></label></div>
                <label className="block text-sm font-medium text-slate-700">Asking price (₹)<input type="number" min="0" value={listingForm.price} onChange={(e) => setListingForm({ ...listingForm, price: Number(e.target.value) })} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <div className="flex gap-2"><button onClick={createMarketplaceListing} disabled={busy} className="rounded-full bg-cyan-700 px-5 py-2.5 font-medium text-white hover:bg-cyan-600 disabled:opacity-50">{listingEditId ? 'Save changes' : 'Publish listing'}</button>{listingEditId && <button onClick={() => { setListingEditId(null); setListingForm({ title: '', description: '', category: 'Books', condition: 'Good', price: 0 }) }} className="rounded-full border border-slate-300 px-4 py-2.5 text-sm text-slate-700">Cancel edit</button>}</div>
              </div>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold uppercase tracking-widest text-cyan-700">Browse campus</p><h3 className="mt-1 text-xl font-bold text-slate-950">Available listings</h3></div><label className="text-sm text-slate-600">Filter category<select value={marketCategory} onChange={(e) => setMarketCategory(e.target.value)} className="ml-2 rounded-lg border border-slate-300 bg-white px-2 py-1.5"><option>All</option>{Array.from(new Set(listings.map((item) => item.category))).map((category) => <option key={category}>{category}</option>)}</select></label></div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">{listings.filter((listing) => marketCategory === 'All' || listing.category === marketCategory).map((listing) => <article key={listing.id} className="rounded-2xl border border-slate-200 p-4"><div className="flex items-start justify-between gap-2"><div><h4 className="font-semibold text-slate-900">{listing.title}</h4>{listing.seller_name && <p className="mt-1 text-xs text-slate-500">Listed by {listing.seller_name}</p>}</div><span className="shrink-0 rounded-full bg-cyan-50 px-2.5 py-1 text-sm font-semibold text-cyan-900">₹{listing.price}</span></div><p className="mt-2 line-clamp-3 text-sm text-slate-600">{listing.description}</p><div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500"><span>{listing.category}</span><span>•</span><span>{listing.condition}</span><span>•</span><span>{listing.status}</span></div><div className="mt-4 flex flex-wrap gap-2"><button onClick={() => expressListingInterest(listing.id)} disabled={busy || !token || listing.status !== 'active' || listing.user_id === user?.id} className="rounded-full border border-cyan-700 px-3 py-2 text-sm font-medium text-cyan-800 hover:bg-cyan-50 disabled:opacity-50">{listing.user_id === user?.id ? 'Your listing' : listing.status === 'active' ? 'I’m interested' : listing.status}</button>{listing.user_id === user?.id && <><button onClick={() => { setListingEditId(listing.id); setListingForm({ title: listing.title, description: listing.description, category: listing.category, condition: listing.condition, price: listing.price }); document.getElementById('reuse-market')?.scrollIntoView({ behavior: 'smooth' }) }} className="rounded-full border border-slate-300 px-3 py-2 text-sm">Edit</button><button onClick={() => updateListingStatus(listing.id, listing.status === 'reserved' ? 'active' : 'reserved')} className="rounded-full border border-slate-300 px-3 py-2 text-sm">{listing.status === 'reserved' ? 'Unreserve' : 'Reserve'}</button><button onClick={() => updateListingStatus(listing.id, 'sold')} className="rounded-full border border-slate-300 px-3 py-2 text-sm">Mark sold</button><button onClick={() => deleteListing(listing.id)} className="rounded-full border border-rose-300 px-3 py-2 text-sm text-rose-700">Delete</button></>}{listing.user_id !== user?.id && token && <button onClick={() => reportListing(listing.id)} className="rounded-full border border-rose-300 px-3 py-2 text-sm text-rose-700">Report</button>}</div></article>)}</div>
              {!listings.length && <p className="mt-4 text-sm text-slate-500">No marketplace listings yet.</p>}
            </div>
          </div>
        </section>

        <section id="account" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-10">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">Demo account</p><h2 className="mt-2 text-2xl font-bold text-slate-950">Save your CampusOne activity</h2><p className="mt-1 text-sm text-slate-600">Student demo: student@campusos.edu / campus123</p></div>{user && <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-800">Signed in as {user.full_name}</span>}</div>
            {!user ? <div className="mt-5 grid gap-5 md:grid-cols-2"><div className="space-y-3"><h3 className="font-semibold">Sign in</h3><input aria-label="Email" value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" /><input aria-label="Password" type="password" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" /><button onClick={login} disabled={busy} className="rounded-full bg-slate-900 px-5 py-2.5 font-medium text-white disabled:opacity-50">Sign in</button><div className="flex flex-wrap gap-2 text-xs"><button onClick={() => setLoginForm({ email: 'student@campusos.edu', password: 'campus123' })} className="rounded-full bg-slate-100 px-3 py-1.5 text-slate-700">Use student demo</button><button onClick={() => setLoginForm({ email: 'staff@campusos.edu', password: 'campus123' })} className="rounded-full bg-indigo-100 px-3 py-1.5 text-indigo-800">Use staff demo</button></div></div><div className="space-y-3"><h3 className="font-semibold">Create student account</h3><input aria-label="Full name" placeholder="Full name" value={registration.full_name} onChange={(e) => setRegistration({ ...registration, full_name: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" /><input aria-label="Registration email" placeholder="Email" type="email" value={registration.email} onChange={(e) => setRegistration({ ...registration, email: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" /><input aria-label="Registration password" placeholder="Password" type="password" value={registration.password} onChange={(e) => setRegistration({ ...registration, password: e.target.value })} className="w-full rounded-xl border border-slate-300 px-3 py-2" /><button onClick={register} disabled={busy} className="rounded-full border border-slate-300 px-5 py-2.5 font-medium text-slate-700 disabled:opacity-50">Create account</button></div></div> : <button onClick={() => setAuthToken('')} className="mt-5 rounded-full border border-slate-300 px-5 py-2.5 font-medium text-slate-700">Sign out</button>}
            {notice && <p role="status" className="mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
            {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p>}
          </div>
          {user?.role === 'staff' && <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <div className="rounded-3xl border border-indigo-200 bg-indigo-50 p-6"><p className="text-sm font-semibold uppercase tracking-widest text-indigo-700">Staff • Lost & Found</p><h3 className="mt-1 text-lg font-bold text-slate-950">Claims for human verification</h3><div className="mt-4 space-y-3">{itemClaims.map((claim) => <article key={claim.id} className="rounded-xl bg-white p-4"><p className="font-semibold">{claim.title}</p><p className="mt-1 text-sm text-slate-600">Claim #{claim.id} · response is private and not surfaced in this list.</p><button onClick={() => resolveClaim(claim.item_id, claim.id)} className="mt-3 rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white">Verify & resolve</button></article>)}</div>{!itemClaims.length && <p className="mt-3 text-sm text-slate-600">No pending claims.</p>}</div>
            <div className="rounded-3xl border border-indigo-200 bg-indigo-50 p-6"><p className="text-sm font-semibold uppercase tracking-widest text-indigo-700">Staff • Marketplace</p><h3 className="mt-1 text-lg font-bold text-slate-950">Reported listings</h3><div className="mt-4 space-y-3">{listingReports.map((report) => <article key={report.id} className="rounded-xl bg-white p-4"><p className="font-semibold">{report.listing_title}</p><p className="mt-1 text-sm text-slate-600">{report.reason}</p><div className="mt-3 flex gap-2"><button onClick={() => moderateReport(report.id, 'dismiss')} className="rounded-full border border-slate-300 px-4 py-2 text-sm">Dismiss</button><button onClick={() => moderateReport(report.id, 'remove')} className="rounded-full bg-rose-600 px-4 py-2 text-sm font-medium text-white">Remove listing</button></div></article>)}</div>{!listingReports.length && <p className="mt-3 text-sm text-slate-600">No listings awaiting moderation.</p>}</div>
          </div>}
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-8 text-sm text-slate-500 md:flex-row md:items-center md:justify-between">
          <div>© 2026 CampusOne • Demo data is simulated</div>
          <div className="flex gap-6"><a href="#features">About</a><a href="#account">Help</a><a href="#smartflow">Privacy</a><a href="#account">Contact</a></div>
        </div>
      </footer>
    </div>
  )
}

export default App
