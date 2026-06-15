import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowUpDown, CheckCircle2, FileText, Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";

interface RagDocument {
  id: string;
  name: string;
  size: number;
  updated_at: number;
  chunk_count: number;
  indexed: boolean;
  status: "indexing" | "ready" | "failed" | "deleted";
  uploaded_by: string | null;
  uploader_name: string | null;
  error_message: string | null;
}

interface IndexProgress {
  active: boolean;
  progress: number;
  stage: string;
  operation: "upload" | "delete" | null;
  file_name: string | null;
  error: string | null;
}

type SortOption = "updated_desc" | "updated_asc" | "name_asc" | "name_desc" | "size_desc" | "chunks_desc";

const stageLabels: Record<string, string> = {
  idle: "Sẵn sàng",
  preparing_document: "Đang chuẩn bị tài liệu",
  reading_documents: "Đang đọc nội dung PDF",
  chunking_documents: "Đang chia nhỏ nội dung",
  creating_embeddings: "Đang tạo embeddings",
  saving_vector_index: "Đang lưu vector index",
  saving_search_index: "Đang lưu BM25 index",
  activating_index: "Đang kích hoạt index mới",
  completed: "Đã hoàn tất",
  failed: "Lập chỉ mục thất bại",
};

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function getErrorMessage(error: any) {
  return error?.response?.data?.detail || "Không thể cập nhật tài liệu. Vui lòng thử lại.";
}

export default function ChatbotData() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [deletingName, setDeletingName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortOption, setSortOption] = useState<SortOption>("updated_desc");
  const [indexProgress, setIndexProgress] = useState<IndexProgress>({
    active: false,
    progress: 0,
    stage: "idle",
    operation: null,
    file_name: null,
    error: null,
  });

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const response = await api.get<RagDocument[]>("/api/v1/admin/documents");
      setDocuments(response.data);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    if (!isUpdating) return;

    const fetchProgress = async () => {
      try {
        const response = await api.get<IndexProgress>("/api/v1/admin/documents/index-status");
        setIndexProgress(response.data);
      } catch {
        // The main upload/delete request will surface actionable errors.
      }
    };

    fetchProgress();
    const interval = window.setInterval(fetchProgress, 500);
    return () => window.clearInterval(interval);
  }, [isUpdating]);

  const sortedDocuments = useMemo(() => {
    return [...documents].sort((a, b) => {
      switch (sortOption) {
        case "updated_asc":
          return a.updated_at - b.updated_at;
        case "name_asc":
          return a.name.localeCompare(b.name, "vi");
        case "name_desc":
          return b.name.localeCompare(a.name, "vi");
        case "size_desc":
          return b.size - a.size;
        case "chunks_desc":
          return b.chunk_count - a.chunk_count;
        default:
          return b.updated_at - a.updated_at;
      }
    });
  }, [documents, sortOption]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Chỉ hỗ trợ tài liệu PDF.");
      return;
    }

    const replacing = documents.some((document) => document.name === file.name);
    if (replacing && !window.confirm(`Tài liệu "${file.name}" đã tồn tại. Bạn muốn thay thế tài liệu này?`)) {
      return;
    }

    setIsUpdating(true);
    setIndexProgress({
      active: true,
      progress: 5,
      stage: "preparing_document",
      operation: "upload",
      file_name: file.name,
      error: null,
    });
    const formData = new FormData();
    formData.append("file", file);
    try {
      await api.post("/api/v1/admin/documents", formData);
      toast.success(replacing ? "Đã thay thế và lập chỉ mục lại tài liệu." : "Đã tải lên và lập chỉ mục tài liệu.");
      await fetchDocuments();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async (document: RagDocument) => {
    if (!window.confirm(`Xóa "${document.name}" khỏi nguồn kiến thức chatbot?`)) return;

    setDeletingName(document.name);
    setIsUpdating(true);
    setIndexProgress({
      active: true,
      progress: 5,
      stage: "preparing_document",
      operation: "delete",
      file_name: document.name,
      error: null,
    });
    try {
      await api.delete(`/api/v1/admin/documents/${encodeURIComponent(document.name)}`);
      toast.success("Đã xóa tài liệu và lập chỉ mục lại.");
      await fetchDocuments();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setDeletingName(null);
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Quản lý tài liệu</h1>
            <span className="text-xxs font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-md">
              RAG Connected
            </span>
          </div>
          <p className="text-slate-500 mt-1">
            Tải lên, thay thế hoặc xóa nguồn kiến thức. Vector DB sẽ tự động được cập nhật.
          </p>
        </div>

        <input ref={inputRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={handleUpload} />
        <Button
          disabled={isUpdating}
          onClick={() => inputRef.current?.click()}
          className="bg-orange-600 hover:bg-orange-700 text-white flex items-center gap-2 h-10 px-4 shrink-0"
        >
          {isUpdating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          {isUpdating ? "Đang lập chỉ mục..." : "Tải lên tài liệu"}
        </Button>
      </div>

      {isUpdating && (
        <div className="space-y-3 rounded-lg border border-orange-200 bg-orange-50 px-4 py-4 text-sm text-orange-800">
          <div className="flex items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-2">
              <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
              <span className="truncate">
                {stageLabels[indexProgress.stage] || "Đang cập nhật vector DB"}
                {indexProgress.file_name ? `: ${indexProgress.file_name}` : ""}
              </span>
            </div>
            <span className="shrink-0 font-semibold">{indexProgress.progress}%</span>
          </div>
          <Progress value={indexProgress.progress} className="h-2 bg-orange-100 [&>div]:bg-orange-600" />
          <p className="text-xs text-orange-700">Vui lòng giữ trang này mở cho đến khi hoàn tất.</p>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="flex flex-col gap-3 border-b bg-slate-50/60 px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-500">{documents.length} tài liệu</p>
          <div className="flex items-center gap-2">
            <ArrowUpDown className="h-4 w-4 text-slate-400" />
            <Select value={sortOption} onValueChange={(value) => setSortOption(value as SortOption)}>
              <SelectTrigger className="h-9 w-[210px] bg-white">
                <SelectValue placeholder="Sắp xếp tài liệu" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="updated_desc">Mới cập nhật trước</SelectItem>
                <SelectItem value="updated_asc">Cũ cập nhật trước</SelectItem>
                <SelectItem value="name_asc">Tên A đến Z</SelectItem>
                <SelectItem value="name_desc">Tên Z đến A</SelectItem>
                <SelectItem value="size_desc">Dung lượng lớn trước</SelectItem>
                <SelectItem value="chunks_desc">Nhiều chunks trước</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-[800px] w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-500 border-b">
              <tr>
                <th className="px-6 py-4 font-semibold">Tên tài liệu</th>
                <th className="px-6 py-4 font-semibold">Dung lượng</th>
                <th className="px-6 py-4 font-semibold">Người tải</th>
                <th className="px-6 py-4 font-semibold">Cập nhật lúc</th>
                <th className="px-6 py-4 font-semibold">Trạng thái</th>
                <th className="px-6 py-4 font-semibold text-right">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center text-slate-500">
                    <Loader2 className="mx-auto mb-2 h-6 w-6 animate-spin" />
                    Đang tải danh sách tài liệu...
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center">
                    <FileText className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                    <h4 className="font-semibold text-slate-800">Chưa có tài liệu nào</h4>
                    <p className="mt-1 text-xs text-slate-400">Tải PDF lên để bổ sung nguồn kiến thức cho chatbot.</p>
                  </td>
                </tr>
              ) : (
                sortedDocuments.map((document) => (
                  <tr key={document.name} className="hover:bg-slate-50/70">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 shrink-0 text-orange-600" />
                        <span className="max-w-md truncate font-medium text-slate-800" title={document.name}>
                          {document.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-500">{formatFileSize(document.size)}</td>
                    <td className="px-6 py-4 text-slate-500">{document.uploader_name || "Hệ thống"}</td>
                    <td className="px-6 py-4 text-slate-500">
                      {new Date(document.updated_at * 1000).toLocaleString("vi-VN")}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                          document.status === "ready"
                            ? "bg-emerald-50 text-emerald-700"
                            : document.status === "failed"
                              ? "bg-red-50 text-red-700"
                              : "bg-amber-50 text-amber-700"
                        }`}
                        title={document.error_message || undefined}
                      >
                        {document.status === "indexing" ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : document.status === "ready" ? (
                          <CheckCircle2 className="h-3.5 w-3.5" />
                        ) : (
                          <AlertCircle className="h-3.5 w-3.5" />
                        )}
                        {document.status === "ready"
                          ? `${document.chunk_count} chunks`
                          : document.status === "failed"
                            ? "Lập chỉ mục thất bại"
                            : "Đang lập chỉ mục"}
                      </span>
                      {document.error_message && (
                        <p className="mt-1 max-w-xs truncate text-xs text-red-500" title={document.error_message}>
                          {document.error_message}
                        </p>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isUpdating}
                        onClick={() => handleDelete(document)}
                        className="text-red-600 hover:bg-red-50 hover:text-red-700"
                      >
                        {deletingName === document.name ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                        <span className="ml-2">Xóa</span>
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
