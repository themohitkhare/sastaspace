import { Check } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface StepIndicatorProps {
  label: string;
  value: number;
  status: "pending" | "active" | "done";
}

export function StepIndicator({ label, value, status }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-3">
      <span
        className={`text-sm shrink-0 w-48 ${
          status === "pending"
            ? "text-muted-foreground"
            : "text-foreground"
        }`}
      >
        {label}
      </span>
      <Progress value={value} className="flex-1 h-1.5" />
      {status === "done" && (
        <Check className="w-4 h-4 text-primary shrink-0" />
      )}
    </div>
  );
}
