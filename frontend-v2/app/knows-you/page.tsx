"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Pencil, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { emptyUnderstanding, learningSuggestionsApi, understandingApi } from "../../lib/user-understanding";
import type { LearningSuggestion, UnderstandingField, UnderstandingSectionKey, UserUnderstandingProfile } from "../../types/user-understanding";

const sections: Array<{
  key: UnderstandingSectionKey;
  title: string;
  fields: UnderstandingField[];
}> = [
  {
    key: "personal",
    title: "Personal",
    fields: [
      { key: "name", label: "Name", placeholder: "How should Synzept refer to you?" },
      { key: "bio", label: "Bio", placeholder: "A short personal context note", multiline: true },
      { key: "interests", label: "Interests", placeholder: "Topics, hobbies, or areas that matter", multiline: true },
    ],
  },
  {
    key: "professional",
    title: "Professional",
    fields: [
      { key: "role", label: "Role", placeholder: "Founder, designer, engineer..." },
      { key: "company", label: "Company", placeholder: "Company or workspace" },
      { key: "skills", label: "Skills", placeholder: "Skills Synzept should remember", multiline: true },
    ],
  },
  {
    key: "goals",
    title: "Goals",
    fields: [
      { key: "shortTermGoals", label: "Short-Term Goals", placeholder: "What you are trying to move soon", multiline: true },
      { key: "longTermGoals", label: "Long-Term Goals", placeholder: "Longer arcs Synzept should keep in view", multiline: true },
    ],
  },
  {
    key: "preferences",
    title: "Preferences",
    fields: [
      { key: "communicationStyle", label: "Communication Style", placeholder: "Concise, direct, exploratory..." },
      { key: "workStyle", label: "Work Style", placeholder: "How you prefer to plan and execute", multiline: true },
    ],
  },
  {
    key: "learning",
    title: "Learning",
    fields: [
      { key: "topicsLearning", label: "Topics Learning", placeholder: "What you are actively learning", multiline: true },
      { key: "topicsInterestedIn", label: "Topics Interested In", placeholder: "Ideas Synzept may connect to your work", multiline: true },
    ],
  },
  {
    key: "currentFocus",
    title: "Current Focus",
    fields: [
      { key: "mainFocus", label: "Main Focus", placeholder: "The main thing that matters right now", multiline: true },
      { key: "activePriorities", label: "Active Priorities", placeholder: "Open priorities, one per line", multiline: true },
    ],
  },
];

export default function KnowsYouPage() {
  const [profile, setProfile] = useState<UserUnderstandingProfile | null>(null);
  const [draft, setDraft] = useState(emptyUnderstanding);
  const [suggestions, setSuggestions] = useState<LearningSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingSuggestion, setEditingSuggestion] = useState<LearningSuggestion | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([understandingApi.get(), learningSuggestionsApi.list()])
      .then(([understanding, suggestionItems]) => {
        if (!alive) return;
        setProfile(understanding);
        setDraft(toDraft(understanding));
        setSuggestions(suggestionItems);
      })
      .catch((reason) => {
        if (!alive) return;
        setError(reason instanceof Error ? reason.message : "Synzept could not load what it knows yet.");
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const pendingSuggestions = useMemo(() => suggestions.filter((item) => item.status === "pending"), [suggestions]);

  const updateField = (section: UnderstandingSectionKey, key: string, value: string) => {
    setDraft((current) => ({
      ...current,
      [section]: {
        ...current[section],
        [key]: value,
      },
    }));
  };

  const removeField = (section: UnderstandingSectionKey, key: string) => {
    setDraft((current) => {
      const nextSection = { ...current[section] };
      delete nextSection[key];
      return { ...current, [section]: nextSection };
    });
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const clean = cleanDraft(draft);
      const updated = profile?.id && !profile.id.startsWith("00000000")
        ? await understandingApi.update(clean)
        : await understandingApi.create(clean);
      setProfile(updated);
      setDraft(toDraft(updated));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Synzept could not save your understanding.");
    } finally {
      setSaving(false);
    }
  };

  const acceptSuggestion = async (suggestion: LearningSuggestion) => {
    setError(null);
    try {
      const updated = await learningSuggestionsApi.accept(suggestion.id);
      setSuggestions((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      const understanding = await understandingApi.get();
      setProfile(understanding);
      setDraft(toDraft(understanding));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Synzept could not accept that suggestion.");
    }
  };

  const ignoreSuggestion = async (suggestion: LearningSuggestion) => {
    setError(null);
    try {
      const updated = await learningSuggestionsApi.ignore(suggestion.id);
      setSuggestions((items) => items.map((item) => (item.id === updated.id ? updated : item)));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Synzept could not ignore that suggestion.");
    }
  };

  const saveSuggestionEdit = async (suggestion: LearningSuggestion) => {
    setError(null);
    try {
      const updated = await learningSuggestionsApi.edit(suggestion.id, {
        title: suggestion.title,
        description: suggestion.description,
      });
      setSuggestions((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setEditingSuggestion(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Synzept could not edit that suggestion.");
    }
  };

  if (loading) {
    return (
      <div className="h-full overflow-y-auto bg-[#faf9f7]">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
          <div className="h-8 w-56 animate-pulse rounded bg-stone-200" />
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-56 animate-pulse rounded-lg border border-border bg-white" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-[#faf9f7]">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-10">
        <header className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Settings</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">Synzept Knows You</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
              A transparent profile of what Synzept knows about you. You can edit or remove every field.
            </p>
          </div>
          <Button onClick={save} disabled={saving}>
            <Check className="mr-1.5 h-4 w-4" />
            {saving ? "Saving..." : "Save"}
          </Button>
        </header>

        {error && (
          <p className="mb-4 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <section className="mb-5 rounded-lg border border-border bg-white px-4 py-4 sm:px-5">
          <div className="flex items-start gap-3">
            <div className="mt-1 rounded-md bg-stone-100 p-2 text-stone-700">
              <Plus className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-stone-950">Control rule</h2>
              <p className="mt-1 text-sm leading-6 text-stone-600">
                Synzept can suggest understanding, but it never stores learned information until you accept it.
              </p>
            </div>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          {sections.map((section) => (
            <UnderstandingCard
              key={section.key}
              title={section.title}
              fields={section.fields}
              values={draft[section.key]}
              onChange={(field, value) => updateField(section.key, field, value)}
              onRemove={(field) => removeField(section.key, field)}
            />
          ))}
        </div>

        <section className="mt-5 rounded-lg border border-border bg-white px-4 py-5 sm:px-5">
          <div className="flex flex-col gap-1 border-b border-border pb-4">
            <h2 className="text-base font-semibold text-stone-950">Suggested Understanding</h2>
            <p className="text-sm leading-6 text-stone-600">Review what Synzept thinks it learned before it becomes part of your profile.</p>
          </div>

          <div className="divide-y divide-border">
            {pendingSuggestions.length === 0 && (
              <p className="py-5 text-sm text-stone-500">No pending suggestions. Nothing has been learned automatically.</p>
            )}
            {pendingSuggestions.map((suggestion) => {
              const editing = editingSuggestion?.id === suggestion.id;
              const current = editing ? editingSuggestion : suggestion;
              return (
                <div key={suggestion.id} className="py-4">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted">I think I learned</p>
                  {editing ? (
                    <div className="mt-3 space-y-3">
                      <Input
                        value={current.title}
                        onChange={(event) => setEditingSuggestion({ ...current, title: event.target.value })}
                      />
                      <Textarea
                        className="min-h-24"
                        value={current.description}
                        onChange={(event) => setEditingSuggestion({ ...current, description: event.target.value })}
                      />
                    </div>
                  ) : (
                    <>
                      <h3 className="mt-2 text-sm font-semibold text-stone-950">{suggestion.title}</h3>
                      <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-stone-600">{suggestion.description}</p>
                    </>
                  )}
                  <div className="mt-4 flex flex-wrap gap-2">
                    {editing ? (
                      <>
                        <Button size="sm" onClick={() => saveSuggestionEdit(current)}>Save edit</Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingSuggestion(null)}>Cancel</Button>
                      </>
                    ) : (
                      <>
                        <Button size="sm" onClick={() => acceptSuggestion(suggestion)}>Accept</Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingSuggestion(suggestion)}>
                          <Pencil className="mr-1.5 h-3.5 w-3.5" />
                          Edit
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => ignoreSuggestion(suggestion)}>
                          <X className="mr-1.5 h-3.5 w-3.5" />
                          Ignore
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}

function UnderstandingCard({
  title,
  fields,
  values,
  onChange,
  onRemove,
}: {
  title: string;
  fields: UnderstandingField[];
  values: Record<string, string>;
  onChange: (field: string, value: string) => void;
  onRemove: (field: string) => void;
}) {
  return (
    <section className="rounded-lg border border-border bg-white px-4 py-5 sm:px-5">
      <h2 className="text-base font-semibold text-stone-950">{title}</h2>
      <div className="mt-4 space-y-4">
        {fields.map((field) => {
          const fieldKey = field.key ?? field.title ?? field.label ?? "";
          const label = field.label ?? field.title ?? field.key ?? "";
          const value = values[fieldKey] ?? "";
          return (
            <div key={fieldKey}>
              <div className="mb-1.5 flex items-center justify-between gap-3">
                <label className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{label}</label>
                {value.trim() && (
                  <button type="button" className="text-xs text-stone-400 hover:text-red-700" onClick={() => onRemove(fieldKey)}>
                    Remove
                  </button>
                )}
              </div>
              {field.multiline ? (
                <Textarea
                  className="min-h-24 resize-y"
                  value={value}
                  placeholder={field.placeholder}
                  onChange={(event) => onChange(fieldKey, event.target.value)}
                />
              ) : (
                <Input value={value} placeholder={field.placeholder} onChange={(event) => onChange(fieldKey, event.target.value)} />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function toDraft(profile: UserUnderstandingProfile) {
  return cleanDraft({
    personal: profile.personal ?? {},
    professional: profile.professional ?? {},
    goals: profile.goals ?? {},
    preferences: profile.preferences ?? {},
    learning: profile.learning ?? {},
    currentFocus: profile.currentFocus ?? {},
  });
}

function cleanDraft(draft: typeof emptyUnderstanding) {
  return Object.fromEntries(
    Object.entries(draft).map(([section, values]) => [
      section,
      Object.fromEntries(Object.entries(values).filter(([, value]) => String(value).trim()).map(([key, value]) => [key, String(value).trim()])),
    ]),
  ) as typeof emptyUnderstanding;
}
