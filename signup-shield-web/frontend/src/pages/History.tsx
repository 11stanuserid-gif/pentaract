import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FileText, Clock, ExternalLink, Loader2, History as HistoryIcon, FileJson, Play } from 'lucide-react'
import { API_URL } from '@/lib/config'

interface ReportFile {
  filename: string
  size_bytes: number
  modified: string
  audit_id: string | null
}

export default function History() {
  const navigate = useNavigate()
  const [reports, setReports] = useState<ReportFile[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const res = await fetch(`${API_URL}/api/reports`)
        if (!res.ok) throw new Error('Failed to fetch reports')
        const data = await res.json()
        setReports(data.reports || [])
      } catch {
        // silently fail
      } finally {
        setLoading(false)
      }
    }
    fetchReports()
  }, [])

  const htmlReports = reports.filter((r) => r.filename.endsWith('.html'))
  const jsonReports = reports.filter((r) => r.filename.endsWith('.json'))

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4 p-6 rounded-xl glass-card border-border/40">
        <div className="p-3 rounded-full bg-primary/10">
          <HistoryIcon className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold">Report History</h1>
          <p className="text-sm text-muted-foreground">Previously generated security audit reports</p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-20">
          <div className="inline-flex items-center justify-center p-4 bg-primary/10 rounded-full mb-4 glow-blue">
            <Loader2 className="h-8 w-8 text-primary animate-spin" />
          </div>
          <p className="text-muted-foreground">Loading reports...</p>
        </div>
      ) : htmlReports.length === 0 ? (
        <Card className="glass-card border-border/40">
          <CardContent className="py-16 text-center">
            <div className="inline-flex items-center justify-center p-4 bg-muted/30 rounded-full mb-4">
              <FileText className="h-10 w-10 text-muted-foreground opacity-50" />
            </div>
            <h3 className="text-lg font-medium mb-2">No Reports Yet</h3>
            <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
              Run a security audit to generate your first report. It will appear here automatically.
            </p>
            <Button onClick={() => navigate('/')}>
              <Play className="mr-2 h-4 w-4" /> Start New Audit
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* HTML Reports */}
          <Card className="glass-card border-border/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                HTML Reports
                <Badge variant="outline" className="ml-1 text-xs border-border/40">{htmlReports.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {htmlReports.map((r, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-4 rounded-xl bg-accent/5 border border-border/20 hover:bg-accent/15 transition-all stat-card"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="p-2 rounded-lg bg-primary/10 shrink-0">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{r.filename}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(r.modified).toLocaleString()}
                        </span>
                        <span className="bg-muted/30 px-1.5 py-0.5 rounded text-[10px]">
                          {(r.size_bytes / 1024).toFixed(1)} KB
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    {r.audit_id && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/report/${r.audit_id}`)}
                        className="border-border/40"
                      >
                        View
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(`${API_URL}/api/reports/${r.filename}`, '_blank')}
                      className="hover:bg-accent/20"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* JSON Reports */}
          {jsonReports.length > 0 && (
            <Card className="glass-card border-border/40">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileJson className="h-4 w-4 text-amber-400" />
                  JSON Reports
                  <Badge variant="outline" className="ml-1 text-xs border-border/40">{jsonReports.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {jsonReports.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-4 rounded-xl bg-accent/5 border border-border/20 hover:bg-accent/15 transition-all stat-card"
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="p-2 rounded-lg bg-amber-500/10 shrink-0">
                        <FileJson className="h-5 w-5 text-amber-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{r.filename}</p>
                        <p className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(r.modified).toLocaleString()}
                          </span>
                          <span className="bg-muted/30 px-1.5 py-0.5 rounded text-[10px]">
                            {(r.size_bytes / 1024).toFixed(1)} KB
                          </span>
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(`${API_URL}/api/reports/${r.filename}`, '_blank')}
                      className="hover:bg-accent/20 shrink-0 ml-3"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
