import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, ArrowLeft, FileText, AlertCircle, Activity, Terminal } from 'lucide-react'
import { API_URL } from '@/lib/config'

interface StatusData {
  audit_id: string
  status: string
  progress: number
  current_step: string
  log_lines: string[]
}

export default function AuditProgress() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [status, setStatus] = useState<StatusData | null>(null)
  const [error, setError] = useState('')
  const logEndRef = useRef<HTMLDivElement>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval>>()

  useEffect(() => {
    if (!id) return

    const poll = async () => {
      try {
        const res = await fetch(`${API_URL}/api/audit/${id}/status`)
        if (!res.ok) throw new Error('Audit not found')
        const data: StatusData = await res.json()
        setStatus(data)

        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(intervalRef.current)
        }
      } catch (err: any) {
        setError(err.message)
        clearInterval(intervalRef.current)
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 1000)

    return () => clearInterval(intervalRef.current)
  }, [id])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [status?.log_lines])

  if (error) {
    return (
      <div className="max-w-2xl mx-auto text-center py-20">
        <div className="inline-flex items-center justify-center p-4 bg-destructive/10 rounded-full mb-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Error</h2>
        <p className="text-muted-foreground mb-6">{error}</p>
        <Button onClick={() => navigate('/')}>Back to Home</Button>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="max-w-2xl mx-auto text-center py-20">
        <div className="inline-flex items-center justify-center p-4 bg-primary/10 rounded-full mb-4 glow-blue">
          <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
        <p className="text-muted-foreground">Loading audit status...</p>
      </div>
    )
  }

  const isComplete = status.status === 'completed'
  const isFailed = status.status === 'failed'
  const isRunning = status.status === 'running'

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between p-6 rounded-xl glass-card border-border/40">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-full ${isRunning ? 'bg-primary/10' : isComplete ? 'bg-emerald-500/10' : 'bg-destructive/10'}`}>
            <Activity className={`h-6 w-6 ${isRunning ? 'text-primary' : isComplete ? 'text-emerald-400' : 'text-destructive'}`} />
          </div>
          <div>
            <h1 className="text-xl font-bold">Security Audit</h1>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">ID: {id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isRunning && (
            <Badge variant="warning" className="animate-pulse px-3 py-1">
              <Loader2 className="h-3 w-3 mr-1.5 animate-spin" /> Running
            </Badge>
          )}
          {isComplete && <Badge variant="success" className="px-3 py-1">Completed</Badge>}
          {isFailed && <Badge variant="destructive" className="px-3 py-1">Failed</Badge>}
        </div>
      </div>

      {/* Progress */}
      <Card className="glass-card border-border/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Progress
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Progress value={status.progress} className="h-3 rounded-full bg-border/50" />
            <div
              className="absolute top-0 left-0 h-3 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500 ease-out"
              style={{ width: `${status.progress}%`, opacity: 0.3 }}
            />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground flex items-center gap-2">
              <Terminal className="h-3.5 w-3.5" />
              {status.current_step}
            </span>
            <span className="text-lg font-bold text-gradient">{Math.round(status.progress)}%</span>
          </div>
        </CardContent>
      </Card>

      {/* Log console */}
      <Card className="glass-card border-border/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Terminal className="h-4 w-4 text-muted-foreground" />
            Activity Log
            {isRunning && <span className="text-xs font-normal text-muted-foreground">(updating...)</span>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[420px] rounded-xl bg-black/60 border border-border/30 p-4">
            <div className="space-y-1">
              {status.log_lines.length === 0 && (
                <div className="text-xs font-mono text-muted-foreground italic">Waiting for logs...</div>
              )}
              {status.log_lines.map((line, i) => (
                <div key={i} className="log-entry text-xs font-mono text-green-400/80 leading-relaxed hover:text-green-300 transition-colors">
                  {line}
                </div>
              ))}
              {isRunning && (
                <div className="text-xs font-mono text-primary animate-pulse mt-2">▌</div>
              )}
              <div ref={logEndRef} />
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <Button variant="outline" onClick={() => navigate('/')} className="border-border/40">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back
        </Button>
        {isComplete && (
          <Button onClick={() => navigate(`/report/${id}`)} className="shadow-lg shadow-primary/20">
            <FileText className="mr-2 h-4 w-4" /> View Report
          </Button>
        )}
        {isFailed && (
          <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-4 py-2 rounded-lg border border-destructive/20">
            <AlertCircle className="h-4 w-4" />
            The audit failed. Check the log for details.
          </div>
        )}
      </div>
    </div>
  )
}
