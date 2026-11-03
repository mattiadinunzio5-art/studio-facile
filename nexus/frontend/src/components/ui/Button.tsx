import { forwardRef, type ButtonHTMLAttributes } from 'react';

const variants = {
  primary: 'bg-gold-400 text-ink-950 hover:bg-gold-300 disabled:bg-ink-600 disabled:text-steel-400',
  secondary: 'border border-ink-600 text-paper hover:border-steel-500 hover:bg-ink-800 disabled:text-steel-500',
  ghost: 'text-steel-300 hover:bg-ink-800 hover:text-paper disabled:text-steel-500',
  danger: 'bg-bad text-ink-950 hover:brightness-110 disabled:opacity-50',
} as const;

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof variants };

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = 'secondary', className = '', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      {...props}
      className={`inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed ${variants[variant]} ${className}`}
    />
  );
});
