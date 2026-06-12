import { Wifi, LogIn, Globe, Clock, Upload, Laptop, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";

interface QuickActionsProps {
  onSelect: (query: string) => void;
}

const quickActions = [
  { icon: Wifi, label: "Sự cố WiFi phòng thi", query: "Thí sinh không kết nối được WiFi phòng thi" },
  { icon: LogIn, label: "Lỗi đăng nhập portal", query: "Thí sinh không đăng nhập được cổng thi portal" },
  { icon: Globe, label: "Lỗi trình duyệt", query: "Trang thi không tải được hoặc hiển thị sai trên trình duyệt" },
  { icon: Clock, label: "Lỗi đồng hồ đếm", query: "Đồng hồ tính giờ thi không hiển thị hoặc bị đóng băng" },
  { icon: Upload, label: "Lỗi nộp bài thi", query: "Thí sinh không bấm nộp được bài thi EOS/PEA" },
  { icon: Laptop, label: "Sự cố thiết bị", query: "Máy tính của thí sinh bị sập nguồn hoặc hỏng phần cứng" },
  { icon: Phone, label: "Liên hệ hỗ trợ", query: "Cần liên hệ bộ phận hỗ trợ kỹ thuật hoặc trưởng ban coi thi như thế nào?" },
];

export function QuickActions({ onSelect }: QuickActionsProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2 px-4">
      {quickActions.map((action) => {
        const Icon = action.icon;
        return (
          <Button
            key={action.label}
            variant="outline"
            size="sm"
            className="gap-2 rounded-full border-border bg-card hover:bg-secondary hover:border-primary/30"
            onClick={() => onSelect(action.query)}
          >
            <Icon className="h-3.5 w-3.5 text-primary" />
            <span className="text-xs">{action.label}</span>
          </Button>
        );
      })}
    </div>
  );
}
