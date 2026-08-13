import { useEffect, useRef, useState } from "react";
import { BarChart3, Download, FileSpreadsheet, FileText, Loader2, Users } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type GroupBy = "day" | "week" | "month" | "year";
type ExportFormat = "xlsx" | "pdf";
type QuestionScope = "user" | "all" | "admin" | "manager";

const QUESTION_SCOPE_STORAGE_KEY = "admin-dashboard-question-scope";
const questionScopeLabels: Record<QuestionScope, string> = {
  user: "Người dùng",
  all: "Tất cả tài khoản",
  admin: "Admin",
  manager: "Management",
};

interface ReportPreview {
  filters: {
    start_date: string;
    end_date: string;
    group_by: GroupBy;
    question_scope: QuestionScope;
  };
  summary: {
    total_questions: number;
    active_users: number;
    avg_latency_ms: number;
    likes: number;
    dislikes: number;
    satisfaction_rate: number;
  };
  timeline: Array<{
    period: string;
    label: string;
    questions: number;
    users: number;
    avg_latency_ms: number;
  }>;
  topics: Array<{ topic: string; questions: number }>;
}

function toInputDate(date: Date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function getDefaultDates() {
  const today = new Date();
  return {
    start: toInputDate(new Date(today.getFullYear(), today.getMonth(), 1)),
    end: toInputDate(today),
  };
}

export default function Reports() {
  const defaults = getDefaultDates();
  const [startDate, setStartDate] = useState(defaults.start);
  const [endDate, setEndDate] = useState(defaults.end);
  const [groupBy, setGroupBy] = useState<GroupBy>("day");
  const [questionScope, setQuestionScope] = useState<QuestionScope>(() => {
    const storedScope = window.localStorage.getItem(QUESTION_SCOPE_STORAGE_KEY);
    return storedScope && storedScope in questionScopeLabels
      ? (storedScope as QuestionScope)
      : "user";
  });
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [exporting, setExporting] = useState<ExportFormat | null>(null);

  const params = (scope: QuestionScope = questionScope) =>
    new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
      group_by: groupBy,
      question_scope: scope,
    });

  const loadPreview = async (scope: QuestionScope = questionScope) => {
    if (!startDate || !endDate || startDate > endDate) {
      toast.error("Khoảng thời gian không hợp lệ.");
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.get<ReportPreview>(`/api/v1/admin/reports/preview?${params(scope)}`);
      setPreview(response.data);
    } catch (error) {
      console.error("Failed to load report preview", error);
      toast.error("Không thể tải dữ liệu báo cáo.");
    } finally {
      setIsLoading(false);
    }
  };

  const initialLoadPreviewRef = useRef(loadPreview);
  initialLoadPreviewRef.current = loadPreview;

  const exportReport = async (format: ExportFormat) => {
    setExporting(format);
    try {
      const response = await api.get(`/api/v1/admin/reports/export?${params()}&format=${format}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `chatbot-report-${questionScope}-${startDate}-${endDate}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.success(`Đã xuất báo cáo ${format.toUpperCase()}.`);
    } catch (error) {
      console.error("Failed to export report", error);
      toast.error("Không thể xuất báo cáo.");
    } finally {
      setExporting(null);
    }
  };

  useEffect(() => {
    void initialLoadPreviewRef.current();
  }, []);

  return (
    <div className="space-y-4 pb-8 sm:space-y-6 sm:pb-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Báo cáo</h1>
        <p className="mt-1 text-slate-500">Xem trước và xuất báo cáo hoạt động chatbot.</p>
      </div>

      <div className="rounded-xl border bg-white p-4 shadow-sm sm:p-5">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <label className="space-y-1.5 text-sm font-medium text-slate-700">
            Từ ngày
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className="h-10 min-w-0 w-full rounded-md border px-3 font-normal"
            />
          </label>
          <label className="space-y-1.5 text-sm font-medium text-slate-700">
            Đến ngày
            <input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className="h-10 min-w-0 w-full rounded-md border px-3 font-normal"
            />
          </label>
          <label className="space-y-1.5 text-sm font-medium text-slate-700">
            Nhóm dữ liệu theo
            <select
              value={groupBy}
              onChange={(event) => setGroupBy(event.target.value as GroupBy)}
              className="h-10 w-full rounded-md border bg-white px-3 font-normal"
            >
              <option value="day">Ngày</option>
              <option value="week">Tuần</option>
              <option value="month">Tháng</option>
              <option value="year">Năm</option>
            </select>
          </label>
          <label className="space-y-1.5 text-sm font-medium text-slate-700">
            Phạm vi câu hỏi
            <select
              value={questionScope}
              onChange={(event) => {
                const scope = event.target.value as QuestionScope;
                setQuestionScope(scope);
                window.localStorage.setItem(QUESTION_SCOPE_STORAGE_KEY, scope);
                void loadPreview(scope);
              }}
              className="h-10 w-full rounded-md border bg-white px-3 font-normal"
            >
              <option value="user">Người dùng</option>
              <option value="all">Tất cả tài khoản</option>
              <option value="admin">Admin</option>
              <option value="manager">Management</option>
            </select>
          </label>
          <div className="flex items-end">
            <Button onClick={() => void loadPreview()} disabled={isLoading} className="w-full bg-orange-600 hover:bg-orange-700">
              {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BarChart3 className="mr-2 h-4 w-4" />}
              Xem báo cáo
            </Button>
          </div>
        </div>

        <div className="mt-5 grid gap-3 border-t pt-5 sm:flex sm:flex-wrap sm:items-center">
          <Button className="w-full sm:w-auto" variant="outline" onClick={() => exportReport("xlsx")} disabled={exporting !== null}>
            {exporting === "xlsx" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileSpreadsheet className="mr-2 h-4 w-4 text-emerald-600" />}
            Xuất Excel
          </Button>
          <Button className="w-full sm:w-auto" variant="outline" onClick={() => exportReport("pdf")} disabled={exporting !== null}>
            {exporting === "pdf" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4 text-red-600" />}
            Xuất PDF có biểu đồ
          </Button>
          <span className="flex items-start text-xs leading-5 text-slate-500 sm:items-center">
            <Download className="mr-1.5 mt-0.5 h-3.5 w-3.5 shrink-0 sm:mt-0" />
            Excel gồm dữ liệu chi tiết; PDF tập trung vào tổng quan và biểu đồ.
          </span>
        </div>
      </div>

      {isLoading && !preview ? (
        <div className="flex h-64 items-center justify-center rounded-xl border bg-white">
          <Loader2 className="h-7 w-7 animate-spin text-orange-600" />
        </div>
      ) : preview ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryCard
              label={`Câu hỏi · ${questionScopeLabels[preview.filters.question_scope]}`}
              value={preview.summary.total_questions.toLocaleString()}
              icon={<BarChart3 />}
            />
            <SummaryCard label="Người dùng hoạt động" value={preview.summary.active_users.toLocaleString()} icon={<Users />} />
            <SummaryCard label="Phản hồi trung bình" value={`${preview.summary.avg_latency_ms.toLocaleString()} ms`} icon={<Download />} />
            <SummaryCard label="Tỷ lệ hài lòng" value={`${preview.summary.satisfaction_rate}%`} icon={<FileText />} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard title="Hoạt động theo thời gian">
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={300}>
                <LineChart data={preview.timeline}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="questions" name="Câu hỏi" stroke="#f97316" strokeWidth={2} />
                  <Line type="monotone" dataKey="users" name="Người dùng" stroke="#3b82f6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Câu hỏi theo chủ đề">
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={300}>
                <BarChart data={preview.topics.slice(0, 10)} layout="vertical" margin={{ left: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis type="category" dataKey="topic" width={110} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="questions" name="Câu hỏi" fill="#f97316" radius={[0, 5, 5, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      ) : null}
    </div>
  );
}

function SummaryCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="min-w-0 rounded-xl border bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-center justify-between text-sm font-medium text-slate-500">
        {label}
        <span className="text-orange-500 [&>svg]:h-5 [&>svg]:w-5">{icon}</span>
      </div>
      <div className="mt-2 break-words text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 overflow-hidden rounded-xl border bg-white p-3 shadow-sm sm:p-5">
      <h2 className="mb-4 font-semibold text-slate-800">{title}</h2>
      <div className="h-[300px] min-h-[300px] w-full sm:h-[330px] sm:min-h-[330px]">{children}</div>
    </div>
  );
}
