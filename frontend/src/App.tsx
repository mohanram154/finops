import { useState, useEffect } from 'react'
import {
  LayoutDashboard,
  PlayCircle,
  Lightbulb,
  Sliders,
  Zap,
  Coins,
  RefreshCw,
  Send,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Sparkles,
  Database
} from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts'

// ============================================================================
// Types
// ============================================================================
interface AnalyticsSummary {
  total_ai_spend: number
  baseline_cost: number
  total_savings: number
  savings_percentage: number
  average_quality: number
  baseline_average_quality: number
  cache_savings: number
  cost_per_successful_outcome: number
  total_requests: number
  successful_requests: number
  cache_hit_rate: number
  fallback_count: number
  currency: string
  pricing_label: string
  data_label: string
  monthly_budget: number
  budget_used: number
  budget_remaining: number
  budget_usage_percent: number
  budget_status: 'normal' | 'warning' | 'critical'
  executive_summary: string
}

interface CostOverTimePoint {
  date: string
  spend: number
  baseline: number
  savings: number
  cache_savings: number
}

interface QualityVsCostPoint {
  tier: string
  model: string
  cost_per_1k: number
  quality_score: number
  latency_ms: number
  requests_count: number
}

interface FinOpsRecommendation {
  id: string
  title: string
  description: string
  issue: string
  observation: string
  recommendation: string
  estimated_savings: number
  quality_impact: number
  risk: string
  category: string
  status: string
  action_type: string
  badge: string
}

interface ModelTierComparison {
  tier: string
  model_name: string
  estimated_tokens: number
  estimated_cost: number
  estimated_quality: number
  estimated_latency_ms: number
  is_valid: boolean
  status_label: string
  reason: string
}

interface SimulateResponse {
  prompt: string
  required_quality: number
  comparisons: ModelTierComparison[]
  recommended_tier: string
  recommended_model: string
  recommendation_reason: string
  estimated_savings_vs_advanced: number
  savings_percentage: number
}

interface AnalysisResult {
  intent: string
  task_type: string
  complexity: 'LOW' | 'MEDIUM' | 'HIGH'
  estimated_input_tokens: number
  estimated_output_tokens: number
  sensitivity: string
  business_criticality: string
  required_quality: number
  latency_requirement: string
  context_size: string
  risk_level: string
  priority: string
}

interface ChatResponse {
  request_id: string
  response: string
  selected_model: string
  final_model: string
  routing_reason: string[]
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost: number
  quality_score: number
  latency_ms: number
  cache_hit: boolean
  fallback_used: boolean
  success: boolean
  execution_mode: string
  fallback_details?: {
    fallback_triggered: boolean
    initial_model: string
    fallback_model?: string
    fallback_reason?: string
    final_model: string
    final_status: string
    frontend_message?: string
  }
  quality_details?: {
    quality_score: number
    success: boolean
    relevance_score: number
    correctness_score: number
    completeness_score: number
    instruction_following_score: number
    explanation: string
  }
  baseline_comparison?: {
    baseline_model: string
    baseline_cost: number
    optimized_cost: number
    savings: number
    savings_percentage: number
    cost_per_successful_outcome: number
  }
  copilot_explanation?: string
  analysis?: AnalysisResult
}

const EXECUTION_STEPS = [
  'Analyzing request complexity & intent...',
  'Checking enterprise policy & budget limits...',
  'Intelligent routing engine selecting optimal model...',
  'Executing model completion...',
  'Evaluating 4-dimension quality guardrail...',
  'Computing token accounting & FinOps savings...'
]

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'playground' | 'advisor' | 'simulator'>('dashboard')
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [costTrends, setCostTrends] = useState<CostOverTimePoint[]>([])
  const [qualityPoints, setQualityPoints] = useState<QualityVsCostPoint[]>([])
  const [recommendations, setRecommendations] = useState<FinOpsRecommendation[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [backendHealthy, setBackendHealthy] = useState<boolean>(true)
  const [actionNotice, setActionNotice] = useState<string | null>(null)

  // Playground State (Automatic Routing: User enters only prompt)
  const [prompt, setPrompt] = useState<string>(
    'Explain what is a linked list in simple terms'
  )
  const [useCache, setUseCache] = useState<boolean>(true)
  const [customBudgetLimit, setCustomBudgetLimit] = useState<number | null>(null)
  const [executing, setExecuting] = useState<boolean>(false)
  const [execStepIdx, setExecStepIdx] = useState<number>(0)
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)

  // What-If Simulator State
  const [simPrompt, setSimPrompt] = useState<string>(
    'Analyze this enterprise architecture and identify security risks.'
  )
  const [simQuality, setSimQuality] = useState<number>(90)
  const [simulating, setSimulating] = useState<boolean>(false)
  const [simResult, setSimResult] = useState<SimulateResponse | null>(null)

  // Fetch initial analytics and data
  const fetchData = async () => {
    setLoading(true)
    try {
      const healthRes = await fetch('/api/v1/health')
      setBackendHealthy(healthRes.ok)

      const summaryRes = await fetch('/api/v1/analytics/summary')
      if (summaryRes.ok) {
        const sumData: AnalyticsSummary = await summaryRes.json()
        setSummary(sumData)
      }

      const costRes = await fetch('/api/v1/analytics/cost')
      if (costRes.ok) {
        const cData = await costRes.json()
        setCostTrends(cData)
      }

      const qualRes = await fetch('/api/v1/analytics/quality')
      if (qualRes.ok) {
        const qData = await qualRes.json()
        setQualityPoints(qData)
      }

      const recRes = await fetch('/api/v1/finops/recommendations')
      if (recRes.ok) {
        const rData = await recRes.json()
        setRecommendations(rData)
      }
    } catch {
      setBackendHealthy(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Animate loading stages while executing
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null
    if (executing) {
      setExecStepIdx(0)
      interval = setInterval(() => {
        setExecStepIdx((prev) => (prev < EXECUTION_STEPS.length - 1 ? prev + 1 : prev))
      }, 350)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [executing])

  // Execute Request in Playground
  const handleExecute = async () => {
    if (!prompt.trim()) return
    setExecuting(true)
    setChatError(null)

    try {
      const payload: Record<string, any> = {
        prompt: prompt.trim(),
        use_cache: useCache
      }

      // Low budget simulation override if configured
      if (customBudgetLimit !== null) {
        payload.custom_budget = {
          monthly_budget: customBudgetLimit,
          current_spend: customBudgetLimit * 0.98,
          remaining_budget: customBudgetLimit * 0.02
        }
      }

      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        const data: ChatResponse = await res.json()
        setChatResult(data)
        // Refresh summary KPIs quietly
        fetch('/api/v1/analytics/summary')
          .then((r) => r.json())
          .then((d) => setSummary(d))
          .catch(() => { })
      } else {
        const errJson = await res.json().catch(() => ({}))
        setChatError(errJson.detail || 'Something went wrong while executing the request. Please try again.')
      }
    } catch {
      setChatError('Something went wrong while executing the request. Please try again.')
    } finally {
      setExecuting(false)
    }
  }

  // Apply FinOps Recommendation
  const handleApplyRec = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/finops/recommendations/${id}/apply`, { method: 'POST' })
      if (res.ok) {
        const updated: FinOpsRecommendation = await res.json()
        setRecommendations((prev) => prev.map((r) => (r.id === id ? updated : r)))
        setActionNotice(`Policy Updated Successfully: "${updated.title}". Router now enforces this rule.`)
        setTimeout(() => setActionNotice(null), 6000)
      }
    } catch {
      // Handled
    }
  }

  // Run What-If Simulation
  const handleSimulate = async () => {
    if (!simPrompt.trim()) return
    setSimulating(true)
    try {
      const res = await fetch('/api/v1/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: simPrompt.trim(),
          required_quality: simQuality
        })
      })
      if (res.ok) {
        const data: SimulateResponse = await res.json()
        setSimResult(data)
      }
    } catch {
      // Handled
    } finally {
      setSimulating(false)
    }
  }

  const PIE_COLORS = ['#8B5CF6', '#6D28D9', '#C4B5FD']

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#1E1B4B] flex flex-col md:flex-row">
      {/* ==================================================================== */}
      {/* Sidebar Navigation */}
      {/* ==================================================================== */}
      <aside className="w-full md:w-64 bg-white border-r border-[#E5E7EB] flex flex-col justify-between shrink-0 shadow-xs">
        <div>
          {/* Brand Header */}
          <div className="p-6 border-b border-[#E5E7EB]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#6D28D9] text-white flex items-center justify-center font-black tracking-wider shadow-md shadow-violet-200">
                NX
              </div>
              <div>
                <h1 className="text-base font-bold text-[#1E1B4B] leading-none tracking-tight">NEXUS AI FINOPS</h1>
                <p className="text-[11px] font-semibold text-[#7C3AED] mt-1">Autonomous FinOps Gateway</p>
              </div>
            </div>
            <div className="mt-4 px-2.5 py-1 rounded-md bg-[#F5F3FF] border border-[#EDE9FE] flex items-center justify-between">
              <span className="text-[10px] font-bold text-[#6D28D9] uppercase tracking-wider">Mode</span>
              <span className="text-[10px] font-mono font-bold text-[#7C3AED] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                real / SIMULATION
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${activeTab === 'dashboard'
                  ? 'bg-[#EDE9FE] text-[#6D28D9] shadow-xs'
                  : 'text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#1E1B4B]'
                }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Command Center</span>
            </button>

            <button
              onClick={() => setActiveTab('playground')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${activeTab === 'playground'
                  ? 'bg-[#EDE9FE] text-[#6D28D9] shadow-xs'
                  : 'text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#1E1B4B]'
                }`}
            >
              <PlayCircle className="w-4 h-4" />
              <span>AI Playground</span>
              <span className="ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#6D28D9] text-white">LIVE</span>
            </button>

            <button
              onClick={() => setActiveTab('advisor')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${activeTab === 'advisor'
                  ? 'bg-[#EDE9FE] text-[#6D28D9] shadow-xs'
                  : 'text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#1E1B4B]'
                }`}
            >
              <Lightbulb className="w-4 h-4" />
              <span>FinOps Advisor</span>
              <span className="ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700">
                {recommendations.length} Recs
              </span>
            </button>

            <button
              onClick={() => setActiveTab('simulator')}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${activeTab === 'simulator'
                  ? 'bg-[#EDE9FE] text-[#6D28D9] shadow-xs'
                  : 'text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#1E1B4B]'
                }`}
            >
              <Sliders className="w-4 h-4" />
              <span>What-If Simulator</span>
            </button>
          </nav>
        </div>

        {/* Sidebar Footer Metadata */}
        <div className="p-4 border-t border-[#E5E7EB] space-y-3 bg-[#F8FAFC]">
          <div className="flex items-center justify-between text-[11px] text-[#64748B]">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-[#7C3AED]" /> Database
            </span>
            <span className="font-mono font-semibold text-[#1E1B4B]">SQLite (550+ rows)</span>
          </div>

          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[#64748B]">Backend Health</span>
            <span className="inline-flex items-center gap-1 font-semibold text-emerald-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              {backendHealthy ? 'HEALTHY' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </aside>

      {/* ==================================================================== */}
      {/* Main Content Area */}
      {/* ==================================================================== */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Navbar */}
        <header className="bg-white border-b border-[#E5E7EB] px-6 py-4 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-10 shadow-xs">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-[#1E1B4B]">
                {activeTab === 'dashboard' && 'AI FinOps Command Center'}
                {activeTab === 'playground' && 'AI Request Playground'}
                {activeTab === 'advisor' && 'Autonomous FinOps Advisor'}
                {activeTab === 'simulator' && 'What-If Model Simulator'}
              </h2>
            </div>
            <p className="text-xs text-[#64748B] mt-0.5">
              {activeTab === 'dashboard' && 'Optimize AI spend without compromising intelligence.'}
              {activeTab === 'playground' && 'Interactive prompt profiling, intelligent model routing, guardrails & unit economics.'}
              {activeTab === 'advisor' && 'Autonomous recommendations for reducing AI spend while protecting quality.'}
              {activeTab === 'simulator' && 'Simulate unit economics across Small, Medium, and Advanced model tiers.'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-[#EDE9FE] text-[#6D28D9] border border-violet-200">
              Simulated Enterprise Pricing
            </span>
            <button
              onClick={fetchData}
              disabled={loading}
              className="p-2 rounded-lg bg-white border border-[#E5E7EB] hover:bg-[#F8FAFC] text-[#64748B] transition-colors cursor-pointer"
              title="Refresh Analytics"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </header>

        {/* Global Toast / Action Notice */}
        {actionNotice && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 shadow-xs animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-medium">{actionNotice}</span>
          </div>
        )}

        {/* Page Container */}
        <div className="p-6 space-y-6">
          {/* ================================================================ */}
          {/* TAB 1: COMMAND CENTER DASHBOARD */}
          {/* ================================================================ */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              {/* Executive Summary Hero Card */}
              <div className="bg-gradient-to-r from-white via-[#F5F3FF] to-white border border-[#EDE9FE] rounded-2xl p-6 shadow-xs">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                  <div className="space-y-2 max-w-2xl">
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#6D28D9] text-white">
                      <Sparkles className="w-3 h-3" /> EXECUTIVE SUMMARY
                    </div>
                    <h3 className="text-lg font-bold text-[#1E1B4B]">
                      {summary?.savings_percentage ?? 38.4}% AI Cost Reduction Delivered
                    </h3>
                    <p className="text-xs text-[#64748B] leading-relaxed">
                      NEXUS AI FINOPS optimizes AI model selection across 550+ transactions based on request complexity, quality requirements, latency SLAs, privacy constraints, and department budgets. Delivered quality remains at <strong className="text-[#1E1B4B]">{summary?.average_quality ?? 94.2}%</strong>.
                    </p>
                  </div>

                  {/* Value Banner */}
                  <div className="bg-white border border-[#E5E7EB] rounded-xl p-4 shadow-xs text-right shrink-0">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED] block">
                      Core Business Differentiator
                    </span>
                    <p className="text-sm font-black text-[#1E1B4B] mt-1">
                      WE DO NOT JUST SAVE TOKENS.
                    </p>
                    <p className="text-xs font-semibold text-[#6D28D9] mt-0.5">
                      WE OPTIMIZE THE COST OF ACHIEVING A SUCCESSFUL OUTCOME.
                    </p>
                  </div>
                </div>
              </div>

              {/* Baseline vs Optimized Highlight Banner */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 shadow-xs">
                  <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Unoptimized Baseline</span>
                  <p className="text-2xl font-black text-[#64748B] mt-1">₹{summary?.baseline_cost.toFixed(0) ?? '1000'}</p>
                  <span className="text-[10px] text-[#64748B] mt-1 block">All Requests &rarr; Advanced</span>
                </div>

                <div className="bg-white border-2 border-[#6D28D9] rounded-2xl p-5 shadow-sm bg-gradient-to-b from-[#F5F3FF] to-white">
                  <span className="text-xs font-bold text-[#6D28D9] uppercase tracking-wider">NEXUS Optimized</span>
                  <p className="text-2xl font-black text-[#6D28D9] mt-1">₹{summary?.total_ai_spend.toFixed(0) ?? '620'}</p>
                  <span className="text-[10px] font-semibold text-[#16A34A] mt-1 block">
                    ✓ Saved ₹{summary?.total_savings.toFixed(0) ?? '380'} ({summary?.savings_percentage ?? 38}%)
                  </span>
                </div>

                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 shadow-xs">
                  <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Delivered Quality</span>
                  <p className="text-2xl font-black text-[#1E1B4B] mt-1">{summary?.average_quality ?? 94.2}%</p>
                  <span className="text-[10px] text-emerald-600 mt-1 block">Baseline benchmark: 97.0%</span>
                </div>

                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 shadow-xs">
                  <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Cache Savings</span>
                  <p className="text-2xl font-black text-emerald-600 mt-1">₹{summary?.cache_savings.toFixed(0) ?? '320'}</p>
                  <span className="text-[10px] text-[#64748B] mt-1 block">16.4% duplicate avoidance</span>
                </div>

                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 shadow-xs">
                  <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Cost / Success</span>
                  <p className="text-2xl font-black text-[#7C3AED] mt-1">₹{summary?.cost_per_successful_outcome.toFixed(2) ?? '6.20'}</p>
                  <span className="text-[10px] text-[#64748B] mt-1 block">Total Cost / Successes</span>
                </div>
              </div>

              {/* 8 Complete KPI Cards Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
                <div className="bg-white border border-[#E5E7EB] rounded-xl p-3.5 shadow-xs">
                  <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Total Requests</span>
                  <span className="text-lg font-bold text-[#1E1B4B] mt-0.5 block">{summary?.total_requests ?? 550}</span>
                </div>
                <div className="bg-white border border-[#E5E7EB] rounded-xl p-3.5 shadow-xs">
                  <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Total Spend</span>
                  <span className="text-lg font-bold text-[#6D28D9] mt-0.5 block">₹{summary?.total_ai_spend ?? 620}</span>
                </div>
                <div className="bg-white border border-[#E5E7EB] rounded-xl p-3.5 shadow-xs">
                  <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Cost Savings</span>
                  <span className="text-lg font-bold text-emerald-600 mt-0.5 block">₹{summary?.total_savings ?? 380}</span>
                </div>
                <div className="bg-white border border-[#E5E7EB] rounded-xl p-3.5 shadow-xs">
                  <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Savings %</span>
                  <span className="text-lg font-bold text-emerald-600 mt-0.5 block">{summary?.savings_percentage ?? 38.4}%</span>
                </div>
                <div className="bg-white border border-[#E5E7EB] rounded-xl p-3.5 shadow-xs">
                  <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Avg Quality</span>
                  <span className="text-lg font-bold text-[#1E1B4B] mt-0.5 block">{summary?.average_quality ?? 94.2}%</span>
                </div>
                <div className="bg-white border border-[#E5E7EB] rounded-xl p-3.5 shadow-xs">
                  <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Avg Latency</span>
                  <span className="text-lg font-bold text-[#1E1B4B] mt-0.5 block">195 ms</span>
                </div>
                <div className="bg-white border border-[#E5E7EB] rounded-xl p-3.5 shadow-xs">
                  <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Cache Savings</span>
                  <span className="text-lg font-bold text-emerald-600 mt-0.5 block">₹{summary?.cache_savings ?? 320}</span>
                </div>
                <div className="bg-white border border-[#E5E7EB] rounded-xl p-3.5 shadow-xs">
                  <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Cost / Success</span>
                  <span className="text-lg font-bold text-[#7C3AED] mt-0.5 block">₹{summary?.cost_per_successful_outcome ?? 6.20}</span>
                </div>
              </div>

              {/* Monthly AI Budget Progress Card */}
              <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Coins className="w-5 h-5 text-[#6D28D9]" />
                    <h4 className="text-sm font-bold text-[#1E1B4B]">Monthly AI Spend Governance</h4>
                  </div>
                  <div className="flex items-center gap-3 text-xs font-mono">
                    <span className="text-[#64748B]">
                      Used: <strong className="text-[#1E1B4B]">₹{summary?.budget_used ?? 620}</strong> / Budget: ₹{summary?.monthly_budget ?? 1000}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${(summary?.budget_usage_percent ?? 62) < 80
                          ? 'bg-emerald-100 text-emerald-700'
                          : (summary?.budget_usage_percent ?? 62) <= 95
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-rose-100 text-rose-700'
                        }`}
                    >
                      {(summary?.budget_usage_percent ?? 62) < 80 ? 'NORMAL (<80%)' : 'WARNING (>80%)'}
                    </span>
                  </div>
                </div>

                {/* Visual Progress Bar */}
                <div className="w-full bg-[#E5E7EB] h-3 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${(summary?.budget_usage_percent ?? 62) < 80
                        ? 'bg-[#16A34A]'
                        : (summary?.budget_usage_percent ?? 62) <= 95
                          ? 'bg-[#F59E0B]'
                          : 'bg-[#DC2626]'
                      }`}
                    style={{ width: `${summary?.budget_usage_percent ?? 62}%` }}
                  />
                </div>
                <div className="flex justify-between text-[11px] text-[#64748B]">
                  <span>Remaining allocation: ₹{summary?.budget_remaining ?? 380} (38%)</span>
                  <span>Cap enforcement: Automatic model rightsizing active</span>
                </div>
              </div>

              {/* Clean Professional Charts Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Chart 1: AI Spend Over Time vs Baseline */}
                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-sm font-bold text-[#1E1B4B]">AI Spend Over Time</h4>
                      <p className="text-xs text-[#64748B]">NEXUS Optimized Spend vs All-Advanced Baseline (INR)</p>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-[#EDE9FE] text-[#6D28D9]">7-Day Curve</span>
                  </div>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={costTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="date" stroke="#94A3B8" fontSize={11} />
                        <YAxis stroke="#94A3B8" fontSize={11} />
                        <Tooltip />
                        <Area type="monotone" dataKey="baseline" stroke="#94A3B8" fill="#F1F5F9" name="Baseline (Advanced)" />
                        <Area type="monotone" dataKey="spend" stroke="#6D28D9" fill="#EDE9FE" strokeWidth={2} name="NEXUS Optimized" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Chart 2: Model Tier Distribution */}
                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-sm font-bold text-[#1E1B4B]">Model Tier Distribution</h4>
                      <p className="text-xs text-[#64748B]">Workload share across Small, Medium, and Advanced</p>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-[#EDE9FE] text-[#6D28D9]">550 Requests</span>
                  </div>
                  <div className="h-64 w-full flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={[
                            { name: 'Small Tier (GPT-4o Mini)', value: 197 },
                            { name: 'Medium Tier (GPT-4o)', value: 271 },
                            { name: 'Advanced Tier (o1)', value: 82 }
                          ]}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={90}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {PIE_COLORS.map((color, index) => (
                            <Cell key={`cell-${index}`} fill={color} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Chart 3: Cost by Model Tier */}
                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-sm font-bold text-[#1E1B4B]">Cost by Model Tier</h4>
                      <p className="text-xs text-[#64748B]">Monthly spend distribution across tiers (INR)</p>
                    </div>
                  </div>
                  <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={[
                          { tier: 'Small Tier', spend: 45.2, baseline: 180.0 },
                          { tier: 'Medium Tier', spend: 214.8, baseline: 420.0 },
                          { tier: 'Advanced Tier', spend: 360.0, baseline: 400.0 }
                        ]}
                        margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="tier" stroke="#94A3B8" fontSize={11} />
                        <YAxis stroke="#94A3B8" fontSize={11} />
                        <Tooltip />
                        <Bar dataKey="spend" fill="#6D28D9" radius={[4, 4, 0, 0]} name="Actual Spend" />
                        <Bar dataKey="baseline" fill="#CBD5E1" radius={[4, 4, 0, 0]} name="Unoptimized Baseline" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Chart 4: Department Spend vs Budget */}
                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-sm font-bold text-[#1E1B4B]">Department Spend vs Budget</h4>
                      <p className="text-xs text-[#64748B]">Budget utilization per department (INR)</p>
                    </div>
                  </div>
                  <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={[
                          { dept: 'Engineering', spend: 265.0, budget: 3500.0 },
                          { dept: 'Finance', spend: 195.0, budget: 1000.0 },
                          { dept: 'Marketing', spend: 115.0, budget: 1800.0 },
                          { dept: 'HR', spend: 45.0, budget: 600.0 }
                        ]}
                        margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="dept" stroke="#94A3B8" fontSize={11} />
                        <YAxis stroke="#94A3B8" fontSize={11} />
                        <Tooltip />
                        <Bar dataKey="spend" fill="#8B5CF6" radius={[4, 4, 0, 0]} name="Spend" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Chart 5: Quality vs Cost Comparison */}
                <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs lg:col-span-2">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-sm font-bold text-[#1E1B4B]">Model Tier Quality & Latency Trade-Off Matrix</h4>
                      <p className="text-xs text-[#64748B]">Measured quality scores, execution latency, and price per 1k tokens</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {qualityPoints.map((pt, idx) => (
                      <div key={idx} className="bg-[#F8FAFC] p-4 rounded-xl border border-[#E5E7EB]">
                        <div className="flex justify-between items-center">
                          <span className="text-xs font-bold text-[#6D28D9]">{pt.tier} Tier</span>
                          <span className="text-xs font-mono font-bold text-[#1E1B4B]">₹{pt.cost_per_1k} / 1k</span>
                        </div>
                        <p className="text-xs text-[#64748B] mt-1">{pt.model}</p>
                        <div className="mt-3 space-y-1.5 text-xs">
                          <div className="flex justify-between">
                            <span className="text-[#64748B]">Quality:</span>
                            <span className="font-semibold text-emerald-600">{pt.quality_score}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-[#64748B]">Latency:</span>
                            <span className="font-mono text-[#1E1B4B]">{pt.latency_ms} ms</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-[#64748B]">Volume:</span>
                            <span className="font-mono text-[#64748B]">{pt.requests_count} calls</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ================================================================ */}
          {/* TAB 2: AI REQUEST PLAYGROUND (Primary Live real) */}
          {/* ================================================================ */}
          {activeTab === 'playground' && (
            <div className="space-y-6">
              {/* Primary Playground Card */}
              <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 md:p-8 shadow-xs space-y-5">
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-[#6D28D9]" />
                    <h3 className="text-lg font-bold text-[#1E1B4B]">AI Request Playground</h3>
                  </div>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    Test live intelligent routing, guardrail verification, semantic caching, and unit economics.
                  </p>
                </div>

                {/* 1-Click Example Queries */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                      Try Example Queries (Auto-Routed):
                    </span>
                    <span className="text-[10px] text-[#6D28D9] font-semibold bg-[#F5F3FF] px-2.5 py-0.5 rounded-full border border-[#EDE9FE]">
                      Zero Configuration Required &bull; Auto Model Selection
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => {
                        setPrompt('Explain what is a linked list in simple terms')
                        setCustomBudgetLimit(null)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-[#F8FAFC] hover:bg-[#F5F3FF] text-[#1E1B4B] hover:text-[#6D28D9] border border-[#E2E8F0] hover:border-[#DDD6FE] transition-all cursor-pointer shadow-2xs"
                    >
                      💡 Linked List in Simple Terms <span className="text-[10px] text-[#6D28D9] font-bold">&rarr; Small Tier</span>
                    </button>
                    <button
                      onClick={() => {
                        setPrompt('Explain recursion with an example.')
                        setCustomBudgetLimit(null)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-[#F8FAFC] hover:bg-[#F5F3FF] text-[#1E1B4B] hover:text-[#6D28D9] border border-[#E2E8F0] hover:border-[#DDD6FE] transition-all cursor-pointer shadow-2xs"
                    >
                      ⚙️ Recursion with Example <span className="text-[10px] text-[#6D28D9] font-bold">&rarr; Medium Tier</span>
                    </button>
                    <button
                      onClick={() => {
                        setPrompt('Analyze this complex financial report and identify potential fraud patterns.')
                        setCustomBudgetLimit(null)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-[#F8FAFC] hover:bg-[#F5F3FF] text-[#1E1B4B] hover:text-[#6D28D9] border border-[#E2E8F0] hover:border-[#DDD6FE] transition-all cursor-pointer shadow-2xs"
                    >
                      🛡️ Financial Fraud Audit <span className="text-[10px] text-[#6D28D9] font-bold">&rarr; Advanced Tier</span>
                    </button>
                    <button
                      onClick={() => {
                        setPrompt('Translate this sentence into Tamil: AI is changing the future of software development.')
                        setCustomBudgetLimit(null)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-[#F8FAFC] hover:bg-[#F5F3FF] text-[#1E1B4B] hover:text-[#6D28D9] border border-[#E2E8F0] hover:border-[#DDD6FE] transition-all cursor-pointer shadow-2xs"
                    >
                      🌐 Translation into Tamil <span className="text-[10px] text-[#6D28D9] font-bold">&rarr; Small Tier</span>
                    </button>
                    <button
                      onClick={() => {
                        setPrompt('Explain cloud computing in simple terms.')
                        setCustomBudgetLimit(null)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-[#F8FAFC] hover:bg-[#F5F3FF] text-[#1E1B4B] hover:text-[#6D28D9] border border-[#E2E8F0] hover:border-[#DDD6FE] transition-all cursor-pointer shadow-2xs"
                    >
                      ⚡ Cache Step 1: Query <span className="text-[10px] text-amber-600 font-bold">&rarr; Cache MISS</span>
                    </button>
                    <button
                      onClick={() => {
                        setPrompt('Can you explain cloud computing simply?')
                        setCustomBudgetLimit(null)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-emerald-50/60 hover:bg-emerald-100/60 text-emerald-900 border border-emerald-200 transition-all cursor-pointer shadow-2xs"
                    >
                      ⚡ Cache Step 2: Paraphrase <span className="text-[10px] text-emerald-700 font-bold">&rarr; Cache HIT (0ms, ₹0)</span>
                    </button>
                    <button
                      onClick={() => {
                        setPrompt('Draft an executive policy memo for quarterly infrastructure cost governance.')
                        setCustomBudgetLimit(null)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-[#F8FAFC] hover:bg-[#F5F3FF] text-[#1E1B4B] hover:text-[#6D28D9] border border-[#E2E8F0] hover:border-[#DDD6FE] transition-all cursor-pointer shadow-2xs"
                    >
                      🎯 Guardrail Fallback <span className="text-[10px] text-[#6D28D9] font-bold">&rarr; Auto Upgrade</span>
                    </button>
                    <button
                      onClick={() => {
                        setPrompt('Execute advanced deep reasoning audit on historical multi-cloud invoices.')
                        setCustomBudgetLimit(0.01)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-amber-50/60 hover:bg-amber-100/60 text-amber-900 border border-amber-200 transition-all cursor-pointer shadow-2xs"
                    >
                      💰 Low Budget Constraint <span className="text-[10px] text-amber-700 font-bold">&rarr; Budget Guard</span>
                    </button>
                    <button
                      onClick={() => {
                        setPrompt('[SIMULATE_FAIL] Execute high-frequency cluster scaling simulation.')
                        setCustomBudgetLimit(null)
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-medium bg-rose-50/60 hover:bg-rose-100/60 text-rose-900 border border-rose-200 transition-all cursor-pointer shadow-2xs"
                    >
                      🚨 Simulated Error <span className="text-[10px] text-rose-700 font-bold">&rarr; Auto Fallback</span>
                    </button>
                  </div>
                </div>

                {/* Prompt Textarea */}
                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="text-xs font-bold text-[#1E1B4B] flex items-center gap-1.5">
                      Enter Query
                      <span className="text-[10px] font-normal text-[#64748B]">(System automatically extracts task, complexity, quality target & SLA)</span>
                    </label>
                    {prompt && (
                      <button
                        onClick={() => {
                          setPrompt('')
                          setChatResult(null)
                          setChatError(null)
                        }}
                        className="text-[11px] text-[#64748B] hover:text-[#6D28D9] cursor-pointer"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                  <textarea
                    rows={3}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Enter what you want AI to do (e.g. 'Explain what is a linked list in simple terms')..."
                    className="w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-4 text-sm text-[#1E1B4B] focus:outline-none focus:border-[#6D28D9] focus:bg-white resize-none shadow-2xs transition-all placeholder:text-[#94A3B8]"
                  />
                </div>

                {/* Autonomous Routing Banner & Execution Bar */}
                <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-[#E5E7EB]">
                  <div className="flex items-center gap-4 text-xs text-[#64748B]">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={useCache}
                        onChange={(e) => setUseCache(e.target.checked)}
                        className="rounded border-[#E5E7EB] text-[#6D28D9] focus:ring-0"
                      />
                      <span>Enable Semantic Cache</span>
                    </label>

                    {customBudgetLimit !== null && (
                      <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 text-[11px] flex items-center gap-1 font-mono">
                        <AlertTriangle className="w-3 h-3" />
                        Remaining Budget: ₹0.02
                        <button
                          onClick={() => setCustomBudgetLimit(null)}
                          className="ml-1 text-amber-900 font-bold hover:underline"
                        >
                          &times;
                        </button>
                      </span>
                    )}
                  </div>

                  <button
                    onClick={handleExecute}
                    disabled={executing || !prompt.trim()}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl bg-[#6D28D9] hover:bg-[#5B21B6] text-white font-bold text-xs tracking-wider shadow-md shadow-violet-200 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {executing ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>PROCESSING...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span>ROUTE &amp; EXECUTE</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Dynamic Loading Step Indicator */}
                {executing && (
                  <div className="p-4 bg-[#F5F3FF] border border-[#EDE9FE] rounded-xl flex items-center gap-3 animate-in fade-in">
                    <RefreshCw className="w-4 h-4 text-[#6D28D9] animate-spin shrink-0" />
                    <div>
                      <span className="text-xs font-bold text-[#6D28D9] block">Execution Pipeline Running:</span>
                      <p className="text-xs text-[#1E1B4B] font-mono mt-0.5">{EXECUTION_STEPS[execStepIdx]}</p>
                    </div>
                  </div>
                )}

                {/* Error Banner */}
                {chatError && (
                  <div className="p-3.5 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
                    <span>{chatError}</span>
                  </div>
                )}
              </div>

              {/* Execution Outcome Container */}
              {chatResult && (
                <div className="space-y-6 animate-in fade-in">
                  {/* Cache & Fallback Status Banner */}
                  <div className="flex flex-wrap gap-3">
                    {chatResult.cache_hit ? (
                      <div className="flex-1 p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between">
                        <div className="flex items-center gap-2 font-bold">
                          <Zap className="w-4 h-4 text-emerald-600" />
                          <span>CACHE HIT &bull; Response served from semantic cache.</span>
                        </div>
                        <div className="font-mono text-emerald-700">
                          Cost avoided: <strong>₹{chatResult.baseline_comparison?.baseline_cost.toFixed(4) ?? '0.05'}</strong> &bull; Tokens avoided: {chatResult.total_tokens}
                        </div>
                      </div>
                    ) : (
                      <div className="p-2.5 px-3.5 rounded-xl bg-[#F8FAFC] border border-[#E5E7EB] text-[#64748B] text-xs flex items-center gap-2">
                        <span>CACHE MISS &bull; Model invocation executed.</span>
                      </div>
                    )}

                    {chatResult.fallback_used && (
                      <div className="w-full p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1">
                        <div className="flex items-center gap-2 font-bold text-amber-800">
                          <AlertTriangle className="w-4 h-4" />
                          <span>FALLBACK TRIGGERED</span>
                        </div>
                        <p className="text-amber-800/90 pl-6">
                          Initial Model: <strong>{chatResult.selected_model}</strong> &bull; Reason: {chatResult.fallback_details?.fallback_reason || 'Quality below required threshold'} &bull; Fallback Model: <strong>{chatResult.final_model}</strong> &bull; Final Quality: <strong>{chatResult.quality_score}%</strong> &bull; Status: <strong className="text-emerald-700">SUCCESS</strong>
                        </p>
                      </div>
                    )}
                  </div>

                  {/* 4 Core Results Columns */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* 1. Request Analysis */}
                    <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 shadow-xs">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED]">
                          1. Request Analysis
                        </span>
                        <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-violet-50 text-[#6D28D9] border border-violet-100">
                          AUTO-DETECTED
                        </span>
                      </div>
                      <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Task:</span>
                          <span className="font-semibold text-[#1E1B4B] capitalize">
                            {chatResult.analysis?.task_type.replace('_', ' ') || 'General'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Complexity:</span>
                          <span
                            className={`font-bold ${chatResult.analysis?.complexity === 'HIGH'
                                ? 'text-rose-600'
                                : chatResult.analysis?.complexity === 'MEDIUM'
                                  ? 'text-amber-600'
                                  : 'text-emerald-600'
                              }`}
                          >
                            {chatResult.analysis?.complexity || (chatResult.quality_score > 90 ? 'HIGH' : 'LOW')}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Sensitivity:</span>
                          <span className="font-semibold text-[#1E1B4B]">
                            {chatResult.analysis?.sensitivity || 'PUBLIC'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Req Quality:</span>
                          <span className="font-mono font-bold text-[#6D28D9]">
                            {chatResult.analysis?.required_quality ? `${chatResult.analysis.required_quality}%` : `${chatResult.quality_score}%`}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Tokens:</span>
                          <span className="font-mono text-[#1E1B4B]">
                            {chatResult.input_tokens} in / {chatResult.output_tokens} out
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Latency SLA:</span>
                          <span className="font-mono text-[11px] text-[#64748B]">
                            {chatResult.analysis?.latency_requirement?.split(' ')[0] || 'INTERACTIVE'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* 2. Routing Decision */}
                    <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 shadow-xs">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED] block mb-2">2. Routing Decision</span>
                      <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between items-center">
                          <span className="text-[#64748B]">Selected Model:</span>
                          <span className="font-bold text-xs px-2 py-0.5 rounded bg-[#EDE9FE] text-[#6D28D9]">
                            {chatResult.final_model.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#64748B] pt-1 leading-tight">
                          {chatResult.routing_reason[0] || 'Lowest cost valid model satisfying constraints.'}
                        </p>
                      </div>
                    </div>

                    {/* 3. Execution Telemetry */}
                    <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 shadow-xs">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED] block mb-2">3. Execution</span>
                      <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Tokens:</span>
                          <span className="font-mono text-[#1E1B4B]">{chatResult.total_tokens} ({chatResult.input_tokens}in/{chatResult.output_tokens}out)</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Latency:</span>
                          <span className="font-mono text-[#1E1B4B]">{chatResult.latency_ms.toFixed(1)} ms</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Cost:</span>
                          <span className="font-mono font-bold text-emerald-600">₹{chatResult.cost.toFixed(4)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Quality:</span>
                          <span className="font-bold text-[#6D28D9]">{chatResult.quality_score}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Status:</span>
                          <span className={`font-bold ${chatResult.success ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {chatResult.success ? 'SUCCESS' : 'BLOCKED'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* 4. Cost Optimization */}
                    <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 shadow-xs">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED] block mb-2">4. Cost Optimization</span>
                      <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Baseline:</span>
                          <span className="text-[#64748B]">Advanced (₹{chatResult.baseline_comparison?.baseline_cost.toFixed(4) ?? '0.00'})</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748B]">Selected:</span>
                          <span className="font-bold text-[#6D28D9]">{chatResult.final_model.toUpperCase()}</span>
                        </div>
                        <div className="flex justify-between pt-1 border-t border-[#E5E7EB]">
                          <span className="text-[#64748B]">Net Savings:</span>
                          <span className="font-mono font-bold text-emerald-600">
                            ₹{chatResult.baseline_comparison?.savings.toFixed(4) ?? '0.0000'} ({chatResult.baseline_comparison?.savings_percentage ?? 0}%)
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Routing Copilot Explanation Card */}
                  <div className="bg-white border border-[#EDE9FE] rounded-2xl p-6 shadow-xs space-y-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-[#6D28D9]" />
                      <h4 className="text-sm font-bold text-[#1E1B4B]">WHY THIS MODEL?</h4>
                    </div>
                    <div className="p-4 bg-[#F5F3FF] rounded-xl text-xs text-[#1E1B4B] font-mono leading-relaxed whitespace-pre-line border border-[#EDE9FE]">
                      {chatResult.copilot_explanation || chatResult.routing_reason.join('\n')}
                    </div>
                  </div>

                  {/* Generated Completion Text */}
                  <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs space-y-2">
                    <span className="text-xs font-bold text-[#64748B] uppercase tracking-wider block">Model Completion:</span>
                    <div className="p-4 bg-[#F8FAFC] rounded-xl border border-[#E5E7EB] text-sm text-[#1E1B4B] leading-relaxed whitespace-pre-wrap font-sans">
                      {chatResult.response}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ================================================================ */}
          {/* TAB 3: FINOPS ADVISOR UI */}
          {/* ================================================================ */}
          {activeTab === 'advisor' && (
            <div className="space-y-6">
              <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-[#6D28D9]" />
                  <h3 className="text-base font-bold text-[#1E1B4B]">Autonomous FinOps Recommendations</h3>
                </div>
                <p className="text-xs text-[#64748B] mt-0.5">
                  The FinOps Advisor continuously inspects request traces, token economics, latency curves, and quality metrics to discover actionable savings.
                </p>
              </div>

              {/* Recommendation Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {recommendations.map((rec) => {
                  const isApplied = rec.status === 'applied'
                  return (
                    <div
                      key={rec.id}
                      className={`bg-white border rounded-2xl p-6 shadow-xs flex flex-col justify-between transition-all ${isApplied ? 'border-emerald-300 bg-emerald-50/20' : 'border-[#E5E7EB]'
                        }`}
                    >
                      <div className="space-y-3">
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#EDE9FE] text-[#6D28D9]">
                            {rec.category.toUpperCase()} OPTIMIZATION
                          </span>
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded ${rec.risk === 'low'
                                ? 'bg-emerald-100 text-emerald-700'
                                : rec.risk === 'medium'
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-rose-100 text-rose-700'
                              }`}
                          >
                            Confidence: HIGH &bull; Risk: {rec.risk.toUpperCase()}
                          </span>
                        </div>

                        <h4 className="text-sm font-bold text-[#1E1B4B]">{rec.title}</h4>

                        <div className="space-y-1.5 text-xs text-[#64748B]">
                          <p><strong className="text-[#1E1B4B]">Problem:</strong> {rec.issue}</p>
                          <p><strong className="text-[#1E1B4B]">Observation:</strong> {rec.observation}</p>
                          <p><strong className="text-[#6D28D9]">Recommendation:</strong> {rec.recommendation}</p>
                        </div>
                      </div>

                      <div className="pt-5 mt-5 border-t border-[#E5E7EB] flex items-center justify-between">
                        <div>
                          <span className="text-[10px] text-[#64748B] uppercase font-semibold block">Potential Savings</span>
                          <span className="text-base font-black text-emerald-600">₹{rec.estimated_savings}/month</span>
                          <span className="text-[10px] text-[#64748B] block mt-0.5">Quality impact: {rec.quality_impact}%</span>
                        </div>

                        <button
                          onClick={() => handleApplyRec(rec.id)}
                          disabled={isApplied}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${isApplied
                              ? 'bg-emerald-100 text-emerald-700 cursor-default'
                              : 'bg-[#6D28D9] hover:bg-[#5B21B6] text-white shadow-xs shadow-violet-200'
                            }`}
                        >
                          {isApplied ? '✓ Policy Updated Successfully' : 'REVIEW & APPLY'}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* ================================================================ */}
          {/* TAB 4: WHAT-IF MODEL SIMULATOR */}
          {/* ================================================================ */}
          {activeTab === 'simulator' && (
            <div className="space-y-6">
              <div className="bg-white border border-[#E5E7EB] rounded-2xl p-6 shadow-xs space-y-4">
                <div>
                  <div className="flex items-center gap-2">
                    <Sliders className="w-5 h-5 text-[#6D28D9]" />
                    <h3 className="text-base font-bold text-[#1E1B4B]">What-If Model Simulator</h3>
                  </div>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    Compare cost, quality, and latency trade-offs between Small, Medium, and Advanced model tiers before making routing decisions.
                  </p>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="text-xs font-semibold text-[#1E1B4B] block mb-1">Test Prompt</label>
                    <textarea
                      rows={2}
                      value={simPrompt}
                      onChange={(e) => setSimPrompt(e.target.value)}
                      className="w-full bg-[#F8FAFC] border border-[#E5E7EB] rounded-xl p-3 text-xs text-[#1E1B4B] focus:outline-none focus:border-[#6D28D9]"
                    />
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-semibold text-[#1E1B4B]">
                        Required Quality Threshold: <strong className="text-[#6D28D9]">{simQuality}%</strong>
                      </span>
                      <input
                        type="range"
                        min={70}
                        max={98}
                        value={simQuality}
                        onChange={(e) => setSimQuality(Number(e.target.value))}
                        className="w-36 accent-[#6D28D9] cursor-pointer"
                      />
                    </div>

                    <button
                      onClick={handleSimulate}
                      disabled={simulating || !simPrompt.trim()}
                      className="px-5 py-2.5 rounded-xl bg-[#6D28D9] hover:bg-[#5B21B6] text-white text-xs font-bold shadow-xs shadow-violet-200 transition-all cursor-pointer"
                    >
                      {simulating ? 'SIMULATING...' : 'COMPARE MODEL TIERS'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Simulation Matrix */}
              {simResult && (
                <div className="space-y-6 animate-in fade-in">
                  {/* Recommended Winner Card */}
                  <div className="bg-gradient-to-r from-[#F5F3FF] to-white border-2 border-[#6D28D9] rounded-2xl p-6 shadow-xs">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C3AED]">Simulator Recommendation</span>
                        <h4 className="text-lg font-black text-[#1E1B4B] mt-1">
                          RECOMMENDED: {simResult.recommended_tier} MODEL
                        </h4>
                        <p className="text-xs text-[#64748B] mt-1">{simResult.recommendation_reason}</p>
                      </div>

                      <div className="text-right">
                        <span className="text-xs text-[#64748B]">Savings vs Advanced:</span>
                        <p className="text-xl font-black text-emerald-600">
                          ₹{simResult.estimated_savings_vs_advanced.toFixed(4)} ({simResult.savings_percentage}%)
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* 3 Tier Comparison Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    {simResult.comparisons.map((c) => {
                      const isRecommended = c.tier === simResult.recommended_tier
                      return (
                        <div
                          key={c.tier}
                          className={`bg-white border rounded-2xl p-6 shadow-xs space-y-4 ${isRecommended ? 'border-2 border-[#6D28D9] bg-[#F5F3FF]/40' : 'border-[#E5E7EB]'
                            }`}
                        >
                          <div className="flex justify-between items-center">
                            <span className="text-sm font-bold text-[#1E1B4B]">{c.tier}</span>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded ${c.is_valid
                                  ? 'bg-emerald-100 text-emerald-700'
                                  : 'bg-rose-100 text-rose-700'
                                }`}
                            >
                              {c.status_label}
                            </span>
                          </div>

                          <div className="space-y-2 text-xs border-y border-[#E5E7EB] py-3">
                            <div className="flex justify-between">
                              <span className="text-[#64748B]">Estimated Cost:</span>
                              <span className="font-mono font-bold text-[#1E1B4B]">₹{c.estimated_cost.toFixed(4)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-[#64748B]">Estimated Quality:</span>
                              <span className="font-bold text-[#6D28D9]">{c.estimated_quality}%</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-[#64748B]">Estimated Latency:</span>
                              <span className="font-mono text-[#1E1B4B]">{c.estimated_latency_ms} ms</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-[#64748B]">Estimated Tokens:</span>
                              <span className="font-mono text-[#1E1B4B]">{c.estimated_tokens}</span>
                            </div>
                          </div>

                          <p className="text-[11px] text-[#64748B] leading-tight">{c.reason}</p>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
