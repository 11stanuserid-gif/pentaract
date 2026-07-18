import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, Shield, AlertTriangle, CheckCircle, XCircle, Clock, Globe, Target } from 'lucide-react'
import { API_URL } from '@/lib/config'

interface ReportData {
  audit_id: string
  status: string
  report?: any
  error?: string
}

const severityClass = (rec: string) => {
  if (rec.startsWith('CRITICAL')) return 'destructive'
  if (rec.startsWith('HIGH')) return 'destructive'
  if (rec.startsWith('MEDIUM')) return 'warning'
  if (rec.startsWith('LOW')) return 'secondary'
  if (rec.startsWith('Good')) return 'success'
  return 'outline'
}

function ScoreCircle({ score }: { score: number }) {
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444'
  const r = 70
  const circumference = 2 * Math.PI * r
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="relative inline-flex items-center justify-center score-glow-green">
      <svg width="200" height="200" className="transform -rotate-90">
        <circle cx="100" cy="100" r={r} fill="none" stroke="#1e293b" strokeWidth="14" />
        <circle
          cx="100"
          cy="100"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-5xl font-bold tracking-tight" style={{ color }}>{score}%</span>
        <span className="text-sm text-muted-foreground mt-1.5 font-medium">
          {score >= 70 ? 'SECURE' : score >= 40 ? 'MODERATE' : 'CRITICAL'}
        </span>
      </div>
    </div>
  )
}

function StatCard({ label, value, color, icon: Icon }: { label: string; value: string | number; color: string; icon?: any }) {
  return (
    <Card className="glass-card border-border/40 stat-card cursor-default">
      <CardContent className="pt-6 text-center">
        {Icon && <Icon className={`h-5 w-5 mx-auto mb-2 ${color}`} />}
        <div className={`text-3xl font-bold ${color}`}>{value}</div>
        <p className="text-xs text-muted-foreground mt-1.5">{label}</p>
      </CardContent>
    </Card>
  )
}

export default function Report() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    const fetchReport = async () => {
      try {
        const res = await fetch(`${API_URL}/api/audit/${id}/report`)
        if (!res.ok) throw new Error('Report not found')
        const d: ReportData = await res.json()
        setData(d)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchReport()
  }, [id])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="inline-flex items-center justify-center p-4 bg-primary/10 rounded-full mb-4 glow-blue">
          <Shield className="h-8 w-8 text-primary animate-pulse" />
        </div>
        <p className="text-muted-foreground">Loading report...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="inline-flex items-center justify-center p-4 bg-destructive/10 rounded-full mb-4">
          <XCircle className="h-10 w-10 text-destructive" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Report Not Found</h2>
        <p className="text-muted-foreground mb-6">{error || 'The report could not be loaded.'}</p>
        <Button onClick={() => navigate('/')}>Back to Home</Button>
      </div>
    )
  }

  if (data.status === 'failed') {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <div className="inline-flex items-center justify-center p-4 bg-destructive/10 rounded-full mb-4">
          <AlertTriangle className="h-10 w-10 text-destructive" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Audit Failed</h2>
        <p className="text-muted-foreground mb-6">{data.error}</p>
        <Button onClick={() => navigate('/')}>Back to Home</Button>
      </div>
    )
  }

  const report = data.report
  if (!report) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <p className="text-muted-foreground">No report data available.</p>
        <Button onClick={() => navigate('/')} className="mt-4">Back to Home</Button>
      </div>
    )
  }

  const meta = report.test_metadata
  const signup = report.signup_summary
  const score = report.security_score
  const recommendations = report.recommendations || []
  const attempts = report.attempts || []
  const createdAccounts = report.created_accounts || []

  const seenTests = new Set()
  const testResults: { name: string; passed: boolean; details: any }[] = []
  for (const attempt of attempts) {
    for (const sr of attempt.security_results || []) {
      if (!seenTests.has(sr.test_name)) {
        seenTests.add(sr.test_name)
        testResults.push({ name: sr.test_name, passed: sr.passed, details: sr.details })
      }
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between p-6 rounded-xl glass-card border-border/40">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-full bg-primary/10">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Security Report</h1>
            <p className="text-sm text-muted-foreground mt-0.5 flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5" />
              {meta.target_url}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="px-3 py-1.5 border-border/40">
            <Clock className="h-3 w-3 mr-1.5" />
            {meta.duration_seconds}s
          </Badge>
          <Button variant="outline" size="sm" onClick={() => navigate('/')} className="border-border/40">
            <ArrowLeft className="mr-1 h-4 w-4" /> Back
          </Button>
        </div>
      </div>

      {/* Score + Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="gradient-border flex items-center justify-center py-8 bg-background/50">
          <ScoreCircle score={score.overall_percentage} />
        </Card>
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            label="Signup Attempts"
            value={meta.num_accounts_executed}
            color="text-primary"
            icon={Target}
          />
          <StatCard
            label="Successful"
            value={signup.successful}
            color="text-emerald-400"
            icon={CheckCircle}
          />
          <StatCard
            label="Blocked"
            value={signup.blocked}
            color="text-red-400"
            icon={XCircle}
          />
          <StatCard
            label="Tests Passed"
            value={`${score.tests_passed}/${score.total_tests}`}
            color="text-amber-400"
            icon={Shield}
          />
        </div>
      </div>

      {/* Details tabs */}
      <Tabs defaultValue="tests">
        <TabsList className="grid grid-cols-4 w-full max-w-2xl bg-background/50 border border-border/30">
          <TabsTrigger value="tests" className="data-[state=active]:bg-primary/10">Tests</TabsTrigger>
          <TabsTrigger value="recommendations" className="data-[state=active]:bg-primary/10">Recommendations</TabsTrigger>
          <TabsTrigger value="accounts" className="data-[state=active]:bg-primary/10">Accounts</TabsTrigger>
          <TabsTrigger value="attempts" className="data-[state=active]:bg-primary/10">Attempts</TabsTrigger>
        </TabsList>

        {/* Test Results */}
        <TabsContent value="tests">
          <Card className="glass-card border-border/40">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                Security Test Results
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {testResults.length === 0 && (
                <p className="text-muted-foreground text-center py-8">No test results available.</p>
              )}
              {testResults.map((tr, i) => (
                <div
                  key={i}
                  className={`p-4 rounded-xl border-l-4 transition-all hover:bg-accent/10 ${
                    tr.passed
                      ? 'border-l-emerald-500 bg-emerald-500/5'
                      : 'border-l-red-500 bg-red-500/5'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium flex items-center gap-2">
                      {tr.passed
                        ? <CheckCircle className="h-4 w-4 text-emerald-400" />
                        : <XCircle className="h-4 w-4 text-red-400" />
                      }
                      {tr.name}
                    </span>
                    <Badge variant={tr.passed ? 'success' : 'destructive'} className="px-2.5">
                      {tr.passed ? 'PASS' : 'FAIL'}
                    </Badge>
                  </div>
                  {tr.details?.status && (
                    <p className="text-sm text-muted-foreground ml-6">{tr.details.status}</p>
                  )}
                  {tr.details?.recommendation && (
                    <p className="text-xs text-muted-foreground mt-1.5 italic ml-6">
                      💡 {tr.details.recommendation}
                    </p>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Recommendations */}
        <TabsContent value="recommendations">
          <Card className="glass-card border-border/40">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {recommendations.length === 0 && (
                <p className="text-muted-foreground text-center py-8">No recommendations. Your signup page looks solid!</p>
              )}
              {recommendations.map((rec: string, i: number) => (
                <div
                  key={i}
                  className={`p-3 rounded-xl border-l-4 transition-all hover:bg-accent/10 ${
                    rec.startsWith('CRITICAL')
                      ? 'border-l-red-500 bg-red-500/10'
                      : rec.startsWith('HIGH')
                      ? 'border-l-orange-500 bg-orange-500/10'
                      : rec.startsWith('MEDIUM')
                      ? 'border-l-yellow-500 bg-yellow-500/10'
                      : rec.startsWith('LOW')
                      ? 'border-l-blue-500 bg-blue-500/10'
                      : 'border-l-emerald-500 bg-emerald-500/10'
                  }`}
                >
                  <Badge variant={severityClass(rec) as any} className="mb-1.5 text-[10px] px-2 py-0">
                    {rec.split(':')[0]}
                  </Badge>
                  <p className="text-sm">{rec.replace(/^(CRITICAL|HIGH|MEDIUM|LOW|Good):\s*/, '')}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Created Accounts */}
        <TabsContent value="accounts">
          <Card className="glass-card border-border/40">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-emerald-400" />
                Created Accounts <span className="text-sm text-muted-foreground font-normal">({createdAccounts.length} accounts)</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              {createdAccounts.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground mb-2">No accounts were created during this test.</p>
                  <p className="text-xs text-muted-foreground">Enable CAPTCHA solving and email verification to create accounts.</p>
                </div>
              ) : (
                <>
                  <div className="mb-4 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-border/40 text-xs"
                      onClick={() => {
                        const text = createdAccounts.map((a: any) =>
                          `Email: ${a.email}\nPassword: ${a.password}\nName: ${a.name}\nPhone: ${a.phone || 'N/A'}\n---`
                        ).join('\n')
                        navigator.clipboard.writeText(text)
                      }}
                    >
                      Copy All Credentials
                    </Button>
                  </div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border/50">
                        <th className="text-left py-3 px-3 text-muted-foreground font-medium">#</th>
                        <th className="text-left py-3 px-3 text-muted-foreground font-medium">Name</th>
                        <th className="text-left py-3 px-3 text-muted-foreground font-medium">Email</th>
                        <th className="text-left py-3 px-3 text-muted-foreground font-medium">Password</th>
                        <th className="text-left py-3 px-3 text-muted-foreground font-medium">Phone</th>
                        <th className="text-left py-3 px-3 text-muted-foreground font-medium">Verified</th>
                        <th className="text-left py-3 px-3 text-muted-foreground font-medium">Copy</th>
                      </tr>
                    </thead>
                    <tbody>
                      {createdAccounts.map((acct: any, i: number) => (
                        <tr key={i} className="border-b border-border/20 hover:bg-accent/20 transition-colors">
                          <td className="py-3 px-3 font-mono text-xs">{acct.attempt_number || i + 1}</td>
                          <td className="py-3 px-3">{acct.name || 'N/A'}</td>
                          <td className="py-3 px-3 font-mono text-xs text-muted-foreground">{acct.email || 'N/A'}</td>
                          <td className="py-3 px-3 font-mono text-xs text-amber-400">{acct.password || 'N/A'}</td>
                          <td className="py-3 px-3 text-xs">{acct.phone || 'N/A'}</td>
                          <td className="py-3 px-3">
                            <span className={`text-xs font-medium ${acct.verified ? 'text-emerald-400' : 'text-yellow-400'}`}>
                              {acct.verified ? 'YES' : 'No'}
                            </span>
                          </td>
                          <td className="py-3 px-3">
                            <button
                              onClick={() => {
                                const text = `Email: ${acct.email}\nPassword: ${acct.password}\nName: ${acct.name}\nPhone: ${acct.phone || 'N/A'}`
                                navigator.clipboard.writeText(text)
                              }}
                              className="text-xs text-primary hover:underline"
                              title="Copy credentials"
                            >
                              Copy
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Attempts Log */}
        <TabsContent value="attempts">
          <Card className="glass-card border-border/40">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Target className="h-4 w-4 text-primary" />
                Signup Attempts
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50">
                    <th className="text-left py-3 px-3 text-muted-foreground font-medium">#</th>
                    <th className="text-left py-3 px-3 text-muted-foreground font-medium">Name</th>
                    <th className="text-left py-3 px-3 text-muted-foreground font-medium">Email</th>
                    <th className="text-left py-3 px-3 text-muted-foreground font-medium">Location</th>
                    <th className="text-left py-3 px-3 text-muted-foreground font-medium">Password</th>
                    <th className="text-left py-3 px-3 text-muted-foreground font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {attempts.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-muted-foreground">No attempt data available.</td>
                    </tr>
                  )}
                  {attempts.map((a: any, i: number) => (
                    <tr key={i} className="border-b border-border/20 hover:bg-acent/20 transition-colors">
                      <td className="py-3 px-3 font-mono text-xs">{a.attempt_number}</td>
                      <td className="py-3 px-3">{a.identity?.name || 'N/A'}</td>
                      <td className="py-3 px-3 font-mono text-xs text-muted-foreground">{a.identity?.email || 'N/A'}</td>
                      <td className="py-3 px-3 text-xs">{a.identity?.location || 'N/A'}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            a.identity?.is_weak_password
                              ? 'bg-red-500/10 text-red-400'
                              : 'bg-emerald-500/10 text-emerald-400'
                          }`}
                        >
                          {a.identity?.is_weak_password ? 'WEAK' : 'Strong'}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`text-xs font-medium flex items-center gap-1 ${
                            a.success ? 'text-emerald-400' : 'text-red-400'
                          }`}
                        >
                          {a.success
                            ? <CheckCircle className="h-3 w-3" />
                            : <XCircle className="h-3 w-3" />
                          }
                          {a.success ? 'SUCCESS' : 'BLOCKED'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Target info */}
      <Card className="glass-card border-border/40">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Globe className="h-4 w-4 text-primary" />
            Target Information
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm">
          <div className="p-3 rounded-lg bg-accent/10">
            <span className="text-muted-foreground text-xs block mb-0.5">URL</span>
            <span className="font-mono text-xs break-all">{meta.target_url}</span>
          </div>
          <div className="p-3 rounded-lg bg-accent/10">
            <span className="text-muted-foreground text-xs block mb-0.5">Duration</span>
            <span className="font-mono">{meta.duration_seconds}s</span>
          </div>
          <div className="p-3 rounded-lg bg-accent/10">
            <span className="text-muted-foreground text-xs block mb-0.5">Start Time</span>
            <span>{new Date(meta.start_time).toLocaleString()}</span>
          </div>
          <div className="p-3 rounded-lg bg-accent/10">
            <span className="text-muted-foreground text-xs block mb-0.5">End Time</span>
            <span>{new Date(meta.end_time).toLocaleString()}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
