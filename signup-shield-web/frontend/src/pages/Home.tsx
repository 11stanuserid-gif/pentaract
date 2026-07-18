import { useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Shield, Play, Loader2, Zap, Timer, Gauge, Sliders } from 'lucide-react'
import { API_URL } from '@/lib/config'

const delayModes = [
  {
    id: 'auto',
    label: 'Auto',
    description: 'Adjusts delay based on account count',
    icon: Gauge,
    color: 'text-blue-400',
    gradient: 'from-blue-500/20 to-purple-500/20',
  },
  {
    id: 'fast',
    label: 'Fast',
    description: '0.5–1.5s between signups',
    icon: Zap,
    color: 'text-emerald-400',
    gradient: 'from-emerald-500/20 to-teal-500/20',
  },
  {
    id: 'normal',
    label: 'Normal',
    description: '2–5s between signups',
    icon: Timer,
    color: 'text-amber-400',
    gradient: 'from-amber-500/20 to-yellow-500/20',
  },
  {
    id: 'stealth',
    label: 'Stealth',
    description: '5–15s — hardest to detect',
    icon: Shield,
    color: 'text-red-400',
    gradient: 'from-red-500/20 to-rose-500/20',
  },
  {
    id: 'custom',
    label: 'Custom',
    description: 'Set your own delays',
    icon: Sliders,
    color: 'text-purple-400',
    gradient: 'from-purple-500/20 to-pink-500/20',
  },
]

export default function Home() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    target_url: '',
    num_accounts: 5,
    delay_mode: 'auto',
    delay_min: 2.0,
    delay_max: 5.0,
    headless: true,
    weak_password_pct: 0,
    captcha_api_key: '',
    captcha_service: 'free',
    test_captcha: true,
    test_rate_limit: true,
    test_email_verify: true,
    test_fingerprint: true,
    test_password_policy: true,
    test_duplicate: true,
  })

  const update = (key: string, value: any) => setForm((f) => ({
    ...f,
    [key]: value,
    ...(key === 'captcha_service' && value === 'free' ? { captcha_api_key: '' } : {}),
  }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!form.target_url || form.target_url === 'https://example.com/signup') {
      setError('Please enter a valid target URL')
      return
    }
    if (!form.target_url.startsWith('http://') && !form.target_url.startsWith('https://')) {
      setError('URL must start with http:// or https://')
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to start audit')
      }
      const data = await res.json()
      navigate(`/audit/${data.audit_id}`)
    } catch (err: any) {
      setError(err.message || 'Connection failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Hero */}
      <div className="text-center py-10 relative">
        <div className="absolute inset-0 bg-grid opacity-30 pointer-events-none" />
        <div className="relative">
          <div className="inline-flex items-center justify-center p-4 bg-primary/10 rounded-full mb-5 glow-blue">
            <Shield className="h-10 w-10 text-primary" />
          </div>
          <h1 className="text-4xl font-bold mb-3 tracking-tight">
            <span className="text-gradient">Signup Shield Auditor</span>
          </h1>
          <p className="text-muted-foreground max-w-xl mx-auto text-lg">
            Automated security testing for signup pages. Test CAPTCHA, rate limiting,
            email verification, password policies, and more.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Target URL */}
        <Card className="glass-card border-border/40">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs text-primary font-bold">1</span>
              Target Configuration
            </CardTitle>
            <CardDescription>Enter the signup page URL you want to test</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="url" className="text-sm font-medium">Target URL</Label>
              <div className="relative">
                <Input
                  id="url"
                  placeholder="https://example.com/signup"
                  value={form.target_url}
                  onChange={(e) => update('target_url', e.target.value)}
                  className="pl-4 h-12 text-base bg-background/50 border-border/50 focus:border-primary/50 transition-all"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="accounts" className="text-sm font-medium">Number of Accounts</Label>
                <Input
                  id="accounts"
                  type="number"
                  min={1}
                  max={1000}
                  value={form.num_accounts}
                  onChange={(e) => update('num_accounts', parseInt(e.target.value) || 1)}
                  className="h-12 bg-background/50 border-border/50"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="headless" className="text-sm font-medium">Browser Mode</Label>
                <div className="flex h-12 items-center gap-3 px-4 rounded-lg border border-border/50 bg-background/50">
                  <Checkbox
                    id="headless"
                    checked={form.headless}
                    onCheckedChange={(c) => update('headless', c === true)}
                  />
                  <Label htmlFor="headless" className="cursor-pointer text-sm">Headless (background)</Label>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="weak_pw" className="text-sm font-medium">Weak Password %</Label>
                <Input
                  id="weak_pw"
                  type="number"
                  min={0}
                  max={100}
                  value={form.weak_password_pct}
                  onChange={(e) => update('weak_password_pct', parseFloat(e.target.value) || 0)}
                  className="h-12 bg-background/50 border-border/50"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Delay Mode */}
        <Card className="glass-card border-border/40">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs text-primary font-bold">2</span>
              Delay Mode
            </CardTitle>
            <CardDescription>Choose how fast signup attempts are made</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {delayModes.map((mode) => {
                const Icon = mode.icon
                const isActive = form.delay_mode === mode.id
                return (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => update('delay_mode', mode.id)}
                    className={`relative p-4 rounded-xl border text-left transition-all duration-200 ${
                      isActive
                        ? `border-primary/50 bg-gradient-to-br ${mode.gradient} shadow-lg shadow-primary/5`
                        : 'border-border/40 bg-background/30 hover:bg-accent/30 hover:border-border/60'
                    }`}
                  >
                    <Icon className={`h-5 w-5 mb-2 ${isActive ? mode.color : 'text-muted-foreground'}`} />
                    <div className={`text-sm font-semibold ${isActive ? 'text-foreground' : 'text-muted-foreground'}`}>
                      {mode.label}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5 leading-tight">
                      {mode.description}
                    </div>
                    {isActive && (
                      <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary animate-pulse" />
                    )}
                  </button>
                )
              })}
            </div>

            {/* Custom delay fields - only visible when custom mode is selected */}
            {form.delay_mode === 'custom' && (
              <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-accent/20 border border-border/40 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="space-y-2">
                  <Label htmlFor="delay_min" className="text-sm font-medium">Min Delay (sec)</Label>
                  <Input
                    id="delay_min"
                    type="number"
                    step={0.5}
                    min={0.5}
                    value={form.delay_min}
                    onChange={(e) => update('delay_min', parseFloat(e.target.value) || 0.5)}
                    className="h-11 bg-background/50 border-border/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="delay_max" className="text-sm font-medium">Max Delay (sec)</Label>
                  <Input
                    id="delay_max"
                    type="number"
                    step={0.5}
                    min={0.5}
                    value={form.delay_max}
                    onChange={(e) => update('delay_max', parseFloat(e.target.value) || 0.5)}
                    className="h-11 bg-background/50 border-border/50"
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* CAPTCHA Configuration */}
        <Card className="glass-card border-border/40">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs text-primary font-bold">3</span>
              CAPTCHA Configuration
            </CardTitle>
            <CardDescription>Set up CAPTCHA solving to bypass automated detection</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium">CAPTCHA Service</Label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: 'free', label: 'Free (Open Source)', desc: 'No API key needed — audio + stealth' },
                  { id: 'capsolver', label: 'Capsolver', desc: 'Fast, modern API (paid)' },
                  { id: '2captcha', label: '2Captcha', desc: 'Reliable, budget-friendly (paid)' },
                ].map((svc) => (
                  <button
                    key={svc.id}
                    type="button"
                    onClick={() => update('captcha_service', svc.id)}
                    className={`relative p-3 rounded-xl border text-left transition-all duration-200 ${
                      form.captcha_service === svc.id
                        ? 'border-primary/50 bg-gradient-to-br from-primary/20 to-purple-500/20 shadow-lg shadow-primary/5'
                        : 'border-border/40 bg-background/30 hover:bg-accent/30'
                    }`}
                  >
                    <div className={`text-sm font-semibold ${form.captcha_service === svc.id ? 'text-foreground' : 'text-muted-foreground'}`}>
                      {svc.label}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{svc.desc}</div>
                    {form.captcha_service === svc.id && (
                      <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary animate-pulse" />
                    )}
                  </button>
                ))}
              </div>
            </div>
            {form.captcha_service !== 'free' && (
              <div className="space-y-2">
                <Label htmlFor="captcha_api_key" className="text-sm font-medium">CAPTCHA API Key</Label>
                <Input
                  id="captcha_api_key"
                  type="password"
                  placeholder="capsolver or 2captcha API key"
                  value={form.captcha_api_key}
                  onChange={(e) => update('captcha_api_key', e.target.value)}
                  className="h-11 bg-background/50 border-border/50 font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Get a key from <a href="https://capsolver.com" target="_blank" rel="noopener noreferrer" className="text-primary underline">capsolver.com</a> or <a href="https://2captcha.com" target="_blank" rel="noopener noreferrer" className="text-primary underline">2captcha.com</a>
                </p>
              </div>
            )}
            {form.captcha_service === 'free' && (
              <div className="rounded-xl bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/20 p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-sm font-semibold text-green-600 dark:text-green-400">Open Source Mode Active</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Uses free techniques: audio reCAPTCHA solving via Google Speech Recognition, 
                  Playwright stealth enhancements, and Cloudflare Turnstile bypass. 
                  No API key required.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Security Tests */}
        <Card className="glass-card border-border/40">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs text-primary font-bold">4</span>
              Security Tests
            </CardTitle>
            <CardDescription>Select which security checks to perform</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { key: 'test_captcha', label: 'CAPTCHA Detection', desc: 'Check if CAPTCHA blocks automated signups' },
                { key: 'test_rate_limit', label: 'Rate Limiting', desc: 'Test request throttling after multiple attempts' },
                { key: 'test_email_verify', label: 'Email Verification', desc: 'Verify email confirmation requirement' },
                { key: 'test_fingerprint', label: 'Device Fingerprint', desc: 'Detect browser fingerprinting' },
                { key: 'test_password_policy', label: 'Password Policy', desc: 'Evaluate password strength requirements' },
                { key: 'test_duplicate', label: 'Duplicate Detection', desc: 'Test duplicate account prevention' },
              ].map(({ key, label, desc }) => (
                <div
                  key={key}
                  className={`flex items-start gap-3 p-3 rounded-lg border transition-all cursor-pointer hover:bg-accent/20 ${
                    (form as any)[key] ? 'border-primary/30 bg-primary/5' : 'border-border/30 bg-background/30'
                  }`}
                  onClick={() => update(key, !(form as any)[key])}
                >
                  <Checkbox
                    id={key}
                    checked={(form as any)[key] as boolean}
                    onCheckedChange={(c) => update(key, c === true)}
                    className="mt-0.5"
                  />
                  <div>
                    <Label htmlFor={key} className="cursor-pointer text-sm font-medium">{label}</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Error display */}
        {error && (
          <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-sm flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-destructive/20 flex items-center justify-center shrink-0">
              <Shield className="h-4 w-4" />
            </div>
            <span>{error}</span>
          </div>
        )}

        {/* Submit */}
        <div className="flex items-center gap-4">
          <Button type="submit" size="lg" disabled={loading} className="h-12 px-8 text-base font-semibold shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Starting Audit...
              </>
            ) : (
              <>
                <Play className="mr-2 h-5 w-5" />
                Start Security Audit
              </>
            )}
          </Button>
          <Badge variant="outline" className="text-xs px-3 py-1.5 border-border/40">
            Playwright &bull; Headless Chrome
          </Badge>
        </div>
      </form>
    </div>
  )
}
