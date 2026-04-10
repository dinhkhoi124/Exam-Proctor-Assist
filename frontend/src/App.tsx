// import { Toaster as Sonner } from "@/components/ui/sonner";
// import { TooltipProvider } from "@/components/ui/tooltip";
// import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
// import { BrowserRouter, Routes, Route } from "react-router-dom";

// import { AuthProvider } from "@/context/AuthContext";
// import { ProtectedRoute } from "@/components/ProtectedRoute";

// import Index from "./pages/Index";
// import About from "./pages/About";
// import NotFound from "./pages/NotFound";

// import Login from "./pages/Login";
// import Register from "./pages/Register";
// import ForgotPassword from "./pages/ForgotPassword";
// import ResetPassword from "./pages/ResetPassword";
// import VerifyEmail from "./pages/VerifyEmail";

// const queryClient = new QueryClient();

// const App = () => {
//   return (
//     <QueryClientProvider client={queryClient}>
//       <AuthProvider>
//         <TooltipProvider>
//           {/* Toast toàn hệ thống */}
//           <Sonner richColors position="top-right" />

//           <BrowserRouter>
//             <Routes>
//               {/* PUBLIC ROUTES */}

//               <Route path="/login" element={<Login />} />
//               <Route path="/register" element={<Register />} />
//               <Route path="/forgot-password" element={<ForgotPassword />} />
//               <Route path="/reset-password" element={<ResetPassword />} />
//               <Route path="/verify-email" element={<VerifyEmail />} />

//               {/* PROTECTED ROUTES */}

//               <Route
//                 path="/"
//                 element={
//                   <ProtectedRoute>
//                     <Index />
//                   </ProtectedRoute>
//                 }
//               />

//               <Route
//                 path="/about"
//                 element={
//                   <ProtectedRoute>
//                     <About />
//                   </ProtectedRoute>
//                 }
//               />

//               {/* 404 */}

//               <Route path="*" element={<NotFound />} />
//             </Routes>
//           </BrowserRouter>
//         </TooltipProvider>
//       </AuthProvider>
//     </QueryClientProvider>
//   );

// };

// export default App;

import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminProtectedRoute } from "@/components/admin/AdminProtectedRoute";

import Index from "./pages/Index";
import About from "./pages/About";
import NotFound from "./pages/NotFound";

import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import VerifyEmail from "./pages/VerifyEmail";

import AdminDashboard from "./pages/admin/AdminDashboard";
import UsersManagement from "./pages/admin/UsersManagement";
import ChatbotData from "./pages/admin/ChatbotData";
import FeedbackManagement from "./pages/admin/FeedbackManagement";

const queryClient = new QueryClient();

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Sonner richColors position="top-right" />

        <BrowserRouter>
          <AuthProvider>
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
                  <AdminProtectedRoute>
                    <AdminDashboard />
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <AdminProtectedRoute>
                    <UsersManagement />
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/data"
                element={
                  <AdminProtectedRoute>
                    <ChatbotData />
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/feedback"
                element={
                  <AdminProtectedRoute>
                    <FeedbackManagement />
                  </AdminProtectedRoute>
                }
              />

              {/* 404 */}

              <Route path="*" element={<NotFound />} />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
