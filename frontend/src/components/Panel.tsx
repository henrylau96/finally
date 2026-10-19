export default function Panel({
  title,
  testId,
  children,
  ...rest
}: {
  title: string;
  testId?: string;
  children: React.ReactNode;
} & React.HTMLAttributes<HTMLElement>) {
  return (
    <section
      data-testid={testId}
      className="flex min-h-0 min-w-0 flex-col border border-border bg-surface"
      {...rest}
    >
      <h2 className="px-2 py-1 text-xs font-semibold uppercase tracking-[0.05em] text-text-muted">
        {title}
      </h2>
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </section>
  );
}
