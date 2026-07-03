import { Wifi, WifiOff } from "lucide-react";
import type { ReactNode } from "react";

import { statusText } from "@/adminViewModel";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export function ConnectionBadge({ connected, enabled }: { connected: boolean; enabled: boolean }) {
  if (!enabled) {
    return (
      <Badge variant="secondary">
        <WifiOff className="mr-1 h-3.5 w-3.5" />
        实时关闭
      </Badge>
    );
  }
  return (
    <Badge variant={connected ? "success" : "warning"}>
      {connected ? <Wifi className="mr-1 h-3.5 w-3.5" /> : <WifiOff className="mr-1 h-3.5 w-3.5" />}
      {connected ? "实时已连接" : "实时待连接"}
    </Badge>
  );
}

export function StatusBadge({ status }: { status?: string }) {
  if (status === "ready") {
    return <Badge variant="success">就绪</Badge>;
  }
  if (status === "pending" || status === "sending") {
    return <Badge variant="warning">{statusText(status)}</Badge>;
  }
  if (status === "failed" || status === "unregistered") {
    return <Badge variant="destructive">{statusText(status)}</Badge>;
  }
  if (status === "disabled") {
    return <Badge variant="secondary">{statusText(status)}</Badge>;
  }
  return <Badge variant="secondary">{statusText(status)}</Badge>;
}

export function MetricCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="flex min-h-[88px] items-center justify-between p-4">
        <div className="min-w-0">
          <div className="text-xs text-muted-foreground">{title}</div>
          <div className="mt-1 truncate text-xl font-semibold">{value}</div>
        </div>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-secondary text-muted-foreground">
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}

export function SignalPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background px-2 py-2">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className="mt-1 truncate text-xs font-medium">{value}</div>
    </div>
  );
}

export function EmptyState({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="grid min-h-[120px] place-items-center rounded-lg border border-dashed bg-background/60 p-6 text-center text-sm text-muted-foreground">
      <div className="grid justify-items-center gap-2">
        <div className="text-muted-foreground">{icon}</div>
        <div>{text}</div>
      </div>
    </div>
  );
}
