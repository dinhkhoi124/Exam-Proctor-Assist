import { lazy, Suspense } from "react";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminProtectedRoute } from "@/components/admin/AdminProtectedRoute";
import { AdminLayout } from "@/components/admin/AdminLayout";

const Index = lazy(() => import("./pages/Index"));
const About = lazy(() => import("./pages/About"));
const NotFound = lazy(() => import("./pages/NotFound"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const VerifyEmail = lazy(() => import("./pages/VerifyEmail"));
const AdminDashboard = lazy(() => import("./pages/admin/AdminDashboard"));
const UsersManagement = lazy(() => import("./pages/admin/UsersManagement"));
const ChatbotData = lazy(() => import("./pages/admin/ChatbotData"));
const FeedbackManagement = lazy(() => import("./pages/admin/FeedbackManagement"));
const AdminSettings = lazy(() => import("./pages/admin/AdminSettings"));
const Reports = lazy(() => import("./pages/admin/Reports"));

const queryClient = new QueryClient();

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Sonner richColors position="top-right" />

        <BrowserRouter>
          <AuthProvider>
            <Suspense
              fallback={
                <div className="flex min-h-screen items-center justify-center text-muted-foreground">
                  Đang tải...
                </div>
              }
            >
              <Routes>
              {/* PUBLIC ROUTES */}

              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/verify-email" element={<VerifyEmail />} />

              {/* PROTECTED ROUTES */}

              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Index />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/about"
                element={
                  <ProtectedRoute>
                    <About />
                  </ProtectedRoute>
                }
              />

              {/* ADMIN ROUTES */}

              <Route
                path="/admin"
                element={
                  <AdminProtectedRoute allowedRoles={["admin", "manager"]}>
                    <AdminLayout />
                  </AdminProtectedRoute>
                }
              >
                <Route index element={<AdminDashboard />} />
                <Route
                  path="users"
                  element={
                    <AdminProtectedRoute allowedRoles={["admin"]}>
                      <UsersManagement />
                    </AdminProtectedRoute>
                  }
                />
                <Route path="data" element={<ChatbotData />} />
                <Route path="feedback" element={<FeedbackManagement />} />
                <Route path="reports" element={<Reports />} />
                <Route
                  path="settings"
                  element={
                    <AdminProtectedRoute allowedRoles={["admin"]}>
                      <AdminSettings />
                    </AdminProtectedRoute>
                  }
                />
              </Route>

              {/* 404 */}

              <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
