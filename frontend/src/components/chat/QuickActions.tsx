import { Wifi, LogIn, Globe, Clock, Upload, Laptop, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";

interface QuickActionsProps {
  onSelect: (query: string) => void;
}

const quickActions = [
  { icon: Wifi, label: "WiFi Issues", query: "Student cannot connect to exam WiFi" },
  { icon: LogIn, label: "Login Problems", query: "Student cannot log in to exam portal" },
  { icon: Globe, label: "Browser Issues", query: "Exam page not loading in browser" },
  { icon: Clock, label: "Timer Issues", query: "Exam timer is not showing" },
  { icon: Upload, label: "Submit Problems", query: "Cannot submit exam answers" },
  { icon: Laptop, label: "Hardware Issues", query: "Student laptop is not working" },
  { icon: Phone, label: "Contact Support", query: "Who should I contact for help?" },
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
