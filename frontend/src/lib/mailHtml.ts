import DOMPurify from "dompurify"

/** Parse stored full HTML, drop duplicate meta when present, sanitize for inline display. */
export function prepareInlineMailHtml(fullDocument: string): string {
  if (!fullDocument.trim()) return ""
  const doc = new DOMParser().parseFromString(fullDocument, "text/html")
  const mailBody = doc.querySelector(".mail-body")
  const root = mailBody ?? doc.body
  root.querySelector(".meta")?.remove()
  const raw = root.innerHTML
  return DOMPurify.sanitize(raw, {
    USE_PROFILES: { html: true },
    ADD_ATTR: [
      "style",
      "class",
      "width",
      "height",
      "align",
      "valign",
      "bgcolor",
      "border",
      "cellpadding",
      "cellspacing",
      "colspan",
      "rowspan",
      "nowrap",
      "id",
      "dir",
      "lang",
    ],
  })
}
