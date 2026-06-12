"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { UnderstandingCategory, UnderstandingField, UserUnderstanding } from "../../types/user-understanding";

type UnderstandingSectionProps = {
  title: string;
  description: string;
  category: UnderstandingCategory;
  fields: UnderstandingField[];
  items: UserUnderstanding[];
  saving?: boolean;
  onSave: (category: UnderstandingCategory, values: Record<string, string>) => Promise<void>;
  onDelete: (category: UnderstandingCategory, title: string) => Promise<void>;
};

export function UnderstandingSection({
  title,
  description,
  category,
  fields,
  items,
  saving,
  onSave,
  onDelete,
}: UnderstandingSectionProps) {
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    setValues(Object.fromEntries(fields.map((field) => {
      const title = field.title ?? field.label ?? field.key ?? "";
      return [title, items.find((item) => item.title === title)?.value || ""];
    })));
  }, [fields, items]);

  const save = async () => {
    await onSave(category, values);
    setEditing(false);
  };

  return (
    <section className="rounded-xl border border-border bg-white px-5 py-5 sm:px-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-stone-950">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-stone-500">{description}</p>
        </div>
        {editing ? (
          <Button size="sm" onClick={save} disabled={saving}>Save</Button>
        ) : (
          <Button size="sm" variant="outline" onClick={() => setEditing(true)}>Edit</Button>
        )}
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {fields.map((field) => {
          const title = field.title ?? field.label ?? field.key ?? "";
          const value = values[title] || "";
          return (
            <div key={title} className={field.multiline ? "sm:col-span-2" : ""}>
              <div className="flex items-center justify-between gap-2">
                <label className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{title}</label>
                {value && (
                  <button
                    type="button"
                    className="text-xs text-stone-400 transition hover:text-red-700"
                    onClick={() => void onDelete(category, title)}
                  >
                    Delete
                  </button>
                )}
              </div>
              {editing ? (
                field.multiline ? (
                  <Textarea className="mt-2 min-h-24 resize-y" value={value} placeholder={field.placeholder} onChange={(event) => setValues({ ...values, [title]: event.target.value })} />
                ) : (
                  <Input className="mt-2" value={value} placeholder={field.placeholder} onChange={(event) => setValues({ ...values, [title]: event.target.value })} />
                )
              ) : (
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-stone-700">
                  {value || <span className="text-stone-400">Nothing shared yet</span>}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
