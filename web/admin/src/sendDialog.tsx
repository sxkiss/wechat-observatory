import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
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
import { Textarea } from "@/components/ui/textarea";
import { SelectedMediaPreview } from "@/sendMediaPreview";

export type SendDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  targetTitle: string;
  draft: string;
  onDraftChange: (value: string) => void;
  selectedMedia: File | null;
  onSelectedMediaChange: (file: File | null) => void;
  emojiMd5: string;
  onEmojiMd5Change: (value: string) => void;
  emojiSourceId: string;
  onEmojiSourceIdChange: (value: string) => void;
  sending: boolean;
  canSubmit: boolean;
  onSubmit: () => void | Promise<void>;
};

export function SendDialog({
  open,
  onOpenChange,
  targetTitle,
  draft,
  onDraftChange,
  selectedMedia,
  onSelectedMediaChange,
  emojiMd5,
  onEmojiMd5Change,
  emojiSourceId,
  onEmojiSourceIdChange,
  sending,
  canSubmit,
  onSubmit
}: SendDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>发送微信消息</DialogTitle>
          <DialogDescription>{targetTitle}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <div className="grid gap-2">
            <Label htmlFor="send-target">发送对象</Label>
            <Input id="send-target" value={targetTitle} readOnly />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="send-text">消息内容</Label>
            <Textarea
              id="send-text"
              value={draft}
              onChange={(event) => onDraftChange(event.target.value)}
              placeholder="输入要发送到微信的文本"
              autoFocus
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="send-media">附件</Label>
            <Input
              id="send-media"
              type="file"
              onChange={(event) => onSelectedMediaChange(event.target.files?.[0] ?? null)}
            />
            {selectedMedia ? <SelectedMediaPreview file={selectedMedia} /> : null}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="send-emoji-md5">表情 MD5</Label>
              <Input
                id="send-emoji-md5"
                value={emojiMd5}
                onChange={(event) => onEmojiMd5Change(event.target.value)}
                placeholder="md5"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="send-emoji-source">源消息 ID</Label>
              <Input
                id="send-emoji-source"
                value={emojiSourceId}
                onChange={(event) => onEmojiSourceIdChange(event.target.value)}
                inputMode="numeric"
                placeholder="chat_record_id"
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button type="button" onClick={() => void onSubmit()} disabled={sending || !canSubmit}>
            <Send className="h-4 w-4" />
            {sending ? "发送中" : "加入队列"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
