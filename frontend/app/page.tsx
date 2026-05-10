"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Tender = {
  id: string;
  title: string | null;
  source_url: string;
  source_portal: string | null;
  location: string | null;
  estimated_value: number | null;
  deadline: string | null;
  deadline_iso: string | null;
  days_left: number | null;
  emd: number | null;
  tender_fee: number | null;
  eligibility: string[];
  required_documents: string[];
  apply_link: string | null;
  risk_flags: string[];
  why_matches: string[];
  fit_score: number;
  recommendation: string;
};

type FinalResult = {
  summary: string;
  top_recommendation: Tender | null;
  tenders: Tender[];
  sources: string[];
  action_plan: string[];
  risk_flags: string[];
};

type Source = { url: string; title?: string };

type AgentEvent =
  | { type: "status"; message: string }
  | { type: "tool_call_started"; tool: string }
  | { type: "tool_call_completed"; tool: string; [k: string]: unknown }
  | { type: "source_discovered"; url: string; title?: string }
  | { type: "partial_results"; tenders: Tender[] }
  | { type: "final_result"; result: FinalResult };

const SAMPLE_PROMPTS = [
  "Find CCTV installation tenders in Karnataka below 25 lakh. I am an MSME vendor with GST and 2 years experience.",
  "Find solar panel installation tenders in Maharashtra below 50 lakh. I have GST, MSME, and 4 years experience. Skip EMD above 1 lakh.",
  "Show housekeeping tenders in Bengaluru under 15 lakh where MSME can apply.",
  "Find IT support tenders in Gujarat below 10 lakh, turnover requirement under 50 lakh.",
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function formatINR(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(2)} Cr`;
  if (n >= 100_000) return `₹${(n / 100_000).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

function recommendationColor(rec: string): string {
  switch (rec) {
    case "Apply":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "Maybe Apply":
      return "bg-blue-100 text-blue-800 border-blue-200";
    case "Review Carefully":
      return "bg-amber-100 text-amber-800 border-amber-200";
    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
}

function StepRow({ status, label, done }: { status: "pending" | "active" | "done"; label: string; done?: string }) {
  const icon =
    status === "done" ? (
      <span className="text-emerald-600">✓</span>
    ) : status === "active" ? (
      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-accent" />
    ) : (
      <span className="inline-block h-2 w-2 rounded-full bg-slate-300" />
    );
  return (
    <div className="flex items-center gap-3 py-1.5 text-sm">
      <span className="flex h-5 w-5 items-center justify-center">{icon}</span>
      <span className={status === "pending" ? "text-muted" : "text-ink"}>{label}</span>
      {done && <span className="text-xs text-muted">— {done}</span>}
    </div>
  );
}

function TenderCard({ t }: { t: Tender }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-panel p-5 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted">
            {t.source_portal && <span className="rounded-full bg-slate-100 px-2 py-0.5">{t.source_portal}</span>}
            {t.location && <span>{t.location}</span>}
          </div>
          <h3 className="text-base font-semibold leading-snug text-ink">
            {t.title || t.source_url}
          </h3>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <div className="text-2xl font-bold tabular-nums text-ink">{t.fit_score}</div>
          <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${recommendationColor(t.recommendation)}`}>
            {t.recommendation}
          </span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
        <div>
          <div className="text-xs text-muted">Estimated value</div>
          <div className="font-medium text-ink">{formatINR(t.estimated_value)}</div>
        </div>
        <div>
          <div className="text-xs text-muted">EMD</div>
          <div className="font-medium text-ink">{formatINR(t.emd)}</div>
        </div>
        <div>
          <div className="text-xs text-muted">Tender fee</div>
          <div className="font-medium text-ink">{formatINR(t.tender_fee)}</div>
        </div>
        <div>
          <div className="text-xs text-muted">Deadline</div>
          <div className="font-medium text-ink">
            {t.deadline_iso || t.deadline || "—"}
            {typeof t.days_left === "number" && (
              <span
                className={`ml-2 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  t.days_left < 0
                    ? "bg-red-100 text-red-700"
                    : t.days_left <= 3
                    ? "bg-amber-100 text-amber-800"
                    : "bg-emerald-100 text-emerald-800"
                }`}
              >
                {t.days_left < 0 ? `${Math.abs(t.days_left)}d ago` : `${t.days_left}d left`}
              </span>
            )}
          </div>
        </div>
      </div>

      {t.why_matches && t.why_matches.length > 0 && (
        <div className="mt-4">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">Why this matches</div>
          <ul className="list-disc space-y-0.5 pl-5 text-sm text-ink">
            {t.why_matches.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {t.eligibility.length > 0 && (
        <div className="mt-4">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">Eligibility signals</div>
          <div className="flex flex-wrap gap-1.5">
            {t.eligibility.map((e, i) => (
              <span key={i} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-800">
                {e}
              </span>
            ))}
          </div>
        </div>
      )}

      {t.risk_flags.length > 0 && (
        <div className="mt-3">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">Risk flags</div>
          <ul className="list-disc pl-5 text-xs text-amber-800">
            {t.risk_flags.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
        <a
          className="text-accent hover:underline"
          href={t.source_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          View source ↗
        </a>
        {t.apply_link && (
          <a
            className="text-accent hover:underline"
            href={t.apply_link}
            target="_blank"
            rel="noopener noreferrer"
          >
            Apply link ↗
          </a>
        )}
      </div>
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [steps, setSteps] = useState<{ id: string; label: string; status: "pending" | "active" | "done"; done?: string }[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [final, setFinal] = useState<FinalResult | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const updateStep = useCallback((id: string, label: string, status: "pending" | "active" | "done", done?: string) => {
    setSteps((prev) => {
      const idx = prev.findIndex((s) => s.id === id);
      if (idx === -1) return [...prev, { id, label, status, done }];
      const copy = prev.slice();
      copy[idx] = { id, label, status, done: done ?? copy[idx].done };
      return copy;
    });
  }, []);

  const handleEvent = useCallback(
    (eventName: string, payload: any) => {
      if (eventName === "status") {
        const id = `status-${steps.length}`;
        updateStep(id, payload.message, "active");
        // Mark previous status step as done
        setSteps((prev) => {
          const out = prev.slice();
          for (let i = out.length - 2; i >= 0; i--) {
            if (out[i].id.startsWith("status-") && out[i].status === "active") {
              out[i] = { ...out[i], status: "done" };
              break;
            }
          }
          return out;
        });
      } else if (eventName === "tool_call_started") {
        updateStep(`tool-${payload.tool}`, `Running ${payload.tool}`, "active");
      } else if (eventName === "tool_call_completed") {
        const detail = payload.error
          ? `error: ${payload.error}`
          : payload.urls_found != null
          ? `${payload.urls_found} URLs`
          : payload.pages != null
          ? `${payload.pages} pages`
          : payload.kept != null
          ? `${payload.kept} kept, ${payload.dropped ?? 0} dropped`
          : payload.queries
          ? `${(payload.queries as string[]).length} queries`
          : payload.intent
          ? "intent parsed"
          : undefined;
        updateStep(`tool-${payload.tool}`, `Ran ${payload.tool}`, "done", detail);
        if (payload.error) {
          setErrorMsg(`${payload.tool}: ${payload.error}`);
        }
      } else if (eventName === "source_discovered") {
        setSources((prev) =>
          prev.find((s) => s.url === payload.url) ? prev : [...prev, { url: payload.url, title: payload.title }]
        );
      } else if (eventName === "partial_results") {
        setTenders(payload.tenders || []);
      } else if (eventName === "final_result") {
        setFinal(payload);
        setTenders(payload.tenders || []);
      }
    },
    [steps.length, updateStep]
  );

  const startSearch = useCallback(
    async (q: string) => {
      if (!q.trim() || q.trim().length < 5) {
        setErrorMsg("Please describe what kind of tenders you want.");
        return;
      }
      setErrorMsg(null);
      setSteps([]);
      setSources([]);
      setTenders([]);
      setFinal(null);
      setRunning(true);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      try {
        const res = await fetch(`${API_BASE}/api/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
          body: JSON.stringify({ query: q }),
          signal: ctrl.signal,
        });
        if (!res.ok || !res.body) {
          throw new Error(`Backend error ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // Split SSE messages by blank line
          let idx;
          while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const block = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            let eventName = "message";
            const dataLines: string[] = [];
            for (const raw of block.split("\n")) {
              if (raw.startsWith("event:")) eventName = raw.slice(6).trim();
              else if (raw.startsWith("data:")) dataLines.push(raw.slice(5).trim());
            }
            if (dataLines.length === 0) continue;
            try {
              const payload = JSON.parse(dataLines.join("\n"));
              handleEvent(eventName, payload);
            } catch {
              // ignore parse errors for partial frames
            }
          }
        }
      } catch (e: any) {
        if (e?.name !== "AbortError") {
          setErrorMsg(e?.message || "Something went wrong");
        }
      } finally {
        setRunning(false);
        // Mark any leftover active step as done
        setSteps((prev) => prev.map((s) => (s.status === "active" ? { ...s, status: "done" } : s)));
      }
    },
    [handleEvent]
  );

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const top = final?.top_recommendation || tenders[0] || null;

  const headline = useMemo(() => {
    if (final) return final.summary;
    if (running) return "TenderFlow is searching, scraping and ranking…";
    return "Type the contracts you want — TenderFlow finds, ranks and plans them.";
  }, [final, running]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 md:py-14">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-ink md:text-4xl">TenderFlow</h1>
        <p className="mt-2 max-w-2xl text-muted">{headline}</p>
      </header>

      <section className="mb-6 rounded-2xl border border-slate-200 bg-panel p-4 shadow-panel">
        <textarea
          className="min-h-[88px] w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
          placeholder="e.g. Find CCTV installation tenders in Karnataka below 25 lakh. I am an MSME vendor with GST and 2 years experience."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) startSearch(query);
          }}
          disabled={running}
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {SAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => setQuery(p)}
                disabled={running}
                className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-muted hover:border-accent hover:text-accent disabled:opacity-50"
              >
                {p.length > 70 ? p.slice(0, 70) + "…" : p}
              </button>
            ))}
          </div>
          <button
            onClick={() => startSearch(query)}
            disabled={running}
            className="rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-60"
          >
            {running ? "Searching…" : "Find tenders"}
          </button>
        </div>
        {errorMsg && <div className="mt-2 text-sm text-red-600">{errorMsg}</div>}
      </section>

      {(running || steps.length > 0) && (
        <section className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-panel p-5 shadow-panel md:col-span-2">
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Agent steps</div>
            <div>
              {steps.map((s) => (
                <StepRow key={s.id} status={s.status} label={s.label} done={s.done} />
              ))}
              {steps.length === 0 && <div className="text-sm text-muted">Waiting for agent…</div>}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-panel p-5 shadow-panel">
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
              Sources discovered ({sources.length})
            </div>
            <div className="max-h-64 space-y-2 overflow-auto">
              {sources.map((s) => (
                <a
                  key={s.url}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block truncate text-sm text-accent hover:underline"
                  title={s.url}
                >
                  {s.title || s.url}
                </a>
              ))}
              {sources.length === 0 && <div className="text-sm text-muted">No sources yet.</div>}
            </div>
          </div>
        </section>
      )}

      {top && (
        <section className="mb-6">
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Top recommendation</div>
          <TenderCard t={top} />
        </section>
      )}

      {tenders.length > 1 && (
        <section className="mb-6">
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Other matches</div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {tenders.slice(1).map((t) => (
              <TenderCard key={t.id} t={t} />
            ))}
          </div>
        </section>
      )}

      {final && (final.action_plan.length > 0 || final.risk_flags.length > 0) && (
        <section className="mb-12 grid grid-cols-1 gap-4 md:grid-cols-2">
          {final.action_plan.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-panel p-5 shadow-panel">
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Action plan</div>
              <ol className="list-decimal space-y-1.5 pl-5 text-sm text-ink">
                {final.action_plan.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ol>
            </div>
          )}
          {final.risk_flags.length > 0 && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-panel">
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-amber-800">Risk flags</div>
              <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">
                {final.risk_flags.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {!running && !final && tenders.length === 0 && steps.length === 0 && (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-8 text-center text-muted">
          Try one of the sample prompts above, or describe the contracts you want.
        </section>
      )}
    </main>
  );
}
