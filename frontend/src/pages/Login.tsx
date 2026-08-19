import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/auth";
import { api, AUTH_NOTICE_STORAGE_KEY } from "@/lib/api";
import { getApiErrorMessage, getApiErrorPayload, isRecord } from "@/lib/api-errors";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import { AlertCircle, Mail, Shield, Eye, Brain, CheckCircle } from "lucide-react";

import heroImage from "@/assets/exam-proctoring-hero.jpg";
import logoImage from "@/assets/Logo-Dai-hoc-FPT.webp";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [unverifiedAccount, setUnverifiedAccount] = useState<{
    message: string;
    canResendVerification: boolean;
  } | null>(null);

  useEffect(() => {
    const notice = sessionStorage.getItem(AUTH_NOTICE_STORAGE_KEY);
    if (!notice) return;
    sessionStorage.removeItem(AUTH_NOTICE_STORAGE_KEY);
    toast.error(notice);
  }, []);

  const handleResendVerification = async () => {
    const email = identifier.trim();

    if (!email.includes("@")) {
      toast.error("Please enter your email address to resend verification.");
      return;
    }

    try {
      setResendLoading(true);

      const response = await api.post("/api/v1/auth/resend-verification", {
        email,
      });

      toast.success(
        response.data?.message ||
          "If the account exists and is not verified, a verification email has been sent.",
      );
    } catch (error) {
      toast.error(
        getApiErrorMessage(
          error,
          "Could not resend verification email. Please try again later.",
        ),
      );
    } finally {
      setResendLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setLoading(true);
      setUnverifiedAccount(null);

      const response = await api.post("/api/v1/auth/login", {
        identifier,
        password,
      });

      console.log("LOGIN RESPONSE:", response.data);

      const token =
        response.data.access_token ||
        response.data.token ||
        response.data.accessToken;

      if (!token) {
        throw new Error("Token not found in login response");
      }

      const user = response.data.user;

      login(token, user);

      toast.success("Login successful!");

      const redirectPath = (user?.role === "admin" || user?.role === "manager") ? "/admin" : "/";

      setTimeout(() => {
        navigate(redirectPath, { replace: true });
      }, 50);

      navigate(redirectPath, { replace: true });
    } catch (error) {
      const errorData = getApiErrorPayload(error);
      const nestedDetail = isRecord(errorData?.detail)
        ? errorData.detail
        : undefined;
      const emailNotVerified =
        errorData?.error === "EMAIL_NOT_VERIFIED" ||
        nestedDetail?.error === "EMAIL_NOT_VERIFIED";

      if (emailNotVerified) {
        const payload =
          errorData?.error === "EMAIL_NOT_VERIFIED"
            ? errorData
            : nestedDetail;

        setUnverifiedAccount({
          message:
            typeof payload?.message === "string"
              ? payload.message
              : "Account is not verified",
          canResendVerification: Boolean(payload.can_resend_verification),
        });

        toast.error("Account is not verified. Please verify your email.");
        return;
      }

      toast.error(getApiErrorMessage(error, "Invalid credentials"));
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: Shield, text: "AI-powered exam assistant" },
    { icon: Eye, text: "Instant regulation lookup" },
    { icon: Brain, text: "Context-aware Q&A system" },
    { icon: CheckCircle, text: "Fast and reliable information retrieval" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="flex flex-1 flex-col lg:flex-row">
        {/* LEFT HERO */}
        <div className="relative hidden lg:flex lg:w-[55%] flex-col justify-between overflow-hidden">
          <img
            src={heroImage}
            alt="AI exam proctoring classroom"
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

            {/* HERO TEXT */}
            <div className="max-w-lg space-y-6">
              <h1 className="text-4xl font-extrabold leading-tight text-white xl:text-5xl">
                AI Exam Proctor
                <br />
                <span className="text-white/90">Assistant</span>
              </h1>

              <p className="text-base leading-relaxed text-white/80 xl:text-lg">
                AI assistant that helps proctors quickly find exam regulations
                and handle exam-related questions in real time.
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

            {/* STATS */}
            <div className="flex items-center gap-8 text-sm text-white/60">
              <div>
                <span className="block text-2xl font-bold text-white">
                  1000+
                </span>
                Questions answered
              </div>

              <div className="h-8 w-px bg-white/20" />

              <div>
                <span className="block text-2xl font-bold text-white">95%</span>
                Response relevance
              </div>

              <div className="h-8 w-px bg-white/20" />

              <div>
                <span className="block text-2xl font-bold text-white">
                  24/7
                </span>
                AI availability
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT LOGIN */}
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
            {/* HEADER */}
            <div className="mb-8 text-center lg:text-left">
              <h2 className="text-2xl font-bold text-foreground">
                Welcome back
              </h2>

              <p className="mt-1 text-sm text-muted-foreground">
                Sign in to access the exam support system
              </p>
            </div>

            <Card className="border-border/50 shadow-chat">
              <CardContent className="p-6">
                <form onSubmit={handleLogin} className="space-y-5">
                  <div className="space-y-2">
                    <Label>Email or Username</Label>

                    <Input
                      placeholder="Enter your email or username"
                      value={identifier}
                      onChange={(e) => {
                        setIdentifier(e.target.value);
                        setUnverifiedAccount(null);
                      }}
                      className="h-11"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Password</Label>

                      <Link
                        to="/forgot-password"
                        className="text-xs text-primary hover:underline"
                      >
                        Forgot password?
                      </Link>
                    </div>

                    <Input
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        setUnverifiedAccount(null);
                      }}
                      className="h-11"
                    />
                  </div>

                  {unverifiedAccount && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>Email verification required</AlertTitle>
                      <AlertDescription className="space-y-3">
                        <p>
                          {unverifiedAccount.message}. Please check your inbox
                          or spam folder before signing in.
                        </p>

                        {unverifiedAccount.canResendVerification && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-9"
                            onClick={handleResendVerification}
                            disabled={resendLoading}
                          >
                            <Mail className="mr-2 h-4 w-4" />
                            {resendLoading
                              ? "Sending..."
                              : "Resend verification email"}
                          </Button>
                        )}
                      </AlertDescription>
                    </Alert>
                  )}

                  <Button
                    type="submit"
                    className="h-11 w-full text-sm font-semibold"
                    disabled={loading}
                  >
                    {loading ? "Signing in..." : "Sign In"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              Don’t have an account?{" "}
              <Link
                to="/register"
                className="font-medium text-primary hover:underline"
              >
                Create account
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
