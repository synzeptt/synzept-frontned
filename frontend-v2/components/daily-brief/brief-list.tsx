export function BriefList({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) {
    return <p className="text-sm leading-6 text-stone-400">{empty}</p>;
  }

  return (
    <ul className="space-y-2.5">
      {items.map((item) => (
        <li key={item} className="flex gap-3 text-sm leading-6 text-stone-700">
          <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-stone-400" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
