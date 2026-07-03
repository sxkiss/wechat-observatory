import { Download, FileText, ImageIcon, Link as LinkIcon, MessageCircle, Mic, Paperclip, ShieldCheck, Smartphone, Video } from "lucide-react";

import { diagnosticValues, formatDate, messageSenderName, messageTypeText, providerText } from "@/adminViewModel";
import { Badge } from "@/components/ui/badge";
import { appMessageSummary, formatBytes, hasMediaAttachment, mediaKindFromType, mediaURL, type AppMessageSummary } from "@/messageProtocol";
import type { ModuleContact, ModuleStatus, StoredMessage } from "@/types";

export function MessageBubble({
  message,
  adminPassword,
  contactByWxid,
  module
}: {
  message: StoredMessage;
  adminPassword: string;
  contactByWxid: Map<string, ModuleContact>;
  module?: ModuleStatus;
}) {
  const outgoing = message.direction === "sent";
  const hasAttachment = hasMediaAttachment(message);
  const appMessage = appMessageSummary(message);
  const senderName = messageSenderName(message, contactByWxid, module);
  return (
    <div className={outgoing ? "flex justify-end" : "flex justify-start"}>
      <div
        className={
          outgoing
            ? "max-w-[82%] rounded-lg border border-primary/20 bg-primary px-3 py-2 text-primary-foreground shadow-sm"
            : "max-w-[82%] rounded-lg border bg-secondary px-3 py-2 text-secondary-foreground shadow-sm"
        }
      >
        <div className="mb-1 flex flex-wrap items-center gap-2 text-xs opacity-80">
          <span>{outgoing ? "发出" : "收到"}</span>
          <span className="font-medium">{senderName}</span>
          {message.raw_provider ? <span>{providerText(message.raw_provider)}</span> : null}
          {message.message_type ? <span>{messageTypeText(message.message_type)}</span> : null}
          {appMessage ? <span>{appMessage.label}</span> : null}
          <span>{formatDate(message.created_at)}</span>
        </div>
        {message.text ? <div className="whitespace-pre-wrap break-words text-sm leading-6">{message.text}</div> : null}
        {appMessage ? <AppMessageCard summary={appMessage} outgoing={outgoing} /> : null}
        {hasAttachment ? <MessageAttachment message={message} adminPassword={adminPassword} outgoing={outgoing} /> : null}
        <MessageDiagnostics message={message} outgoing={outgoing} />
      </div>
    </div>
  );
}

function AppMessageCard({ summary, outgoing }: { summary: AppMessageSummary; outgoing: boolean }) {
  const shell = outgoing ? "border-primary-foreground/30 bg-primary-foreground/10" : "border-border bg-background/80";
  return (
    <div className={`mt-2 grid gap-1 rounded-md border p-3 text-xs ${shell}`}>
      <div className="flex min-w-0 items-center gap-2 font-medium">
        {appMessageIcon(summary.icon)}
        <span className="truncate">{summary.title}</span>
      </div>
      {summary.detail ? <div className="line-clamp-2 break-words opacity-80">{summary.detail}</div> : null}
      {summary.url ? (
        <a href={summary.url} target="_blank" rel="noreferrer" className="truncate text-primary underline-offset-4 hover:underline">
          {summary.url}
        </a>
      ) : null}
    </div>
  );
}

function MessageDiagnostics({ message, outgoing }: { message: StoredMessage; outgoing: boolean }) {
  const unsupported = diagnosticValues(message.unsupported);
  const evidence = diagnosticValues(message.evidence);
  if (unsupported.length === 0 && evidence.length === 0) {
    return null;
  }
  const shell = outgoing ? "border-primary-foreground/30 bg-primary-foreground/10" : "border-border bg-background/80";
  return (
    <div className={`mt-2 grid gap-2 rounded-md border p-2 text-[11px] ${shell}`}>
      {unsupported.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1">
          <span className="opacity-80">未支持</span>
          {unsupported.map((item) => (
            <Badge key={`unsupported-${item}`} variant="destructive">
              {item}
            </Badge>
          ))}
        </div>
      ) : null}
      {evidence.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1">
          <span className="opacity-80">证据</span>
          {evidence.map((item) => (
            <Badge key={`evidence-${item}`} variant="secondary">
              {item}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function MessageAttachment({
  message,
  adminPassword,
  outgoing
}: {
  message: StoredMessage;
  adminPassword: string;
  outgoing: boolean;
}) {
  const kind = message.media_kind || (message.appmsg_subtype === "file" ? "file" : mediaKindFromType(message.message_type)) || "file";
  const url = message.media_url ? mediaURL(message.media_url, adminPassword, window.location.origin) : "";
  const title = message.media_name || message.appmsg_file_name || message.appmsg_title || messageTypeText(message.message_type);
  const shell = outgoing ? "border-primary-foreground/30 bg-primary-foreground/10" : "border-border bg-background/80";

  if (!url) {
    return (
      <div className={`mt-2 rounded-md border border-dashed p-3 text-xs ${shell}`}>
        <div className="flex items-center gap-2 font-medium">
          {mediaIcon(kind)}
          <span>{title}</span>
        </div>
        <div className="mt-1 opacity-80">模块已收到此类消息，但附件文件还没有上传。</div>
      </div>
    );
  }

  if (kind === "image") {
    return (
      <a href={url} target="_blank" rel="noreferrer" className={`mt-2 block overflow-hidden rounded-md border ${shell}`}>
        <img src={url} alt={title} className="max-h-72 w-full object-contain" />
      </a>
    );
  }

  if (kind === "voice") {
    return (
      <div className={`mt-2 grid gap-2 rounded-md border p-3 ${shell}`}>
        <div className="flex items-center gap-2 text-sm font-medium">
          <Mic className="h-4 w-4" />
          <span>{title}</span>
        </div>
        <audio controls preload="none" src={url} className="h-9 w-full" />
        <MediaDownload url={url} name={title} size={message.media_size} />
      </div>
    );
  }

  if (kind === "video") {
    return (
      <div className={`mt-2 overflow-hidden rounded-md border ${shell}`}>
        <video controls preload="metadata" src={url} className="max-h-80 w-full bg-black" />
      </div>
    );
  }

  return (
    <div className={`mt-2 grid gap-2 rounded-md border p-3 text-sm ${shell}`}>
      <div className="flex items-center gap-2 font-medium">
        {mediaIcon(kind)}
        <span className="truncate">{title}</span>
      </div>
      <MediaDownload url={url} name={title} size={message.media_size} />
    </div>
  );
}

function MediaDownload({ url, name, size }: { url: string; name: string; size?: number }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      download={name}
      className="inline-flex h-8 w-fit items-center gap-2 rounded-md border bg-background px-3 text-xs text-foreground shadow-sm hover:bg-secondary"
    >
      <Download className="h-3.5 w-3.5" />
      下载{size ? ` · ${formatBytes(size)}` : ""}
    </a>
  );
}

function appMessageIcon(icon: AppMessageSummary["icon"]) {
  switch (icon) {
    case "link":
      return <LinkIcon className="h-4 w-4 shrink-0" />;
    case "file":
      return <Paperclip className="h-4 w-4 shrink-0" />;
    case "mini_program":
      return <Smartphone className="h-4 w-4 shrink-0" />;
    case "chat_history":
      return <MessageCircle className="h-4 w-4 shrink-0" />;
    case "quote":
      return <FileText className="h-4 w-4 shrink-0" />;
    case "payment":
      return <ShieldCheck className="h-4 w-4 shrink-0" />;
    default:
      return <FileText className="h-4 w-4 shrink-0" />;
  }
}

function mediaIcon(kind: string) {
  switch (kind) {
    case "image":
      return <ImageIcon className="h-4 w-4" />;
    case "voice":
      return <Mic className="h-4 w-4" />;
    case "video":
      return <Video className="h-4 w-4" />;
    case "file":
      return <Paperclip className="h-4 w-4" />;
    default:
      return <FileText className="h-4 w-4" />;
  }
}
