import { appMessageSummary } from "@/messageProtocol";
import type { ModuleContact, ModuleStatus, StoredMessage } from "@/types";

export const RAW_PROVIDER_MODULE_ACK = "module_ack";

export function contactName(contact: ModuleContact) {
  if (isFileHelperContact(contact)) {
    return contact.remark || contact.nickname || "文件传输助手";
  }
  const name = contact.remark || contact.nickname || contact.alias;
  if (name) {
    return name;
  }
  return isRoomContact(contact) ? "未命名群聊" : "未命名好友";
}

export function contactSecondary(contact: ModuleContact) {
  const nickname = contact.nickname && contact.nickname !== contactName(contact) ? contact.nickname : "";
  const parts = [nickname, contact.alias].filter(Boolean);
  return parts.join(" · ") || "-";
}

export function contactKindText(contact: ModuleContact) {
  return isRoomContact(contact) ? "群聊" : "好友";
}

export function selectedChatTitle(wxid: string, contact?: ModuleContact) {
  if (contact) {
    return contactName(contact);
  }
  if (!wxid) {
    return "未选择好友";
  }
  return wxid.toLowerCase().endsWith("@chatroom") ? "未收录群聊" : "未收录好友";
}

export function selectedSendTargetId(wxid: string, contact?: ModuleContact) {
  return contact?.wxid || wxid;
}

export function messageChatId(message: StoredMessage) {
  if (message.chat_id) {
    return message.chat_id;
  }
  if (message.room_id) {
    return message.room_id;
  }
  if (message.direction === "sent") {
    return message.to_wxid || message.from_wxid || message.sender_wxid || "";
  }
  return message.from_wxid || message.sender_wxid || message.to_wxid || "";
}

export function messageIsRoom(message: StoredMessage, contact?: ModuleContact) {
  const chatId = messageChatId(message).toLowerCase();
  return Boolean(contact?.chatroom || message.chat_kind === "room" || message.room_id || chatId.endsWith("@chatroom"));
}

export function messageContactName(message: StoredMessage, contact?: ModuleContact) {
  if (contact) {
    return contactName(contact);
  }
  if (message.chat_display_name) {
    return message.chat_display_name;
  }
  return messageIsRoom(message) ? "未收录群聊" : "未收录好友";
}

export function messageSenderName(message: StoredMessage, contactByWxid: Map<string, ModuleContact>, module?: ModuleStatus) {
  const outgoing = message.direction === "sent";
  if (outgoing) {
    return moduleSelfName(module);
  }

  const senderWxid = message.sender_wxid || "";
  if (messageIsRoom(message) && !senderWxid) {
    return "群聊系统消息";
  }

  const wxid = senderWxid || message.from_wxid || "";
  const contact = wxid ? contactByWxid.get(wxid) : undefined;
  if (contact) {
    return contactName(contact);
  }

  if (messageIsRoom(message)) {
    return senderWxid ? "群成员" : "群聊";
  }
  return wxid && wxid === moduleOwnerWxid(module) ? moduleSelfName(module) : "对方";
}

export function moduleSelfName(module?: ModuleStatus) {
  return module?.device_nickname || "我";
}

export function messagePreview(message: StoredMessage, contactByWxid?: Map<string, ModuleContact>, module?: ModuleStatus) {
  const direction = message.direction === "sent" ? "发出" : "收到";
  const appMessage = appMessageSummary(message);
  const body = message.text?.trim() || appMessage?.title || message.media_name || messageTypeText(message.message_type);
  const sender = contactByWxid ? messageSenderName(message, contactByWxid, module) : "";
  return [direction, sender, body || "空消息"].filter(Boolean).join(" · ");
}

export function diagnosticValues(values?: string[]) {
  if (!values?.length) {
    return [];
  }
  const compact = values.map((value) => value.trim()).filter(Boolean);
  if (compact.length <= 6) {
    return compact;
  }
  return [...compact.slice(0, 6), `+${compact.length - 6}`];
}

export function parsePositiveInteger(value: string) {
  const text = value.trim();
  if (!/^[1-9]\d*$/.test(text)) {
    return undefined;
  }
  return Number.parseInt(text, 10);
}

export function hasEmojiActionInput(emojiMd5: string, emojiSourceId: string) {
  return Boolean(emojiMd5.trim() || parsePositiveInteger(emojiSourceId));
}

export function isRoomContact(contact: ModuleContact) {
  return Boolean(contact.chatroom || contact.wxid.toLowerCase().endsWith("@chatroom"));
}

export function isFileHelperContact(contact: ModuleContact) {
  return contact.wxid.toLowerCase() === "filehelper";
}

export function statusText(status?: string) {
  switch (status) {
    case "ready":
      return "就绪";
    case "pending":
      return "待发送";
    case "sending":
      return "发送中";
    case "failed":
      return "失败";
    case "disabled":
      return "已停用";
    case "unregistered":
      return "未注册";
    default:
      return status || "-";
  }
}

export function providerText(provider: string) {
  switch (provider) {
    case RAW_PROVIDER_MODULE_ACK:
      return "模块回执";
    case "lsposed":
      return "LSPosed";
    case "module":
      return "模块";
    default:
      return provider;
  }
}

export function messageTypeText(type: number) {
  switch (type) {
    case 1:
      return "文本";
    case 3:
      return "图片";
    case 34:
      return "语音";
    case 43:
      return "视频";
    case 47:
      return "表情";
    case 48:
      return "位置";
    case 49:
      return "链接/文件";
    case 62:
      return "小视频";
    case 822083633:
      return "引用";
    case 10000:
      return "系统消息";
    default:
      return `类型 ${type}`;
  }
}

export function moduleOwnerWxid(module?: ModuleStatus) {
  return module?.device_wxid || "";
}

export function chatKindForContact(wxid: string, contact?: ModuleContact) {
  if (contact?.chatroom || wxid.toLowerCase().endsWith("@chatroom")) {
    return "room";
  }
  return "direct";
}

export function formatDate(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

export function formatTimeAgo(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const diff = Date.now() - date.getTime();
  if (diff < 60_000) return "刚刚";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`;
  return date.toLocaleDateString("zh-CN");
}
