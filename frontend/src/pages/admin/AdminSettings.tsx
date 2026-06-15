import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Eye, EyeOff, Save, Send, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function AdminSettings() {
  const [smtpServer, setSmtpServer] = useState("");
  const [smtpPort, setSmtpPort] = useState(587);
  const [senderEmail, setSenderEmail] = useState("");
  const [senderName, setSenderName] = useState("");
  const [appPassword, setAppPassword] = useState("");
  const [useTls, setUseTls] = useState(true);
  
  const [hasPassword, setHasPassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  
  // Test email modal/prompt state
  const [showTestModal, setShowTestModal] = useState(false);
  const [testRecipient, setTestRecipient] = useState("");

  const fetchSettings = async () => {
    try {
      setIsLoading(true);
      const res = await api.get("/api/v1/email-settings");
      setSmtpServer(res.data.smtp_server || "");
      setSmtpPort(res.data.smtp_port || 587);
      setSenderEmail(res.data.sender_email || "");
      setSenderName(res.data.sender_name || "");
      setUseTls(res.data.use_tls ?? true);
      setHasPassword(res.data.has_password || false);
      if (res.data.has_password) {
        setAppPassword("••••••••••••••••");
      }
    } catch (err) {
      console.error("Failed to load email settings", err);
      toast.error("Không thể tải cấu hình SMTP");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!smtpServer || !smtpPort || !senderEmail || !senderName || !appPassword) {
      toast.error("Vui lòng điền đầy đủ các trường thông tin bắt buộc");
      return;
    }

    try {
      setIsSaving(true);
      // If password field is still the masked placeholder, do not send placeholder text
      const passwordToSend = appPassword === "••••••••••••••••" ? "" : appPassword;
      
      await api.post("/api/v1/email-settings", {
        smtp_server: smtpServer,
        smtp_port: Number(smtpPort),
        sender_email: senderEmail,
        sender_name: senderName,
        app_password: passwordToSend,
        use_tls: useTls
      });
      
      toast.success("Đã lưu cấu hình email hệ thống");
      fetchSettings();
    } catch (err) {
      console.error("Failed to save email settings", err);
      toast.error("Không thể lưu cấu hình email");
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testRecipient) {
      toast.error("Vui lòng nhập địa chỉ email nhận test");
      return;
    }

    try {
      setIsTesting(true);
      await api.post("/api/v1/email-settings/test", {
        email: testRecipient
      });
      toast.success(`Đã gửi email test thành công tới ${testRecipient}`);
      setShowTestModal(false);
      setTestRecipient("");
    } catch (err: any) {
      console.error("Failed to send test email", err);
      toast.error(err.response?.data?.detail || "Gửi email kiểm tra thất bại. Vui lòng kiểm tra lại cấu hình.");
    } finally {
      setIsTesting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground animate-pulse font-medium">Đang tải cài đặt hệ thống...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Cài đặt hệ thống</h1>
        <p className="text-slate-500 mt-1">Cập nhật email gửi và App Password dùng để gửi mã xác thực OTP.</p>
      </div>

      <div className="max-w-2xl bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="p-4 border-b bg-slate-50/50 sm:p-6">
          <h3 className="font-semibold text-lg text-slate-800">Cấu hình email gửi</h3>
          <p className="text-xs text-slate-500 mt-0.5">Vui lòng cung cấp cấu hình máy chủ SMTP chính xác.</p>
        </div>

        <form onSubmit={handleSave} className="p-4 space-y-4 sm:p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700 block">SMTP Server *</label>
              <input
                type="text"
                placeholder="smtp.gmail.com"
                value={smtpServer}
                onChange={(e) => setSmtpServer(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500 bg-white"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700 block">SMTP Port *</label>
              <input
                type="number"
                placeholder="587"
                value={smtpPort}
                onChange={(e) => setSmtpPort(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500 bg-white"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700 block">Email gửi hệ thống *</label>
              <input
                type="email"
                placeholder="noreply@fpt.edu.vn"
                value={senderEmail}
                onChange={(e) => setSenderEmail(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500 bg-white"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700 block">Tên người gửi hệ thống *</label>
              <input
                type="text"
                placeholder="FPT Proctor Support"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500 bg-white"
                required
              />
            </div>
          </div>

          <div className="space-y-1.5 relative">
            <label className="text-sm font-semibold text-slate-700 block">App Password *</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Nhập App Password của tài khoản gửi email"
                value={appPassword}
                onChange={(e) => setAppPassword(e.target.value)}
                onFocus={() => {
                  if (appPassword === "••••••••••••••••") setAppPassword("");
                }}
                onBlur={() => {
                  if (!appPassword && hasPassword) setAppPassword("••••••••••••••••");
                }}
                className="w-full pl-3 pr-10 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500 bg-white"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 focus:outline-none"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <p className="text-xxs text-slate-400 mt-1">
              App Password được sinh từ Google/Outlook để gửi mail thông qua giao thức SMTP. Được bảo mật và mã hóa trong Database.
            </p>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="useTls"
              checked={useTls}
              onChange={(e) => setUseTls(e.target.checked)}
              className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-slate-300 rounded"
            />
            <label htmlFor="useTls" className="text-sm font-medium text-slate-700">
              Sử dụng bảo mật TLS (StartTLS)
            </label>
          </div>

          <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <Button
              type="button"
              variant="outline"
              disabled={!hasPassword}
              onClick={() => setShowTestModal(true)}
              className="flex w-full items-center gap-2 hover:bg-slate-50 text-slate-700 border-slate-300 sm:w-auto"
            >
              <Send className="h-4 w-4" />
              Kiểm tra kết nối
            </Button>

            <Button
              type="submit"
              disabled={isSaving}
              className="flex w-full items-center gap-2 bg-orange-600 px-6 text-white hover:bg-orange-700 sm:w-auto"
            >
              <Save className="h-4 w-4" />
              {isSaving ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
          </div>
        </form>
      </div>

      {/* TEST CONNECTION DIALOG MODAL */}
      {showTestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm">
          <div className="max-h-[90dvh] w-full max-w-md overflow-y-auto bg-white rounded-xl border shadow-xl p-5 sm:p-6 space-y-4 animate-in zoom-in-95 duration-200">
            <div>
              <h3 className="font-semibold text-lg text-slate-800 flex items-center gap-2">
                <Send className="text-orange-500 h-5 w-5" />
                Kiểm tra cấu hình SMTP
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Hệ thống sẽ thử nghiệm gửi một email xác thực qua tài khoản đã lưu.
              </p>
            </div>

            <form onSubmit={handleTestEmail} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700 block">Địa chỉ email nhận test *</label>
                <input
                  type="email"
                  placeholder="name@fpt.edu.vn"
                  value={testRecipient}
                  onChange={(e) => setTestRecipient(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 bg-white"
                  required
                />
              </div>

              <div className="flex items-center gap-2 text-xxs text-amber-700 bg-amber-50 p-2.5 rounded-lg border border-amber-100 font-medium">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                <span>Hãy chắc chắn rằng bạn đã bấm "Lưu thay đổi" trước khi thực hiện gửi email thử nghiệm.</span>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setShowTestModal(false);
                    setTestRecipient("");
                  }}
                  className="text-slate-600 hover:bg-slate-100"
                >
                  Hủy bỏ
                </Button>
                <Button
                  type="submit"
                  disabled={isTesting}
                  className="bg-orange-600 hover:bg-orange-700 text-white flex items-center gap-2"
                >
                  {isTesting ? "Đang gửi..." : "Gửi email test"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
