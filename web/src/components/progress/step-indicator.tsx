import { motion } from "motion/react";
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
        className={`text-sm shrink-0 w-36 sm:w-48 ${
          status === "pending"
            ? "text-muted-foreground"
            : "text-foreground"
        }`}
      >
        {label}
      </span>
      {status === "active" ? (
        <div className="relative flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
          {/* Filled portion with pulse */}
          <motion.div
            className="absolute inset-y-0 left-0 rounded-full bg-foreground/80"
            style={{ width: `${value}%` }}
            animate={{ opacity: [0.7, 1, 0.7] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          />
          {/* Shimmer sweep — never looks frozen */}
          <motion.div
            className="absolute inset-y-0 w-16 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            animate={{ x: ["-4rem", "100%"] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: "linear", repeatDelay: 0.5 }}
          />
        </div>
      ) : (
        <Progress value={value} className="flex-1 h-1.5" />
      )}
      {status === "done" && (
        <Check className="w-4 h-4 text-accent shrink-0" />
      )}
    </div>
  );
}
