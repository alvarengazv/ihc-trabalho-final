"""Coordinates shared by the browser, the proxy and the replay projector."""
from textwrap import wrap

WIDTH, HEIGHT, FOOTER = 360, 800, 64
# Corresponding values are used by the browser for explicit line boxes. Width
# per character is a proportional approximation, documented in the specification.
FONT = {"brand": 25, "heading": 29, "section": 23, "name": 19, "price": 18,
        "detailprice": 22, "total": 22, "tag": 16}
CENTERED = {"button", "primary", "selected", "tab", "quiet", "inactive"}


def text_lines(element):
    x, y, w, h = element["box"]
    style = element["style"]
    size = FONT.get(style, 16)
    leading = size * 1.18
    inset = 12 if style in ("name", "description", "price", "tag", "footer") else 4
    max_width = w - 2 * inset
    estimated_width = size * 0.52
    chunks = wrap(element["text"], max(1, int(max_width / estimated_width)),
                  break_long_words=False, break_on_hyphens=False) or [""]
    top = y + max(0, (h - len(chunks)*leading)/2)
    lines = []
    for chunk in chunks:
        width = min(max_width, max(1, len(chunk) * estimated_width))
        left = x + (w-width)/2 if style in CENTERED else x+inset
        lines.append({"text": chunk, "box": [left, top, width, leading]})
        top += leading
    return lines


def projected_layout(app, y=0, z=1):
    """Place the full scene and clip its visible sign areas behind the B footer.

    y is the world-space top of the magnified aperture; native document scroll
    follows once the aperture passes the center of the base mobile display.
    """
    base = app.elements()
    has_footer = any(e.get("fixed") for e in base)
    footer_height = HEIGHT-min(e["box"][1] for e in base if e.get("fixed")) if has_footer else 0
    extra = footer_height+16 if has_footer else 8
    height = max(HEIGHT, max(e["box"][1]+e["box"][3] for e in base if not e.get("fixed"))+extra)
    scroll = min(max(0, y-(HEIGHT-HEIGHT/z)/2), height-HEIGHT)
    elements = app.elements(scroll) if has_footer else base
    for e in elements:
        x0, y0, w, h = e["box"]
        # Keep the element's true hit rectangle and unoccluded subrectangle.
        # G can ignore visible_box for its declared full-page condition.
        if not e.get("fixed"):
            top = max(scroll, y0)
            bottom = min(y0+h, scroll+HEIGHT-footer_height)
            e["visible_box"] = [x0, top, w, max(0, bottom-top)]
        elif e["id"] == "summary":
            # The adjacent review control occupies the other half of the bar.
            e["visible_box"] = [0, y0, 208, h]
        e["text_lines"] = text_lines(e)
        if len(e["text_lines"]) == 1:
            e["text_box"] = e["text_lines"][0]["box"]
    return elements, height, scroll

