import { ImageIcon, Mic, Paperclip, Video } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatBytes, mediaActionKind } from "@/messageProtocol";

export function SelectedMediaPreview({ file, className }: { file: File; className?: string }) {
  return (
    <div className={cn("flex min-w-0 items-center gap-2 text-xs text-muted-foreground", className)}>
      {mediaKindIcon(mediaActionKind(file))}
      <span className="truncate">{file.name}</span>
      <span className="shrink-0">{formatBytes(file.size)}</span>
    </div>
  );
}

function mediaKindIcon(kind: ReturnType<typeof mediaActionKind>) {
  switch (kind) {
    case "video":
      return <Video className="h-4 w-4 shrink-0" />;
    case "voice":
      return <Mic className="h-4 w-4 shrink-0" />;
    case "image":
      return <ImageIcon className="h-4 w-4 shrink-0" />;
    default:
      return <Paperclip className="h-4 w-4 shrink-0" />;
  }
}
