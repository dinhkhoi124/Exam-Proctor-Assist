import { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { getApiErrorDetail, isRecord } from "@/lib/api-errors";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

import { Lock, KeyRound, ShieldCheck, CheckCircle } from "lucide-react";

import heroImage from "@/assets/exam-reset-hero.jpg";
import logoImage from "@/assets/Logo-Dai-hoc-FPT.webp";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const e: Record<string, string> = {};

    if (!password) {
      e.new_password = "Password is required";
    } else if (password.length < 6) {
      e.new_password = "Password must be at least 6 characters";
    }

    if (password !== confirmPassword) {
      e.confirm_password = "Passwords do not match";
    }

    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    try {
      setLoading(true);

      await api.post("/api/v1/auth/reset-password", {
        token,
        new_password: password,
        confirm_password: confirmPassword,
      });

      toast.success("Password reset successful!");

      navigate("/login", { replace: true });
    } catch (error) {
      const details = getApiErrorDetail(error);

      if (Array.isArray(details)) {
        const fieldErrors: Record<string, string> = {};

        details.filter(isRecord).forEach((err) => {
          const location = Array.isArray(err.loc) ? err.loc : [];
          const field = location[1];
          if (typeof field === "string" && typeof err.msg === "string") {
            fieldErrors[field] = err.msg;
          }
        });

        setErrors(fieldErrors);
      } else {
        toast.error(
          typeof details === "string" ? details : "Invalid or expired reset link",
        );
      }
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        Invalid reset link.
      </div>
    );
  }

  const features = [
    { icon: Lock, text: "Strong password enforcement" },
    { icon: KeyRound, text: "Encrypted credentials" },
    { icon: ShieldCheck, text: "Secure token validation" },
    { icon: CheckCircle, text: "Instant password update" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="flex flex-1 flex-col lg:flex-row">
        {/* LEFT HERO */}
        <div className="relative hidden lg:flex lg:w-[55%] flex-col justify-between overflow-hidden">
          <img
            src={heroImage}
            alt="AI proctoring computer lab"
            className="absolute inset-0 h-full w-full object-cover"
          />

          <div className="absolute inset-0 bg-gradient-to-br from-primary/90 via-primary/70 to-primary/95" />

          <div className="relative z-10 flex flex-1 flex-col justify-between p-10">
            {/* LOGO */}
            <div className="flex items-center gap-3">
              <div className="bg-white p-2 rounded-lg shadow-md">
                <img
                  src={logoImage}
                  alt="FPT University Logo"
                  className="h-11 w-auto"
                />
              </div>
            </div>

            {/* TEXT */}
            <div className="max-w-lg space-y-6">
              <h1 className="text-4xl font-extrabold leading-tight text-white xl:text-5xl">
                Reset Your
                <br />
                <span className="text-white/90">Password</span>
              </h1>

              <p className="text-base leading-relaxed text-white/80 xl:text-lg">
                Choose a strong new password to secure your proctor account and
                protect examination integrity.
              </p>

              <div className="grid grid-cols-2 gap-3 pt-2">
                {features.map((f) => (
                  <div
                    key={f.text}
                    className="flex items-center gap-2.5 rounded-lg bg-white/10 px-4 py-3 backdrop-blur-sm"
                  >
                    <f.icon className="h-4 w-4 text-white/90" />
                    <span className="text-sm text-white/90">{f.text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* STATS */}
            <div className="flex items-center gap-8 text-sm text-white/60">
              <div>
                <span className="block text-2xl font-bold text-white">6+</span>
                Character minimum
              </div>

              <div className="h-8 w-px bg-white/20" />

              <div>
                <span className="block text-2xl font-bold text-white">AES</span>
                Encryption
              </div>

              <div className="h-8 w-px bg-white/20" />

              <div>
                <span className="block text-2xl font-bold text-white">
                  Instant
                </span>
                Activation
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT FORM */}
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-12">
          {/* MOBILE LOGO */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="bg-white p-2 rounded-lg shadow-md">
              <img
                src={logoImage}
                alt="FPT University Logo"
                className="h-12 w-auto"
              />
            </div>
          </div>

          <div className="w-full max-w-md">
            <div className="mb-8 text-center lg:text-left">
              <h2 className="text-2xl font-bold text-foreground">
                Reset Password
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Enter a new password for your account
              </p>
            </div>

            <Card className="border-border/50 shadow-chat">
              <CardContent className="p-6">
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="password">New Password</Label>

                    <Input
                      id="password"
                      type="password"
                      placeholder="At least 6 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className={`h-11 ${
                        errors.new_password ? "border-red-500" : ""
                      }`}
                    />

                    {errors.new_password && (
                      <p className="text-sm text-destructive">
                        {errors.new_password}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">
                      Confirm New Password
                    </Label>

                    <Input
                      id="confirmPassword"
                      type="password"
                      placeholder="Re-enter password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className={`h-11 ${
                        errors.confirm_password ? "border-red-500" : ""
                      }`}
                    />

                    {errors.confirm_password && (
                      <p className="text-sm text-destructive">
                        {errors.confirm_password}
                      </p>
                    )}
                  </div>

                  <Button
                    type="submit"
                    className="h-11 w-full text-sm font-semibold"
                    disabled={loading}
                  >
                    {loading ? "Processing..." : "Reset Password"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              <Link
                to="/login"
                className="font-medium text-primary hover:underline"
              >
                Back to Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>

      <footer className="border-t border-border/50 py-4 text-center text-xs text-muted-foreground">
        © 2026 FPT University – AI Proctor Assistant
      </footer>
    </div>
  );
}
