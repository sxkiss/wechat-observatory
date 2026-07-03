import { renderToStaticMarkup } from "react-dom/server";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

function markup(element: ReactNode) {
  return renderToStaticMarkup(<>{element}</>);
}

describe("ui components", () => {
  it("merges Tailwind classes with caller overrides", () => {
    expect(cn("px-2 text-sm", false && "hidden", ["font-medium"], { "px-4": true })).toBe(
      "text-sm font-medium px-4"
    );
  });

  it("renders button variants, sizes, attributes, and class overrides", () => {
    const html = markup(
      <Button variant="destructive" size="xs" className="px-4" disabled>
        删除
      </Button>
    );

    expect(html).toContain("<button");
    expect(html).toContain("bg-destructive");
    expect(html).toContain("h-7");
    expect(html).toContain("text-xs");
    expect(html).toContain("px-4");
    expect(html).toContain("disabled=\"\"");
    expect(html).toContain(">删除</button>");
    expect(html).not.toContain("px-2");
  });

  it("renders badge variants with stable semantic colors", () => {
    const success = markup(<Badge variant="success">成功</Badge>);
    const warning = markup(<Badge variant="warning">等待</Badge>);
    const outline = markup(<Badge variant="outline">轮廓</Badge>);

    expect(success).toContain("bg-emerald-50");
    expect(warning).toContain("bg-amber-50");
    expect(outline).toContain("text-foreground");
  });

  it("renders form primitives with caller props", () => {
    expect(markup(<Input placeholder="搜索" disabled className="h-10" />)).toContain("placeholder=\"搜索\"");
    expect(markup(<Textarea placeholder="备注" className="min-h-[120px]" />)).toContain("min-h-[120px]");
    expect(markup(<Checkbox checked readOnly aria-label="启用" />)).toContain("type=\"checkbox\"");
    expect(markup(<Label htmlFor="field-a">名称</Label>)).toContain("for=\"field-a\"");
  });

  it("renders card and table structure without swallowing children", () => {
    const card = markup(
      <Card>
        <CardHeader>
          <CardTitle>标题</CardTitle>
        </CardHeader>
        <CardContent>内容</CardContent>
      </Card>
    );
    const table = markup(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>列</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>值</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    expect(card).toContain("rounded-lg");
    expect(card).toContain("<h2");
    expect(card).toContain("标题");
    expect(table).toContain("<table");
    expect(table).toContain("<thead");
    expect(table).toContain("<tbody");
    expect(table).toContain("值");
  });

  it("renders tabs active and inactive states", () => {
    const html = markup(
      <Tabs>
        <TabsList>
          <TabsTrigger active>消息</TabsTrigger>
          <TabsTrigger>设备</TabsTrigger>
        </TabsList>
        <TabsContent>内容</TabsContent>
      </Tabs>
    );

    expect(html).toContain("grid gap-4");
    expect(html).toContain("bg-background text-foreground shadow-sm");
    expect(html).toContain("hover:text-foreground");
    expect(html).toContain("内容");
  });

  it("renders dialog only when open and exposes close affordances", () => {
    expect(markup(<Dialog open={false} onOpenChange={() => undefined}>关闭</Dialog>)).toBe("");

    const html = markup(
      <Dialog open onOpenChange={() => undefined}>
        <DialogContent onClose={() => undefined}>
          <DialogHeader>
            <DialogTitle>发送微信消息</DialogTitle>
            <DialogDescription>测试对象</DialogDescription>
          </DialogHeader>
          <DialogFooter>操作</DialogFooter>
        </DialogContent>
      </Dialog>
    );

    expect(html).toContain("fixed inset-0");
    expect(html).toContain("aria-label=\"关闭\"");
    expect(html).toContain("发送微信消息");
    expect(html).toContain("测试对象");
    expect(html).toContain("操作");
  });
});
