import { describe, expect, it } from "vitest";

import {
  appMessageIconName,
  appMessageLabel,
  appMessageSummary,
  firstText,
  formatBytes,
  hasMediaAttachment,
  liveEventTouchesChat,
  mediaActionKind,
  mediaKindFromType,
  mediaURL
} from "@/messageProtocol";

describe("messageProtocol", () => {
  it("maps selected files to outbound action kinds", () => {
    expect(mediaActionKind({ type: "image/png", name: "photo.png" })).toBe("image");
    expect(mediaActionKind({ type: "video/mp4", name: "clip.mp4" })).toBe("video");
    expect(mediaActionKind({ type: "audio/amr", name: "voice.bin" })).toBe("voice");
    expect(mediaActionKind({ type: "", name: "voice.silk" })).toBe("voice");
    expect(mediaActionKind({ type: "application/pdf", name: "doc.pdf" })).toBe("file");
  });

  it("maps wechat message_type values to media kinds", () => {
    expect(mediaKindFromType(3)).toBe("image");
    expect(mediaKindFromType(34)).toBe("voice");
    expect(mediaKindFromType(43)).toBe("video");
    expect(mediaKindFromType(62)).toBe("video");
    expect(mediaKindFromType(47)).toBe("emoji");
    expect(mediaKindFromType(48)).toBe("location");
    expect(mediaKindFromType(49)).toBe("file");
    expect(mediaKindFromType(1)).toBe("");
  });

  it("detects media attachments without treating every appmsg as a file", () => {
    expect(hasMediaAttachment({ media_url: "/api/media/demo.png" })).toBe(true);
    expect(hasMediaAttachment({ media_kind: "image" })).toBe(true);
    expect(hasMediaAttachment({ message_type: 3 })).toBe(true);
    expect(hasMediaAttachment({ message_type: 49, appmsg_subtype: "file" })).toBe(true);
    expect(hasMediaAttachment({ message_type: 49, appmsg_subtype: "link" })).toBe(false);
    expect(hasMediaAttachment({ message_type: 1 })).toBe(false);
  });

  it("summarizes appmsg cards for display and diagnostics", () => {
    expect(appMessageSummary({ message_type: 49, appmsg_subtype: "link", appmsg_title: "Article", appmsg_url: "https://example.test/a" })).toMatchObject({
      label: "链接",
      icon: "link",
      title: "Article",
      url: "https://example.test/a"
    });
    expect(appMessageSummary({ message_type: 49, appmsg_subtype: "mini_program", appmsg_title: "Mini", appmsg_description: "Page" })).toMatchObject({
      label: "小程序",
      icon: "mini_program",
      title: "Mini",
      detail: "Page"
    });
    expect(appMessageSummary({ message_type: 49, appmsg_subtype: "chat_history", appmsg_title: "Records" })).toMatchObject({
      label: "聊天记录",
      icon: "chat_history"
    });
    expect(appMessageSummary({ message_type: 49, appmsg_subtype: "file", appmsg_file_name: "report.pdf", text: "fallback" })).toMatchObject({
      label: "文件",
      icon: "file",
      title: "report.pdf"
    });
    expect(appMessageSummary({ message_type: 49 })).toMatchObject({
      label: "未支持类型",
      icon: "appmsg",
      title: "未支持类型"
    });
    expect(appMessageSummary({ message_type: 1 })).toBeNull();
  });

  it("keeps appmsg label and icon mappings explicit", () => {
    expect(appMessageLabel("quote")).toBe("引用");
    expect(appMessageIconName("quote")).toBe("quote");
    expect(appMessageLabel("transfer")).toBe("转账");
    expect(appMessageIconName("transfer")).toBe("payment");
    expect(appMessageLabel("red_packet")).toBe("红包");
    expect(appMessageIconName("red_packet")).toBe("payment");
    expect(appMessageLabel("custom_type")).toBe("custom_type");
    expect(appMessageIconName("custom_type")).toBe("appmsg");
  });

  it("normalizes short text and byte labels", () => {
    expect(firstText(undefined, "  ", "  ok  ")).toBe("ok");
    expect(firstText()).toBe("");
    expect(formatBytes()).toBe("");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });

  it("builds media URLs relative to the current origin and preserves existing query params", () => {
    expect(mediaURL("/api/media/device-a/image.jpg", "admin-password", "https://wx.example.test")).toBe(
      "/api/media/device-a/image.jpg?password=admin-password"
    );
    expect(mediaURL("/api/media/device-a/image.jpg?download=1", "admin-password", "https://wx.example.test")).toBe(
      "/api/media/device-a/image.jpg?download=1&password=admin-password"
    );
    expect(mediaURL("api/media/device-a/image.jpg", "", "https://wx.example.test/admin")).toBe(
      "/api/media/device-a/image.jpg"
    );
    expect(mediaURL("https://cdn.example.test/api/media/device-a/image.jpg", "admin-password", "https://wx.example.test")).toBe(
      "/api/media/device-a/image.jpg?password=admin-password"
    );
  });

  it("checks whether a live event belongs to the selected chat", () => {
    expect(liveEventTouchesChat({ chat_id: "room@chatroom" }, "room@chatroom")).toBe(true);
    expect(liveEventTouchesChat({ room_id: "room@chatroom" }, "room@chatroom")).toBe(true);
    expect(liveEventTouchesChat({ room_id: "other@chatroom" }, "room@chatroom")).toBe(false);
    expect(liveEventTouchesChat({ from: "wxid_a", to: "wxid_b" }, "wxid_b")).toBe(true);
    expect(liveEventTouchesChat({ sender: "wxid_member" }, "wxid_other")).toBe(false);
  });
});
