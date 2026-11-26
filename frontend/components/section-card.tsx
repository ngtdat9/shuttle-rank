import type { ReactNode } from "react";

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

type SectionCardProps = {
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function SectionCard({
  title,
  description,
  action,
  children,
  className,
}: SectionCardProps) {
  const hasHeader = Boolean(title || description || action);

  return (
    <Card className={cn("sr-panel rounded-[24px] [--card-spacing:--spacing(5)] md:[--card-spacing:--spacing(6)]", className)}>
      {hasHeader ? (
        <CardHeader>
          <div className="min-w-0">
            {title ? <CardTitle className="text-lg font-semibold">{title}</CardTitle> : null}
            {description ? <CardDescription>{description}</CardDescription> : null}
          </div>
          {action ? <CardAction>{action}</CardAction> : null}
        </CardHeader>
      ) : null}
      <CardContent>{children}</CardContent>
    </Card>
  );
}
