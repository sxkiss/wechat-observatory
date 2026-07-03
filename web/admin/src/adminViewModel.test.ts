import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RAW_PROVIDER_MODULE_ACK,
  chatKindForContact,
  contactKindText,
  contactName,
  contactSecondary,
  diagnosticValues,
  formatDate,
  formatTimeAgo,
  hasEmojiActionInput,
  isFileHelperContact,
  isRoomContact,
  messageChatId,
  messageContactName,
  messageIsRoom,
  messagePreview,
  messageSenderName,
  messageTypeText,
  moduleOwnerWxid,
  parsePositiveInteger,
  providerText,
  selectedChatTitle,
  selectedSendTargetId,
  statusText
} from "@/adminViewModel";
import type { ModuleContact, ModuleStatus, StoredMessage } from "@/types";

function contact(overrides: Partial<ModuleContact>): ModuleContact {
  return {
    id: 1,
    device: "device-a",
    wxid: "wxid_contact",
    chatroom: false,
    deleted: false,
    ...overrides
  };
}

function message(overrides: Partial<StoredMessage>): StoredMessage {
  return {
    id: 1,
    device: "device-a",
    direction: "recv",
    text: "",
    message_type: 1,
    ...overrides
  };
}

describe("adminViewModel", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("names contacts and distinguishes room/direct chats", () => {
    const room = contact({ wxid: "room-a@chatroom", chatroom: true, nickname: "测试群" });
    const direct = contact({ wxid: "wxid_friend", nickname: "好友昵称", remark: "好友备注", alias: "alias-a" });
    const fileHelper = contact({ wxid: "filehelper" });

    expect(contactName(room)).toBe("测试群");
    expect(contactName(direct)).toBe("好友备注");
    expect(contactName(fileHelper)).toBe("文件传输助手");
    expect(contactSecondary(direct)).toBe("好友昵称 · alias-a");
    expect(contactKindText(room)).toBe("群聊");
    expect(contactKindText(direct)).toBe("好友");
    expect(isRoomContact(room)).toBe(true);
    expect(isFileHelperContact(fileHelper)).toBe(true);
  });

  it("builds selected chat titles from either contacts or wxid shape", () => {
    expect(selectedChatTitle("", undefined)).toBe("未选择好友");
    expect(selectedChatTitle("room-a@chatroom", undefined)).toBe("未收录群聊");
    expect(selectedChatTitle("wxid_friend", undefined)).toBe("未收录好友");
    expect(selectedChatTitle("wxid_friend", contact({ remark: "好友备注" }))).toBe("好友备注");
  });

  it("keeps the send target as the stable wxid or room id instead of the display name", () => {
    const room = contact({ wxid: "12345@chatroom", chatroom: true, remark: "有风测试群", nickname: "群昵称" });
    const direct = contact({ wxid: "wxid_friend", remark: "两碗冰", nickname: "好友昵称", alias: "friend-alias" });

    expect(selectedChatTitle(room.wxid, room)).toBe("有风测试群");
    expect(selectedSendTargetId(room.wxid, room)).toBe("12345@chatroom");
    expect(selectedSendTargetId(direct.wxid, direct)).toBe("wxid_friend");
    expect(selectedSendTargetId("unindexed-room@chatroom", undefined)).toBe("unindexed-room@chatroom");
  });

  it("resolves stable chat ids for sent, received, and room messages", () => {
    expect(messageChatId(message({ chat_id: "chat-a", room_id: "room-a@chatroom" }))).toBe("chat-a");
    expect(messageChatId(message({ room_id: "room-a@chatroom" }))).toBe("room-a@chatroom");
    expect(messageChatId(message({ direction: "sent", to_wxid: "wxid_target", from_wxid: "wxid_self" }))).toBe("wxid_target");
    expect(messageChatId(message({ direction: "recv", from_wxid: "wxid_friend", to_wxid: "wxid_self" }))).toBe("wxid_friend");
  });

  it("uses room evidence from contact, message kind, room id, or chat suffix", () => {
    expect(messageIsRoom(message({ from_wxid: "room-a@chatroom" }))).toBe(true);
    expect(messageIsRoom(message({ chat_kind: "room" }))).toBe(true);
    expect(messageIsRoom(message({ room_id: "room-a@chatroom" }))).toBe(true);
    expect(messageIsRoom(message({ from_wxid: "wxid_friend" }), contact({ chatroom: true }))).toBe(true);
    expect(messageIsRoom(message({ from_wxid: "wxid_friend" }))).toBe(false);
  });

  it("resolves conversation and sender labels without leaking raw ids into normal labels", () => {
    const room = contact({ wxid: "room-a@chatroom", chatroom: true, remark: "测试群" });
    const member = contact({ wxid: "wxid_member", remark: "成员备注" });
    const contactByWxid = new Map([[member.wxid, member]]);
    const module: ModuleStatus = { device: "device-a", device_wxid: "wxid_self", device_nickname: "机器人" };

    expect(messageContactName(message({ chat_display_name: "显示名" }))).toBe("显示名");
    expect(messageContactName(message({ room_id: "room-a@chatroom" }))).toBe("未收录群聊");
    expect(messageContactName(message({ from_wxid: "wxid_friend" }))).toBe("未收录好友");
    expect(messageContactName(message({ from_wxid: "room-a@chatroom" }), room)).toBe("测试群");

    expect(messageSenderName(message({ direction: "sent", to_wxid: "wxid_friend" }), contactByWxid, module)).toBe("机器人");
    expect(messageSenderName(message({ room_id: "room-a@chatroom" }), contactByWxid, module)).toBe("群聊系统消息");
    expect(messageSenderName(message({ room_id: "room-a@chatroom", sender_wxid: "wxid_member" }), contactByWxid, module)).toBe("成员备注");
    expect(messageSenderName(message({ room_id: "room-a@chatroom", sender_wxid: "wxid_unknown" }), contactByWxid, module)).toBe("群成员");
    expect(messageSenderName(message({ from_wxid: "wxid_self" }), contactByWxid, module)).toBe("机器人");
  });

  it("formats message previews with text, appmsg, media, and type fallbacks", () => {
    const contactByWxid = new Map([
      ["wxid_friend", contact({ wxid: "wxid_friend", remark: "好友备注" })]
    ]);
    const module: ModuleStatus = { device: "device-a", device_nickname: "机器人" };

    expect(messagePreview(message({ text: "  hi  ", from_wxid: "wxid_friend" }), contactByWxid, module)).toBe("收到 · 好友备注 · hi");
    expect(
      messagePreview(
        message({ message_type: 49, appmsg_subtype: "link", appmsg_title: "Article", from_wxid: "wxid_friend" }),
        contactByWxid,
        module
      )
    ).toBe("收到 · 好友备注 · Article");
    expect(messagePreview(message({ message_type: 3, media_name: "photo.jpg", direction: "sent" }), contactByWxid, module)).toBe(
      "发出 · 机器人 · photo.jpg"
    );
    expect(messagePreview(message({ message_type: 34 }))).toBe("收到 · 语音");
  });

  it("compacts unsupported and evidence diagnostics for message bubbles", () => {
    expect(diagnosticValues()).toEqual([]);
    expect(diagnosticValues([])).toEqual([]);
    expect(diagnosticValues([" raw_xml.appmsg ", "", " message.type=49 "])).toEqual([
      "raw_xml.appmsg",
      "message.type=49"
    ]);
    expect(diagnosticValues(["a", "b", "c", "d", "e", "f"])).toEqual(["a", "b", "c", "d", "e", "f"]);
    expect(diagnosticValues(["a", "b", "c", "d", "e", "f", "g", "h"])).toEqual([
      "a",
      "b",
      "c",
      "d",
      "e",
      "f",
      "+2"
    ]);
  });

  it("parses positive integer form fields without accepting partial or invalid input", () => {
    expect(parsePositiveInteger("42")).toBe(42);
    expect(parsePositiveInteger(" 9001 ")).toBe(9001);
    expect(parsePositiveInteger("0")).toBeUndefined();
    expect(parsePositiveInteger("-1")).toBeUndefined();
    expect(parsePositiveInteger("12abc")).toBeUndefined();
    expect(parsePositiveInteger("abc")).toBeUndefined();
    expect(parsePositiveInteger("")).toBeUndefined();
  });

  it("only treats emoji send controls as active when md5 or a valid source id is present", () => {
    expect(hasEmojiActionInput("", "")).toBe(false);
    expect(hasEmojiActionInput("", "abc")).toBe(false);
    expect(hasEmojiActionInput("", "12abc")).toBe(false);
    expect(hasEmojiActionInput("", "42")).toBe(true);
    expect(hasEmojiActionInput("  md5-value  ", "abc")).toBe(true);
  });

  it("keeps status, provider, message type, and chat kind labels explicit", () => {
    expect(statusText("ready")).toBe("就绪");
    expect(statusText("failed")).toBe("失败");
    expect(statusText()).toBe("-");
    expect(providerText(RAW_PROVIDER_MODULE_ACK)).toBe("模块回执");
    expect(providerText("lsposed")).toBe("LSPosed");
    expect(messageTypeText(822083633)).toBe("引用");
    expect(messageTypeText(10000)).toBe("系统消息");
    expect(messageTypeText(777)).toBe("类型 777");
    expect(chatKindForContact("room-a@chatroom")).toBe("room");
    expect(chatKindForContact("wxid_friend")).toBe("direct");
    expect(moduleOwnerWxid({ device: "device-a", device_wxid: "wxid_self" })).toBe("wxid_self");
  });

  it("formats dates and relative times", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));

    expect(formatDate()).toBe("-");
    expect(formatDate("not-a-date")).toBe("not-a-date");
    expect(formatTimeAgo()).toBe("-");
    expect(formatTimeAgo("not-a-date")).toBe("not-a-date");
    expect(formatTimeAgo("2026-01-01T11:59:30Z")).toBe("刚刚");
    expect(formatTimeAgo("2026-01-01T11:30:00Z")).toBe("30 分钟前");
    expect(formatTimeAgo("2026-01-01T09:00:00Z")).toBe("3 小时前");
  });
});
