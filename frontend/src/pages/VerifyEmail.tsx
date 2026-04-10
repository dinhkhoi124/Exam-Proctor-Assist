import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import heroImage from "@/assets/exam-proctoring-hero.jpg";
import logoImage from "@/assets/Logo-Dai-hoc-FPT.jpg"; // Import logo mới

type VerifyResponse = {
  message: string;
  username: string;
  email: string;
};

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<VerifyResponse | null>(null);
  const [error, setError] = useState("");

  const token = searchParams.get("token");

  useEffect(() => {
    if (!token) {
      setError("Invalid verification link");
      setLoading(false);
      return;
    }

    api
      .get(`/api/v1/auth/verify-email?token=${token}`)
      .then((res) => {
        setData(res.data);
        toast.success("Email verified successfully!");
      })
      .catch((err) => {
        const msg =
          err.response?.data?.detail || "Verification failed or token expired";

        setError(msg);
        toast.error(msg);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

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
                  src={logoImage} // Sử dụng logo mới
                  alt="FPT University Logo"
                  className="h-11 w-auto"
                />
              </div>
            </div>

            {/* HERO TEXT */}
            <div className="max-w-lg space-y-6">
              <h1 className="text-4xl font-extrabold leading-tight text-white xl:text-5xl">
                Verify Your
                <br />
                <span className="text-white/90">Email Address</span>
              </h1>

              <p className="text-base leading-relaxed text-white/80 xl:text-lg">
                We are verifying your email address to ensure your account's
                security and access to the FPT Exam Assistant.
              </p>
            </div>
          </div>
        </div>

        {/* RIGHT VERIFY EMAIL */}
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-12">
          {/* MOBILE LOGO */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="bg-white p-2 rounded-lg shadow-md">
              <img
                src={logoImage} // Sử dụng logo mới
                alt="FPT University Logo"
                className="h-12 w-auto"
              />
            </div>
          </div>

          <div className="w-full max-w-md">
            <Card className="border-border/50 shadow-chat">
              <CardContent className="space-y-6 pt-6 text-center">
                {loading && (
                  <>
                    <h2 className="text-xl font-semibold">
                      Verifying email...
                    </h2>
                    <p className="text-muted-foreground">
                      Please wait while we verify your account.
                    </p>
                  </>
                )}

                {!loading && error && (
                  <>
                    <h2 className="text-xl font-semibold text-destructive">
                      Verification Failed
                    </h2>

                    <p className="text-muted-foreground">{error}</p>

                    <Button
                      className="h-11 w-full text-sm font-semibold"
                      onClick={() => navigate("/login")}
                    >
                      Go to Login
                    </Button>
                  </>
                )}

                {!loading && data && (
                  <>
                    <h2 className="text-xl font-semibold text-green-600">
                      Email Verified
                    </h2>

                    <div className="text-sm text-muted-foreground space-y-1">
                      <p>
                        <strong>Username:</strong> {data.username}
                      </p>

                      <p>
                        <strong>Email:</strong> {data.email}
                      </p>
                    </div>

                    <Button
                      className="h-11 w-full text-sm font-semibold"
                      onClick={() => navigate("/login")}
                    >
                      Go to Login
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      <footer className="border-t border-border/50 py-4 text-center text-xs text-muted-foreground">
        © 2026 FPT University – AI Proctor Assistant
      </footer>
    </div>
  );
}
