import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowUpDown, CheckCircle2, FileText, Loader2, Plus, Search, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { getApiErrorMessage as getSharedApiErrorMessage } from "@/lib/api-errors";

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

const MAX_BATCH_FILES = 20;
const MAX_PDF_SIZE = 25 * 1024 * 1024;
const MAX_BATCH_TOTAL_SIZE = 90 * 1024 * 1024;
const MAX_BATCH_DELETE_FILES = 100;

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

function getErrorMessage(error: unknown) {
  return getSharedApiErrorMessage(
    error,
    "Không thể cập nhật tài liệu. Vui lòng thử lại.",
  );
}

function normalizeSearchText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLocaleLowerCase("vi");
}

export default function ChatbotData() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [deletingName, setDeletingName] = useState<string | null>(null);
  const [selectedNames, setSelectedNames] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
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
      const availableNames = new Set(response.data.map((document) => document.name));
      setSelectedNames((previous) => new Set(
        [...previous].filter((name) => availableNames.has(name)),
      ));
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
    const normalizedQuery = normalizeSearchText(searchQuery.trim());
    const filteredDocuments = normalizedQuery
      ? documents.filter((document) =>
          normalizeSearchText(document.name).includes(normalizedQuery),
        )
      : documents;

    return [...filteredDocuments].sort((a, b) => {
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
  }, [documents, searchQuery, sortOption]);

  const visibleNames = sortedDocuments.map((document) => document.name);
  const allVisibleSelected = visibleNames.length > 0
    && visibleNames.every((name) => selectedNames.has(name));
  const someVisibleSelected = visibleNames.some((name) => selectedNames.has(name));

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (files.length === 0) return;

    if (files.length > MAX_BATCH_FILES) {
      toast.error(`Mỗi lần chỉ được chọn tối đa ${MAX_BATCH_FILES} tài liệu.`);
      return;
    }

    if (files.some((file) => !file.name.toLowerCase().endsWith(".pdf"))) {
      toast.error("Chỉ hỗ trợ tài liệu PDF.");
      return;
    }

    const oversizedFile = files.find((file) => file.size > MAX_PDF_SIZE);
    if (oversizedFile) {
      toast.error(`“${oversizedFile.name}” vượt quá giới hạn 25 MB.`);
      return;
    }

    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    if (totalSize > MAX_BATCH_TOTAL_SIZE) {
      toast.error("Tổng dung lượng tài liệu không được vượt quá 90 MB.");
      return;
    }

    const foldedNames = files.map((file) => file.name.toLocaleLowerCase("vi"));
    if (new Set(foldedNames).size !== foldedNames.length) {
      toast.error("Danh sách đã chọn có tên file bị trùng.");
      return;
    }

    const existingNames = new Map(
      documents.map((document) => [
        document.name.toLocaleLowerCase("vi"),
        document.name,
      ]),
    );
    const caseVariantCollision = files
      .map((file) => ({
        requested: file.name,
        existing: existingNames.get(file.name.toLocaleLowerCase("vi")),
      }))
      .find(({ requested, existing }) => existing && existing !== requested);
    if (caseVariantCollision) {
      toast.error(
        `Tên “${caseVariantCollision.requested}” chỉ khác hoa/thường với “${caseVariantCollision.existing}”. `
        + "Hãy dùng đúng tên hiện có khi thay thế tài liệu.",
      );
      return;
    }

    const replacementNames = files
      .map((file) => file.name)
      .filter((name) => existingNames.get(name.toLocaleLowerCase("vi")) === name);
    if (
      replacementNames.length > 0
      && !window.confirm(
        `${replacementNames.length} tài liệu đã tồn tại và sẽ được thay thế:\n\n${replacementNames.join("\n")}`,
      )
    ) {
      return;
    }

    setIsUpdating(true);
    setIndexProgress({
      active: true,
      progress: 5,
      stage: "preparing_document",
      operation: "upload",
      file_name: `${files.length} tài liệu`,
      error: null,
    });
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    try {
      await api.post("/api/v1/admin/documents/batch-upload", formData);
      toast.success(`Đã xử lý ${files.length} tài liệu và lập chỉ mục lại một lần.`);
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
      setSelectedNames((previous) => {
        const next = new Set(previous);
        next.delete(document.name);
        return next;
      });
      await fetchDocuments();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setDeletingName(null);
      setIsUpdating(false);
    }
  };

  const toggleDocument = (name: string) => {
    setSelectedNames((previous) => {
      const next = new Set(previous);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const toggleAllVisible = () => {
    setSelectedNames((previous) => {
      const next = new Set(previous);
      if (allVisibleSelected) {
        visibleNames.forEach((name) => next.delete(name));
      } else {
        visibleNames.forEach((name) => next.add(name));
      }
      return next;
    });
  };

  const handleBatchDelete = async () => {
    const fileNames = [...selectedNames];
    if (fileNames.length === 0) return;
    if (fileNames.length > MAX_BATCH_DELETE_FILES) {
      toast.error(`Mỗi lần chỉ được xóa tối đa ${MAX_BATCH_DELETE_FILES} tài liệu.`);
      return;
    }
    if (!window.confirm(`Xóa ${fileNames.length} tài liệu đã chọn và chỉ lập chỉ mục lại một lần?`)) return;

    setIsUpdating(true);
    setIndexProgress({
      active: true,
      progress: 5,
      stage: "preparing_document",
      operation: "delete",
      file_name: `${fileNames.length} tài liệu`,
      error: null,
    });
    try {
      await api.post("/api/v1/admin/documents/batch-delete", { file_names: fileNames });
      toast.success(`Đã xóa ${fileNames.length} tài liệu và lập chỉ mục lại một lần.`);
      setSelectedNames(new Set());
      await fetchDocuments();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
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

        <input ref={inputRef} type="file" accept="application/pdf,.pdf" multiple className="hidden" onChange={handleUpload} />
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
        <div className="flex flex-col gap-3 border-b bg-slate-50/60 px-4 py-3 sm:px-5 lg:flex-row lg:items-center lg:justify-between">
          <p className="shrink-0 text-sm text-slate-500">
            {searchQuery.trim()
              ? `${sortedDocuments.length}/${documents.length} tài liệu`
              : `${documents.length} tài liệu`}
          </p>
          <div className="flex w-full flex-col gap-2 sm:flex-row lg:w-auto">
            {selectedNames.size > 0 && (
              <Button
                type="button"
                variant="outline"
                disabled={isUpdating}
                onClick={handleBatchDelete}
                className="h-10 border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 sm:h-9"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Xóa {selectedNames.size} mục
              </Button>
            )}
            <div className="relative w-full sm:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                type="text"
                role="searchbox"
                spellCheck={false}
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Tìm theo tên tài liệu..."
                aria-label="Tìm kiếm tài liệu theo tên"
                className="h-10 bg-white pl-9 pr-10 sm:h-9"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  aria-label="Xóa nội dung tìm kiếm"
                  className="absolute right-1 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="flex w-full items-center gap-2 sm:w-auto">
              <ArrowUpDown className="h-4 w-4 shrink-0 text-slate-400" />
            <Select value={sortOption} onValueChange={(value) => setSortOption(value as SortOption)}>
              <SelectTrigger className="h-10 flex-1 bg-white sm:h-9 sm:w-[210px] sm:flex-none">
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
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-[860px] w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-500 border-b">
              <tr>
                <th className="w-12 px-4 py-4 text-center font-semibold">
                  <input
                    ref={(input) => {
                      if (input) input.indeterminate = someVisibleSelected && !allVisibleSelected;
                    }}
                    type="checkbox"
                    checked={allVisibleSelected}
                    disabled={isUpdating || visibleNames.length === 0}
                    onChange={toggleAllVisible}
                    aria-label="Chọn tất cả tài liệu đang hiển thị"
                    className="h-4 w-4 cursor-pointer accent-orange-600 disabled:cursor-not-allowed"
                  />
                </th>
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
                  <td colSpan={7} className="px-6 py-16 text-center text-slate-500">
                    <Loader2 className="mx-auto mb-2 h-6 w-6 animate-spin" />
                    Đang tải danh sách tài liệu...
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-16 text-center">
                    <FileText className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                    <h4 className="font-semibold text-slate-800">Chưa có tài liệu nào</h4>
                    <p className="mt-1 text-xs text-slate-400">Tải PDF lên để bổ sung nguồn kiến thức cho chatbot.</p>
                  </td>
                </tr>
              ) : sortedDocuments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-16 text-center">
                    <Search className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                    <h4 className="font-semibold text-slate-800">Không tìm thấy tài liệu</h4>
                    <p className="mt-1 text-xs text-slate-400">
                      Không có tên tài liệu nào khớp với “{searchQuery.trim()}”.
                    </p>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setSearchQuery("")}
                      className="mt-3 text-orange-600 hover:bg-orange-50 hover:text-orange-700"
                    >
                      Xóa tìm kiếm
                    </Button>
                  </td>
                </tr>
              ) : (
                sortedDocuments.map((document) => (
                  <tr key={document.name} className="hover:bg-slate-50/70">
                    <td className="px-4 py-4 text-center">
                      <input
                        type="checkbox"
                        checked={selectedNames.has(document.name)}
                        disabled={isUpdating}
                        onChange={() => toggleDocument(document.name)}
                        aria-label={`Chọn ${document.name}`}
                        className="h-4 w-4 cursor-pointer accent-orange-600 disabled:cursor-not-allowed"
                      />
                    </td>
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
