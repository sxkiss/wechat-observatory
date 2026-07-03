import { Activity } from "lucide-react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ConnectionBadge, EmptyState, MetricCard, SignalPill, StatusBadge } from "@/adminWidgets";

describe("admin widgets", () => {
  it("renders connection and status badges with localized states", () => {
    expect(renderToStaticMarkup(<ConnectionBadge connected enabled />)).toContain("实时已连接");
    expect(renderToStaticMarkup(<ConnectionBadge connected={false} enabled />)).toContain("实时待连接");
    expect(renderToStaticMarkup(<ConnectionBadge connected={false} enabled={false} />)).toContain("实时关闭");

    expect(renderToStaticMarkup(<StatusBadge status="ready" />)).toContain("就绪");
    expect(renderToStaticMarkup(<StatusBadge status="failed" />)).toContain("失败");
  });

  it("renders compact metric and empty-state blocks", () => {
    const metric = renderToStaticMarkup(<MetricCard title="设备" value="phone-a" icon={<Activity className="h-4 w-4" />} />);
    const signal = renderToStaticMarkup(<SignalPill label="最近轮询" value="刚刚" />);
    const empty = renderToStaticMarkup(<EmptyState icon={<Activity className="h-4 w-4" />} text="暂无数据" />);

    expect(metric).toContain("设备");
    expect(metric).toContain("phone-a");
    expect(signal).toContain("最近轮询");
    expect(signal).toContain("刚刚");
    expect(empty).toContain("暂无数据");
  });
});
