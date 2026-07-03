import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MessageBubble } from "@/messageComponents";
import type { ModuleContact, ModuleStatus, StoredMessage } from "@/types";

const moduleInfo: ModuleStatus = {
  device: "phone-a",
  device_nickname: "我的微信",
  device_wxid: "wxid_self"
};

function contactMap(...contacts: ModuleContact[]) {
  return new Map(contacts.map((contact) => [contact.wxid, contact]));
}

function renderMessage(message: Partial<StoredMessage>, contacts = contactMap()) {
  return renderToStaticMarkup(
    <MessageBubble
      message={
        {
          id: 1,
          device: "phone-a",
          direction: "recv",
          from_wxid: "wxid_friend",
          to_wxid: "wxid_self",
          text: "",
          message_type: 1,
          created_at: "2026-07-02T12:00:00Z",
          ...message
        } as StoredMessage
      }
      adminPassword="admin"
      contactByWxid={contacts}
      module={moduleInfo}
    />
  );
}

describe("message components", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders incoming text with resolved sender name", () => {
    const html = renderMessage(
      {
        text: "你好",
        sender_wxid: "wxid_friend"
      },
      contactMap({
        id: 1,
        device: "phone-a",
        wxid: "wxid_friend",
        nickname: "两碗冰",
        chatroom: false,
        deleted: false
      })
    );

    expect(html).toContain("收到");
    expect(html).toContain("两碗冰");
    expect(html).toContain("你好");
  });

  it("renders appmsg summary and diagnostics without leaking raw payload fields", () => {
    const html = renderMessage({
      message_type: 49,
      appmsg_subtype: "mini_program",
      appmsg_title: "小程序标题",
      appmsg_description: "页面说明",
      unsupported: ["direct_build_needs_sample"],
      evidence: ["message.type=49", "appmsg.type=33"]
    });

    expect(html).toContain("小程序");
    expect(html).toContain("小程序标题");
    expect(html).toContain("页面说明");
    expect(html).toContain("direct_build_needs_sample");
    expect(html).toContain("appmsg.type=33");
    expect(html).not.toContain("payload_json");
    expect(html).not.toContain("media_base64");
  });

  it("renders missing media attachments as explicit pending upload text", () => {
    const html = renderMessage({
      message_type: 43,
      media_kind: "video",
      media_name: "clip.mp4"
    });

    expect(html).toContain("clip.mp4");
    expect(html).toContain("附件文件还没有上传");
  });

  it("renders uploaded media attachments with authenticated URLs", () => {
    vi.stubGlobal("window", { location: { origin: "https://wx.example.test" } });

    const imageHTML = renderMessage({
      message_type: 3,
      media_kind: "image",
      media_name: "photo.jpg",
      media_url: "/api/media/device-a/photo.jpg?download=1"
    });
    expect(imageHTML).toContain("photo.jpg");
    expect(imageHTML).toContain("/api/media/device-a/photo.jpg?download=1&amp;password=admin");

    const voiceHTML = renderMessage({
      message_type: 34,
      media_kind: "voice",
      media_name: "voice.amr",
      media_size: 2048,
      media_url: "/api/media/device-a/voice.amr"
    });
    expect(voiceHTML).toContain("voice.amr");
    expect(voiceHTML).toContain("<audio");
    expect(voiceHTML).toContain("/api/media/device-a/voice.amr?password=admin");
    expect(voiceHTML).toContain("下载 · 2.0 KB");

    const fileHTML = renderMessage({
      message_type: 49,
      appmsg_subtype: "file",
      appmsg_file_name: "report.pdf",
      media_url: "/api/media/device-a/report.pdf"
    });
    expect(fileHTML).toContain("report.pdf");
    expect(fileHTML).toContain("download=\"report.pdf\"");
    expect(fileHTML).toContain("/api/media/device-a/report.pdf?password=admin");
  });
});
