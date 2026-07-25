import UserGuidePage from './pages/UserGuidePage'
import BenchmarkPage from './pages/BenchmarkPage';
import ApiDocsPage from './pages/ApiDocsPage';
import { Component, ReactNode, lazy, Suspense, useCallback, useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Gauge, ListTree, FlaskConical, Beaker, CircleDollarSign, BellRing, Code2, RadioTower, Boxes, Bookmark , BookOpen} from "lucide-react";
import { AppShell } from "./kit/AppShell";
import { WakingBackend } from "./kit/misc";
import { Skeleton } from "./kit/primitives";
import { api } from "./lib/api";
import Queries from "./pages/Queries";
import Evaluate from "./pages/Evaluate";
import Experiments from "./pages/Experiments";
import Alerts from "./pages/Alerts";
import Instrumentation from "./pages/Instrumentation";
import Traces from "./pages/Traces";
import Models from "./pages/Models";
import Saved from "./pages/Saved";
import ApiDocs from "./pages/ApiDocs";

function lazyWithRetry<T extends React.ComponentType<any>>(
  componentImport: () => Promise<{ default: T }>
) {
  return lazy(async () => {
    const pageHasBeenRefreshed = JSON.parse(
      window.sessionStorage.getItem("retry-lazy-refreshed") || "false"
    );
    try {
      const component = await componentImport();
      window.sessionStorage.removeItem("retry-lazy-refreshed");
      return component;
    } catch (error) {
      if (!pageHasBeenRefreshed) {
        window.sessionStorage.setItem("retry-lazy-refreshed", "true");
        window.location.reload();
        return new Promise<{ default: T }>(() => {});
      }
      throw error;
    }
  });
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error("RAGeval UI Error caught by boundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center text-red-400 bg-red-950/30 rounded-xl border border-red-800/50 m-4">
          <h2 className="text-xl font-bold mb-2">Component Error</h2>
          <p className="text-sm opacity-80 mb-4">{this.state.error?.message || "An unexpected error occurred."}</p>
          <button
            onClick={() => {
              window.sessionStorage.removeItem("retry-lazy-refreshed");
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-medium rounded-lg text-sm transition"
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const Overview = lazyWithRetry(() => import("./pages/Overview"));
const Cost = lazyWithRetry(() => import("./pages/Cost"));

const NAV = [
  { to: "/", label: "Overview", icon: Gauge },
  { to: "/queries", label: "Queries", icon: ListTree },
  { to: "/traces", label: "Live Traces", icon: RadioTower },
  { to: "/evaluate", label: "Evaluate", icon: FlaskConical },
  { to: "/experiments", label: "Experiments", icon: Beaker },
  { to: "/saved", label: "Saved", icon: Bookmark },
  { to: "/models", label: "Models", icon: Boxes },
  { to: "/cost", label: "Cost", icon: CircleDollarSign },
  { to: "/alerts", label: "Alerts", icon: BellRing },
  { to: "/instrumentation", label: "Instrumentation", icon: Code2 },
  { to: "/api-docs", label: "API Docs", icon: Code2 },
  { to: "/user-guide", label: "User Guide", icon: BookOpen }
];

export default function App() {
  const [health, setHealth] = useState<"ok" | "down" | "checking">("checking");
  const [attempts, setAttempts] = useState(0);

  const check = useCallback(() => {
    setHealth("checking");
    api.health().then(() => setHealth("ok")).catch(() => setHealth("down"));
  }, []);

  useEffect(() => { check(); }, [check, attempts]);

  useEffect(() => {
    if (health === "down" && attempts < 6) {
      const t = setTimeout(() => setAttempts((a) => a + 1), 8000);
      return () => clearTimeout(t);
    }
  }, [health, attempts]);

  return (
    <BrowserRouter>
      <AppShell product="RAGeval" tagline="LLMOps Observability" nav={NAV} health={health}>
        {health !== "ok" && !(health === "checking" && attempts === 0) ? (
          <WakingBackend waking={attempts < 6} onRetry={() => setAttempts(0)} />
        ) : (
          <Suspense fallback={<Skeleton className="h-64 w-full" />}>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/queries" element={<Queries />} />
                <Route path="/traces" element={<Traces />} />
                <Route path="/models" element={<Models />} />
                <Route path="/saved" element={<Saved />} />
                <Route path="/evaluate" element={<Evaluate />} />
                <Route path="/experiments" element={<Experiments />} />
                <Route path="/cost" element={<Cost />} />
                <Route path="/alerts" element={<Alerts />} />
                <Route path="/instrumentation" element={<Instrumentation />} />
                <Route path="/api-docs" element={<ApiDocsPage />} />
                <Route path="/benchmark" element={<BenchmarkPage />} />
                <Route path="/user-guide" element={<UserGuidePage />} />
                <Route path="*" element={<Overview />} />
              </Routes>
            </ErrorBoundary>
          </Suspense>
        )}
      </AppShell>
    </BrowserRouter>
  );
}
