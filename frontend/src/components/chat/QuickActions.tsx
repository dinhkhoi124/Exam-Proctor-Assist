import { Wifi, LogIn, Globe, Clock, Download, Laptop, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";

interface QuickActionsProps {
  onSelect: (query: string) => void;
}

const quickActions = [
  { icon: Wifi, label: "Sự cố WiFi phòng thi", query: "Thí sinh không kết nối được WiFi phòng thi" },
  { icon: LogIn, label: "Kết nối WiFi thi", query: "Hướng dẫn kết nối wifi phòng thi" },
  { icon: Globe, label: "Ký tên điện tử", query: "Hướng dẫn sinh viên ký tên điện tử" },
  { icon: Clock, label: "Sinh viên đi muộn", query: "Sinh viên đi muộn" },
  { icon: Download, label: "Tải EOS", query: "Hướng dẫn tải EOS" },
  { icon: Laptop, label: "Sự cố thiết bị", query: "Máy tính của sinh viên bị treo" },
  { icon: Phone, label: "Email phòng đào tạo", query: "Email của phòng đào tạo là gì?" },
];

export function QuickActions({ onSelect }: QuickActionsProps) {
  return (
    <div className="flex w-full flex-wrap justify-center gap-1.5 px-0 sm:gap-2 sm:px-4">
      {quickActions.map((action) => {
        const Icon = action.icon;
        return (
          <Button
            key={action.label}
            variant="outline"
            size="sm"
            className="max-w-full gap-1.5 rounded-full border-border bg-card px-3 hover:border-primary/30 hover:bg-secondary sm:gap-2"
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
