// import { useState } from "react";
// import { Link } from "react-router-dom";
// import { api } from "@/lib/api";
// import { toast } from "sonner";

// import { Card, CardContent } from "@/components/ui/card";
// import { Input } from "@/components/ui/input";
// import { Button } from "@/components/ui/button";
// import { Label } from "@/components/ui/label";

// import { GraduationCap, Mail, Lock, KeyRound, ShieldAlert } from "lucide-react";
// import heroImage from "@/assets/exam-forgot-hero.jpg";

// export default function ForgotPassword() {
//   const [email, setEmail] = useState("");
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState("");

//   const handleSubmit = async (e: React.FormEvent) => {
//     e.preventDefault();

//     if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
//       setError("Please enter a valid email address");
//       return;
//     }

//     setError("");
//     setLoading(true);

//     try {
//       const res = await api.post("/api/v1/auth/forgot-password", {
//         email,
//       });

//       toast.success(res.data.message || "Reset link sent to your email");
//     } catch (error: any) {
//       toast.error(
//         error.response?.data?.detail?.[0]?.msg ||
//           error.response?.data?.detail ||
//           "Something went wrong",
//       );
//     } finally {
//       setLoading(false);
//     }
//   };

//   const features = [
//     { icon: Mail, text: "Email verification" },
//     { icon: Lock, text: "Secure password reset" },
//     { icon: KeyRound, text: "One-time passcode" },
//     { icon: ShieldAlert, text: "Account protection" },
//   ];

//   return (
//     <div className="flex min-h-screen flex-col bg-background">
//       <div className="flex flex-1 flex-col lg:flex-row">
//         {/* LEFT HERO */}
//         <div className="relative hidden lg:flex lg:w-[55%] flex-col justify-between overflow-hidden">
//           <img
//             src={heroImage}
//             alt="AI exam monitoring dashboard"
//             className="absolute inset-0 h-full w-full object-cover"
//           />

//           <div className="absolute inset-0 bg-gradient-to-br from-primary/90 via-primary/70 to-primary/95" />

//           <div className="relative z-10 flex flex-1 flex-col justify-between p-10">
//             {/* Logo */}
//             <div className="flex items-center gap-3">
//               <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
//                 <GraduationCap className="h-6 w-6 text-white" />
//               </div>
//               <div>
//                 <span className="text-lg font-bold text-white">
//                   FPT University
//                 </span>
//                 <p className="text-xs text-white/70">Education Technology</p>
//               </div>
//             </div>

//             {/* Text */}
//             <div className="max-w-lg space-y-6">
//               <h1 className="text-4xl font-extrabold leading-tight text-white xl:text-5xl">
//                 Account
//                 <br />
//                 <span className="text-white/90">Recovery</span>
//               </h1>

//               <p className="text-base leading-relaxed text-white/80 xl:text-lg">
//                 Securely reset your password and regain access to the FPT Exam
//                 Assistant.
//               </p>

//               <div className="grid grid-cols-2 gap-3 pt-2">
//                 {features.map((f) => (
//                   <div
//                     key={f.text}
//                     className="flex items-center gap-2.5 rounded-lg bg-white/10 px-4 py-3 backdrop-blur-sm"
//                   >
//                     <f.icon className="h-4 w-4 text-white/90" />
//                     <span className="text-sm text-white/90">{f.text}</span>
//                   </div>
//                 ))}
//               </div>
//             </div>

//             {/* Stats */}
//             <div className="flex items-center gap-8 text-sm text-white/60">
//               <div>
//                 <span className="block text-2xl font-bold text-white">
//                   256-bit
//                 </span>
//                 Encryption
//               </div>

//               <div className="h-8 w-px bg-white/20" />

//               <div>
//                 <span className="block text-2xl font-bold text-white">2FA</span>
//                 Verification
//               </div>

//               <div className="h-8 w-px bg-white/20" />

//               <div>
//                 <span className="block text-2xl font-bold text-white">
//                   5 min
//                 </span>
//                 OTP expiry
//               </div>
//             </div>
//           </div>
//         </div>

//         {/* RIGHT FORM */}
//         <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-12">
//           {/* Mobile Logo */}
//           <div className="mb-8 flex items-center gap-3 lg:hidden">
//             <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary shadow-md">
//               <GraduationCap className="h-6 w-6 text-primary-foreground" />
//             </div>
//             <div className="flex flex-col">
//               <span className="text-xl font-bold text-foreground">
//                 FPT Exam Support
//               </span>
//               <span className="text-xs text-muted-foreground">
//                 Proctor Assistant
//               </span>
//             </div>
//           </div>

//           <div className="w-full max-w-md">
//             <div className="mb-8 text-center lg:text-left">
//               <h2 className="text-2xl font-bold text-foreground">
//                 Forgot Password
//               </h2>
//               <p className="mt-1 text-sm text-muted-foreground">
//                 Enter your email and we will send you a password reset link
//               </p>
//             </div>

//             <Card className="border-border/50 shadow-chat">
//               <CardContent className="p-6">
//                 <form onSubmit={handleSubmit} className="space-y-5">
//                   <div className="space-y-2">
//                     <Label htmlFor="email">Email address</Label>

//                     <Input
//                       id="email"
//                       type="email"
//                       placeholder="email@fpt.edu.vn"
//                       value={email}
//                       onChange={(e) => setEmail(e.target.value)}
//                       className="h-11"
//                     />

//                     {error && (
//                       <p className="text-sm text-destructive">{error}</p>
//                     )}
//                   </div>

//                   <Button
//                     type="submit"
//                     className="h-11 w-full text-sm font-semibold"
//                     disabled={loading}
//                   >
//                     {loading ? "Sending..." : "Send Reset Link"}
//                   </Button>
//                 </form>
//               </CardContent>
//             </Card>

//             <p className="mt-6 text-center text-sm text-muted-foreground">
//               <Link
//                 to="/login"
//                 className="font-medium text-primary hover:underline"
//               >
//                 Back to Sign In
//               </Link>
//             </p>
//           </div>
//         </div>
//       </div>

//       <footer className="border-t border-border/50 py-4 text-center text-xs text-muted-foreground">
//         © 2026 FPT University – AI Proctor Assistant
//       </footer>
//     </div>
//   );
// }

import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

import { Mail, Lock, KeyRound, ShieldAlert } from "lucide-react";
import heroImage from "@/assets/exam-forgot-hero.jpg";
import logoImage from "@/assets/Logo-Dai-hoc-FPT.jpg"; // Import logo mới

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Please enter a valid email address");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await api.post("/api/v1/auth/forgot-password", {
        email,
      });

      toast.success(res.data.message || "Reset link sent to your email");
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail?.[0]?.msg ||
          error.response?.data?.detail ||
          "Something went wrong",
      );
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: Mail, text: "Email verification" },
    { icon: Lock, text: "Secure password reset" },
    { icon: KeyRound, text: "One-time passcode" },
    { icon: ShieldAlert, text: "Account protection" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="flex flex-1 flex-col lg:flex-row">
        {/* LEFT HERO */}
        <div className="relative hidden lg:flex lg:w-[55%] flex-col justify-between overflow-hidden">
          <img
            src={heroImage}
            alt="AI exam monitoring dashboard"
            className="absolute inset-0 h-full w-full object-cover"
          />

          <div className="absolute inset-0 bg-gradient-to-br from-primary/90 via-primary/70 to-primary/95" />

          <div className="relative z-10 flex flex-1 flex-col justify-between p-10">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="bg-white p-2 rounded-lg shadow-md">
                <img
                  src={logoImage} // Sử dụng logo mới
                  alt="FPT University Logo"
                  className="h-11 w-auto"
                />
              </div>
            </div>

            {/* Text */}
            <div className="max-w-lg space-y-6">
              <h1 className="text-4xl font-extrabold leading-tight text-white xl:text-5xl">
                Account
                <br />
                <span className="text-white/90">Recovery</span>
              </h1>

              <p className="text-base leading-relaxed text-white/80 xl:text-lg">
                Securely reset your password and regain access to the FPT Exam
                Assistant.
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

            {/* Stats */}
            <div className="flex items-center gap-8 text-sm text-white/60">
              <div>
                <span className="block text-2xl font-bold text-white">
                  256-bit
                </span>
                Encryption
              </div>

              <div className="h-8 w-px bg-white/20" />

              <div>
                <span className="block text-2xl font-bold text-white">2FA</span>
                Verification
              </div>

              <div className="h-8 w-px bg-white/20" />

              <div>
                <span className="block text-2xl font-bold text-white">
                  5 min
                </span>
                OTP expiry
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT FORM */}
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-12">
          {/* Mobile Logo */}
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
            <div className="mb-8 text-center lg:text-left">
              <h2 className="text-2xl font-bold text-foreground">
                Forgot Password
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Enter your email and we will send you a password reset link
              </p>
            </div>

            <Card className="border-border/50 shadow-chat">
              <CardContent className="p-6">
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email address</Label>

                    <Input
                      id="email"
                      type="email"
                      placeholder="email@fpt.edu.vn"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="h-11"
                    />

                    {error && (
                      <p className="text-sm text-destructive">{error}</p>
                    )}
                  </div>

                  <Button
                    type="submit"
                    className="h-11 w-full text-sm font-semibold"
                    disabled={loading}
                  >
                    {loading ? "Sending..." : "Send Reset Link"}
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
