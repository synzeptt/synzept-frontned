"use client";

import { useState } from "react";
import { BarChart3, BrainCircuit, CheckCircle2, Clock, MessageSquareWarning, Target, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { learningEvaluationMock } from "@/lib/learning-evaluation/mock-data";
import type { Recommendation } from "@/lib/learning-evaluation/types";

const feedbackOptions = ["Helpful", "Incorrect", "Outdated", "Incomplete"];

export function LearningEvaluationView() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>(learningEvaluationMock.recommendations);
  const [feedbackLog, setFeedbackLog] = useState<string[]>([]);

  function markFeedback(recommendationId: string, feedback: string) {
    setRecommendations((items) => items.map((item) => (item.id === recommendationId ? { ...item, status: feedback.toLowerCase() } : item)));
    setFeedbackLog((items) => [`${recommendationId}: ${feedback}`, ...items].slice(0, 4));
  }

  return (
    <div className="min-h-full bg-zinc-50 text-zinc-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-muted">
            <BrainCircuit className="h-4 w-4" />
            Sprint 3 Learning & Evaluation
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">Close the loop on every recommendation</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
            Compare predictions with outcomes, extract lessons, and update the Decision Profile for better future recommendations.
          </p>
        </header>

        <section className="grid gap-3 md:grid-cols-5">
          <Metric icon={<Target className="h-4 w-4" />} label="Accuracy" value={`${Math.round(learningEvaluationMock.metrics.predictionAccuracy * 100)}%`} />
          <Metric icon={<CheckCircle2 className="h-4 w-4" />} label="Accepted" value={`${Math.round(learningEvaluationMock.metrics.recommendationAcceptanceRate * 100)}%`} />
          <Metric icon={<TrendingUp className="h-4 w-4" />} label="Success" value={`${Math.round(learningEvaluationMock.metrics.recommendationSuccessRate * 100)}%`} />
          <Metric icon={<Clock className="h-4 w-4" />} label="Outcome time" value={`${learningEvaluationMock.metrics.averageTimeToOutcomeHours}h`} />
          <Metric icon={<BarChart3 className="h-4 w-4" />} label="Feedback" value={`${Math.round(learningEvaluationMock.metrics.userFeedbackScore * 100)}%`} />
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <main className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <h2 className="text-lg font-semibold">Recommendation History</h2>
              <div className="mt-4 space-y-3">
                {recommendations.map((recommendation) => (
                  <article key={recommendation.id} className="rounded-lg border border-border bg-surface p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{recommendation.status}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{Math.round(recommendation.confidence * 100)}% confidence</span>
                        </div>
                        <h3 className="mt-3 text-base font-semibold">{recommendation.title}</h3>
                        <p className="mt-2 text-sm leading-6 text-zinc-700">{recommendation.recommendation}</p>
                        <p className="mt-2 text-xs text-muted-foreground">Reasoning: {recommendation.reasoningPlanId} {recommendation.decisionId ? `- Decision: ${recommendation.decisionId}` : ""}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 lg:max-w-56 lg:justify-end">
                        {feedbackOptions.map((option) => (
                          <Button key={option} variant="outline" onClick={() => markFeedback(recommendation.id, option)}>
                            {option}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="grid gap-5 lg:grid-cols-2">
              <Panel title="Accuracy Trends">
                {learningEvaluationMock.evaluations.map((evaluation) => (
                  <Bar key={evaluation.id} label={evaluation.recommendationId} value={evaluation.predictionAccuracy} />
                ))}
              </Panel>
              <Panel title="Confidence Calibration">
                {learningEvaluationMock.confidenceHistory.map((point) => (
                  <Bar key={point.id} label={point.reason} value={point.confidence} />
                ))}
              </Panel>
            </section>
          </main>

          <aside className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="text-lg font-semibold">Lessons Learned</h2>
              <div className="mt-3 space-y-3">
                {learningEvaluationMock.lessons.map((lesson) => (
                  <article key={lesson.id} className="rounded-md bg-surface p-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold">{lesson.title}</p>
                      <span className={`rounded-full px-2.5 py-1 text-xs ${lesson.confidenceDelta >= 0 ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>
                        {lesson.confidenceDelta >= 0 ? "+" : ""}{Math.round(lesson.confidenceDelta * 100)}%
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{lesson.lesson}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="text-lg font-semibold">Decision Profile</h2>
              <Bar label="Calibration" value={learningEvaluationMock.decisionProfile.calibrationScore} />
              <List title="Strengths" items={learningEvaluationMock.decisionProfile.strengths} />
              <List title="Blind spots" items={learningEvaluationMock.decisionProfile.blindSpots} />
              <List title="Preferences" items={learningEvaluationMock.decisionProfile.recommendationPreferences} />
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <MessageSquareWarning className="h-5 w-5" />
                Feedback Log
              </h2>
              <div className="mt-3 space-y-2">
                {(feedbackLog.length ? feedbackLog : ["No new feedback this session."]).map((entry) => (
                  <p key={entry} className="rounded-md bg-surface p-3 text-sm text-muted-foreground">{entry}</p>
                ))}
              </div>
            </section>
          </aside>
        </section>
      </div>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-white p-4 shadow-soft">
      <div className="flex items-center gap-2 text-muted">{icon}<span className="text-xs uppercase tracking-[0.12em]">{label}</span></div>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span className="line-clamp-1">{label}</span>
        <span>{Math.round(value * 100)}%</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-zinc-100">
        <div className="h-2 rounded-full bg-zinc-900" style={{ width: `${Math.max(4, Math.round(value * 100))}%` }} />
      </div>
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="mt-4">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{title}</p>
      <div className="mt-2 space-y-2">
        {items.map((item) => <p key={item} className="rounded-md bg-surface p-2 text-sm text-zinc-700">{item}</p>)}
      </div>
    </div>
  );
}
