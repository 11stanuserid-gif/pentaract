import { Routes, Route, Link, useLocation } from 'react-router'
import { Shield, History, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'
import Home from './pages/Home'
import AuditProgress from './pages/AuditProgress'
import Report from './pages/Report'
import HistoryPage from './pages/History'

const navItems = [
  { path: '/', label: 'New Audit', icon: Shield },
  { path: '/history', label: 'History', icon: History },
]

export default function App() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 items-center px-4">
          <div className="flex items-center gap-2 mr-8">
            <Activity className="h-5 w-5 text-primary" />
            <span className="font-bold text-lg text-gradient">Signup Shield</span>
          </div>
          <nav className="flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  'inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  location.pathname === item.path
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/audit/:id" element={<AuditProgress />} />
          <Route path="/report/:id" element={<Report />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  )
}
