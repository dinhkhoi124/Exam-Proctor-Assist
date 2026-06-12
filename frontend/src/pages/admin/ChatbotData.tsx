import { FileText, Plus, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ChatbotData() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Quản lý tài liệu</h1>
            <span className="text-xxs font-bold px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-md">
              Backend Pending
            </span>
          </div>
          <p className="text-slate-500 mt-1">Tải lên và quản lý nguồn kiến thức cho chatbot.</p>
        </div>
        <Button 
          disabled 
          className="bg-orange-600/50 cursor-not-allowed text-white flex items-center gap-2 h-10 px-4 shrink-0"
        >
          <Plus className="h-4 w-4" />
          Tải lên tài liệu
        </Button>
      </div>

      {/* Empty State Table Container */}
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-500 border-b">
              <tr>
                <th className="px-6 py-4 font-semibold">Tên tài liệu</th>
                <th className="px-6 py-4 font-semibold">Loại</th>
                <th className="px-6 py-4 font-semibold">Dung lượng</th>
                <th className="px-6 py-4 font-semibold">Người tải</th>
                <th className="px-6 py-4 font-semibold">Ngày tải</th>
                <th className="px-6 py-4 font-semibold">Trạng thái</th>
                <th className="px-6 py-4 font-semibold text-right">Hành động</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colSpan={7} className="px-6 py-16 text-center">
                  <div className="flex flex-col items-center justify-center max-w-sm mx-auto space-y-3">
                    <div className="h-12 w-12 rounded-full bg-slate-50 border flex items-center justify-center text-slate-400">
                      <FileText className="h-6 w-6" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-semibold text-slate-800 text-sm">Chưa có tài liệu nào</h4>
                      <p className="text-xs text-slate-400">
                        Tính năng quản lý và đồng bộ chỉ mục tài liệu RAG đang chờ máy chủ cung cấp API tải lên và lập chỉ mục.
                      </p>
                    </div>
                    <div className="inline-flex items-center gap-1.5 text-xxs text-amber-700 bg-amber-50 px-2.5 py-1 rounded border border-amber-100 font-medium">
                      <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
                      <span>Trạng thái kết nối API: Backend Pending</span>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
