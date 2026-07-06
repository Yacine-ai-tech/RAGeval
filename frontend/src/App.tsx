import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Gauge, ListTree, FlaskConical, Beaker, CircleDollarSign, BellRing, Code2 } from "lucide-react";
import { AppShell } from "./kit/AppShell";
import { WakingBackend } from "./kit/misc";
import { Skeleton } from "./kit/primitives";
import { api } from "./lib/api";
import Queries from "./pages/Queries";
import Evaluate from "./pages/Evaluate";
import Experiments from "./pages/Experiments";
import Alerts from "./pages/Alerts";
import Instrumentation from "./pages/Instrumentation";

const Overview = lazy(() => import("./pages/Overview"));
const Cost = lazy(() => import("./pages/Cost"));

const NAV = [
  { to: "/", label: "Overview", icon: Gauge },
  { to: "/queries", label: "Queries & Traces", icon: ListTree },
  { to: "/evaluate", label: "Evaluate", icon: FlaskConical },
  { to: "/experiments", label: "Experiments", icon: Beaker },
  { to: "/cost", label: "Cost", icon: CircleDollarSign },
  { to: "/alerts", label: "Alerts", icon: BellRing },
  { to: "/instrumentation", label: "Instrumentation", icon: Code2 },
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
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/queries" element={<Queries />} />
              <Route path="/evaluate" element={<Evaluate />} />
              <Route path="/experiments" element={<Experiments />} />
              <Route path="/cost" element={<Cost />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/instrumentation" element={<Instrumentation />} />
              <Route path="*" element={<Overview />} />
            </Routes>
          </Suspense>
        )}
      </AppShell>
    </BrowserRouter>
  );
}
