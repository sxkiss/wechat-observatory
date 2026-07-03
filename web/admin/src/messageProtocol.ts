import type { LiveMessageEvent, StoredMessage } from "@/types";

export type MediaActionKind = "image" | "video" | "voice" | "file";

export type AppMessageIcon = "link" | "file" | "mini_program" | "chat_history" | "quote" | "payment" | "appmsg";

export type AppMessageSummary = {
  label: string;
  icon: AppMessageIcon;
  title: string;
  detail?: string;
  url?: string;
};

type FileLike = {
  type?: string;
  name?: string;
};

export function mediaActionKind(file: FileLike): MediaActionKind {
  const type = file.type || "";
  const name = file.name || "";
  if (type.startsWith("image/")) {
    return "image";
  }
  if (type.startsWith("video/")) {
    return "video";
  }
  if (/^(audio\/amr|audio\/silk|audio\/x-silk)$/i.test(type) || /\.(amr|silk)$/i.test(name)) {
    return "voice";
  }
  return "file";
}

export function mediaKindFromType(type?: number) {
  switch (type) {
    case 3:
      return "image";
    case 34:
      return "voice";
    case 43:
    case 62:
      return "video";
    case 47:
      return "emoji";
    case 48:
      return "location";
    case 49:
      return "file";
    default:
      return "";
  }
}

export function hasMediaAttachment(message: Partial<StoredMessage>) {
  if (message.media_url || message.media_kind) {
    return true;
  }
  if (message.message_type === 49) {
    return message.appmsg_subtype === "file";
  }
  return Boolean(mediaKindFromType(message.message_type));
}

export function appMessageSummary(message: Partial<StoredMessage>): AppMessageSummary | null {
  if (message.message_type !== 49 && !message.appmsg_subtype) {
    return null;
  }
  const subtype = message.appmsg_subtype || "unknown";
  const title = firstText(message.appmsg_title, message.appmsg_file_name, message.text, appMessageLabel(subtype));
  const detail = firstText(message.appmsg_description, message.appmsg_app_name, message.appmsg_file_name);
  return {
    label: appMessageLabel(subtype),
    icon: appMessageIconName(subtype),
    title,
    detail,
    url: message.appmsg_url
  };
}

export function appMessageLabel(subtype: string) {
  switch (subtype) {
    case "link":
      return "链接";
    case "file":
      return "文件";
    case "mini_program":
      return "小程序";
    case "chat_history":
      return "聊天记录";
    case "quote":
      return "引用";
    case "transfer":
      return "转账";
    case "red_packet":
      return "红包";
    case "unknown":
      return "未支持类型";
    default:
      return subtype || "AppMsg";
  }
}

export function appMessageIconName(subtype: string): AppMessageIcon {
  switch (subtype) {
    case "link":
      return "link";
    case "file":
      return "file";
    case "mini_program":
      return "mini_program";
    case "chat_history":
      return "chat_history";
    case "quote":
      return "quote";
    case "transfer":
    case "red_packet":
      return "payment";
    default:
      return "appmsg";
  }
}

export function firstText(...values: Array<string | undefined>) {
  for (const value of values) {
    const text = value?.trim();
    if (text) {
      return text;
    }
  }
  return "";
}

export function formatBytes(value?: number) {
  if (!value || value <= 0) {
    return "";
  }
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function mediaURL(path: string, password: string, origin: string) {
  const url = new URL(path, origin);
  if (password) {
    url.searchParams.set("password", password);
  }
  return `${url.pathname}${url.search}`;
}

export function liveEventTouchesChat(event: Partial<LiveMessageEvent>, chatId: string) {
  return [event.chat_id, event.from, event.to, event.room_id, event.sender].some((value) => value === chatId);
}
