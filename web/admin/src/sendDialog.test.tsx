import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SendDialog } from "@/sendDialog";

const baseProps = {
  open: true,
  onOpenChange: () => undefined,
  targetTitle: "两碗冰",
  draft: "你好",
  onDraftChange: () => undefined,
  selectedMedia: null,
  onSelectedMediaChange: () => undefined,
  emojiMd5: "",
  onEmojiMd5Change: () => undefined,
  emojiSourceId: "",
  onEmojiSourceIdChange: () => undefined,
  sending: false,
  canSubmit: true,
  onSubmit: () => undefined
};

describe("send dialog", () => {
  it("does not render when closed", () => {
    expect(renderToStaticMarkup(<SendDialog {...baseProps} open={false} />)).toBe("");
  });

  it("renders send fields for the selected target", () => {
    const html = renderToStaticMarkup(<SendDialog {...baseProps} />);

    expect(html).toContain("发送微信消息");
    expect(html).toContain("两碗冰");
    expect(html).toContain("消息内容");
    expect(html).toContain("附件");
    expect(html).toContain("表情 MD5");
    expect(html).toContain("源消息 ID");
    expect(html).toContain("加入队列");
  });

  it("renders selected media preview and sending state", () => {
    const html = renderToStaticMarkup(
      <SendDialog
        {...baseProps}
        selectedMedia={{ name: "clip.mp4", type: "video/mp4", size: 2048 } as File}
        sending
      />
    );

    expect(html).toContain("clip.mp4");
    expect(html).toContain("2.0 KB");
    expect(html).toContain("发送中");
    expect(html).toContain("disabled");
  });

  it("disables submit when canSubmit is false without hiding fields", () => {
    const html = renderToStaticMarkup(<SendDialog {...baseProps} canSubmit={false} />);

    expect(html).toContain("消息内容");
    expect(html).toContain("附件");
    expect(html).toContain("表情 MD5");
    expect(html).toContain("源消息 ID");
    expect(html).toContain("加入队列");
    expect(html).toContain("disabled");
  });
});
