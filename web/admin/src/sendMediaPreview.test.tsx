import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SelectedMediaPreview } from "@/sendMediaPreview";

describe("send media preview", () => {
  it("renders media file name and formatted size", () => {
    const html = renderToStaticMarkup(
      <SelectedMediaPreview file={{ name: "photo.png", type: "image/png", size: 2048 } as File} />
    );

    expect(html).toContain("photo.png");
    expect(html).toContain("2.0 KB");
  });

  it("classifies voice files by extension when mime type is missing", () => {
    const html = renderToStaticMarkup(
      <SelectedMediaPreview file={{ name: "voice.silk", type: "", size: 512 } as File} className="max-w-full" />
    );

    expect(html).toContain("voice.silk");
    expect(html).toContain("512 B");
    expect(html).toContain("max-w-full");
  });
});
