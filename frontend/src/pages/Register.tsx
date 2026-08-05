import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { getApiErrorDetail, isRecord } from "@/lib/api-errors";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

import { UserPlus, ShieldCheck, Users, BookOpen } from "lucide-react";

import heroImage from "@/assets/exam-register-hero.jpg";
import logoImage from "@/assets/Logo-Dai-hoc-FPT.webp";

export default function Register() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    try {
      setLoading(true);

      await api.post("/api/v1/auth/register", {
        username,
        email,
        password,
        confirm_password: confirmPassword,
      });

      toast.success(
        "Register successful! Please check email to verify account.",
      );

      navigate("/login");
    } catch (error) {
      const details = getApiErrorDetail(error);

      if (Array.isArray(details)) {
        const messages = details.filter(isRecord).map((err) => {
          const location = Array.isArray(err.loc) ? err.loc : [];
          const field = location[1] ?? "request";
          const message = typeof err.msg === "string" ? err.msg : "Invalid value";
          return `${field}: ${message}`;
        });

        toast.error(messages.join(" | "));
      } else {
        toast.error(typeof details === "string" ? details : "Register failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: UserPlus, text: "Quick proctor registration" },
    { icon: ShieldCheck, text: "Secure credential management" },
    { icon: Users, text: "Multi-role access control" },
    { icon: BookOpen, text: "Context-aware Q&A system" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="flex flex-1 flex-col lg:flex-row">
        {/* Left Hero Section */}
        <div className="relative hidden lg:flex lg:w-[55%] flex-col justify-between overflow-hidden">
          <img
            src={heroImage}
            alt="University classroom with AI monitoring"
            className="absolute inset-0 h-full w-full object-cover"
          />

          <div className="absolute inset-0 bg-gradient-to-br from-primary/90 via-primary/70 to-primary/95" />

          <div className="relative z-10 flex flex-1 flex-col justify-between p-10">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="bg-white p-2 rounded-lg shadow-md">
                <img
                  src={logoImage}
                  alt="FPT University Logo"
                  className="h-11 w-auto"
                />
              </div>
            </div>

            {/* Hero Text */}
            <div className="max-w-lg space-y-6">
              <h1 className="text-4xl font-extrabold leading-tight text-white xl:text-5xl">
                Join the
                <br />
                <span className="text-white/90">FPT Exam Assistant</span>
              </h1>

              <p className="text-base leading-relaxed text-white/80 xl:text-lg">
                Sign up to access the AI-powered exam assistant that helps
                proctors quickly search regulations and handle exam-related
                questions.
              </p>

              <div className="grid grid-cols-2 gap-3 pt-2">
                {features.map((f) => (
                  <div
                    key={f.text}
                    className="flex items-center gap-2.5 rounded-lg bg-white/10 px-4 py-3 backdrop-blur-sm"
                  >
                    <f.icon className="h-4 w-4 shrink-0 text-white/90" />
                    <span className="text-sm text-white/90">{f.text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-8 text-sm text-white/60">
              <div>
                <span className="block text-2xl font-bold text-white">
                  200+
                </span>
                Exam queries solved
              </div>

              <div className="h-8 w-px bg-white/20" />

              <div>
                <span className="block text-2xl font-bold text-white">95%</span>
                Response accuracy
              </div>

              <div className="h-8 w-px bg-white/20" />

              <div>
                <span className="block text-2xl font-bold text-white">
                  24/7
                </span>
                AI assistant
              </div>
            </div>
          </div>
        </div>

        {/* Right Form Section */}
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-12">
          {/* Mobile Logo */}
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
            {/* Title */}
            <div className="mb-8 text-center lg:text-left">
              <h2 className="text-2xl font-bold text-foreground">
                Create Account
              </h2>

              <p className="mt-1 text-sm text-muted-foreground">
                Register a new account
              </p>
            </div>

            <Card className="border-border/50 shadow-chat">
              <CardContent className="p-6">
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Username</Label>
                    <Input
                      placeholder="Enter your username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="h-11"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input
                      type="email"
                      placeholder="Enter your email (@fpt.edu.vn or @fe.edu.vn)"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="h-11"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Password</Label>
                    <Input
                      type="password"
                      placeholder="At least 6 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="h-11"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Confirm Password</Label>
                    <Input
                      type="password"
                      placeholder="Re-enter password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="h-11"
                    />
                  </div>

                  <Button
                    type="submit"
                    className="h-11 w-full text-sm font-semibold"
                    disabled={loading}
                  >
                    {loading ? "Creating..." : "Create Account"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                to="/login"
                className="font-medium text-primary hover:underline"
              >
                Sign In
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
