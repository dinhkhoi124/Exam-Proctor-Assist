import { GraduationCap } from "lucide-react";
import { Link } from "react-router-dom";

export function AuthLayout({
  children,
  title,
  subtitle,
}: {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <Link to="/" className="mb-8 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary shadow-md">
          <GraduationCap className="h-6 w-6 text-primary-foreground" />
        </div>

        <div className="flex flex-col">
          <span className="text-xl font-bold text-foreground">
            FPT Exam Support
          </span>
          <span className="text-xs text-muted-foreground">
            Proctor Assistant
          </span>
        </div>
      </Link>

      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-foreground">{title}</h1>
          {subtitle && (
            <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>

        {children}
      </div>
    </div>
  );
}
