import type { ReactNode } from 'react';

interface CardProps {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  testId?: string;
}

export function Card({ title, action, children, className = '', testId }: CardProps) {
  return (
    <section
      data-testid={testId}
      className={`min-w-0 rounded-lg border border-ink-700 bg-ink-900 ${className}`}
    >
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-ink-700 px-4 py-3">
          <h2 className="truncate text-xs font-semibold uppercase tracking-[0.14em] text-steel-300">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
