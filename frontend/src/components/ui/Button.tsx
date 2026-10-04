import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary: "bg-gov-600 text-black hover:bg-gov-700 hover:text-white border-ink",
  secondary: "bg-white text-ink hover:bg-gov-50 border-ink",
  ghost: "bg-transparent text-ink hover:bg-gov-50 border-transparent",
  danger: "bg-red-600 text-white hover:bg-red-700 border-ink"
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  icon?: ReactNode;
}

export function Button({ variant = "secondary", icon, className = "", children, ...props }: ButtonProps) {
  return (
    <button
      className={`focus-ring inline-flex min-h-10 items-center justify-center gap-2 rounded-md border-2 px-3.5 py-2 text-sm font-bold uppercase tracking-wide transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
