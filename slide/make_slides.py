"""Draw the four final-project slides (1280 x 720 layout, rendered at 2x) and write PNGs, a PDF and a PPTX.

    python slide/make_slides.py [--checks 17/17]     (needs pillow, python-pptx; macOS fonts Helvetica Neue and DIN Alternate)

The PPTX holds one picture per slide. The video box on slide 2 is empty on purpose: in Google Slides, insert the
YouTube video (Unlisted) over it and set Format options > Video playback > Play (automatically).
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Emu

OUT = Path(__file__).resolve().parent / "final"
S = 2                                                      # render scale
W, H = 1280, 720
PAPER, INK, MID, HAIR, GREEN, BOX = (244, 244, 241), (18, 18, 18), (112, 111, 108), (206, 206, 200), (0, 166, 90), (236, 236, 231)
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
DIN = "/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf"
MARGIN_R = 1216                                            # nothing may cross this line


def hn(size, idx=0):
    return ImageFont.truetype(HN, int(size * S), index=idx)


LIGHT, REG, MED = 7, 0, 10


class Slide:
    def __init__(self, n, label):
        self.im = Image.new("RGB", (W * S, H * S), PAPER)
        self.d = ImageDraw.Draw(self.im)
        self.text(64, 30, "GRIDPACT", hn(13, MED), INK, ls=2.4)
        self.text(1216, 30, f"{n} / 4", hn(12, MED), MID, ls=1.6, right=True)
        self.line(64, 56, 1216, 56)
        self.text(64, 83, label, hn(15, MED), GREEN, ls=3)
        self.line(64, 664, 1216, 664)
        self.text(64, 681, "NICOLAS HONG  ·  MAHEEN RASSELL", hn(12, MED), INK, ls=1.8)
        self.text(1216, 681, "PR  GITHUB.COM/PROJNANDA/NANDATOWN/PULL/345", hn(12, REG), MID, ls=1.4, right=True)

    def line(self, x1, y1, x2, y2, fill=HAIR, w=1):
        self.d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=fill, width=int(w * S))

    def width(self, s, font, ls=0):
        return font.getlength(s) / S + ls * max(len(s) - 1, 0)

    def text(self, x, y, s, font, fill=INK, ls=0, right=False):
        if right:
            x -= self.width(s, font, ls)
        if not ls:
            self.d.text((x * S, y * S), s, font=font, fill=fill)
            return
        for ch in s:
            self.d.text((x * S, y * S), ch, font=font, fill=fill)
            x += font.getlength(ch) / S + ls

    def wrap(self, x, y, s, font, fill, maxw, lead):
        """Word-wrap into maxw, never past the right margin; returns the y after the last line."""
        assert x + maxw <= MARGIN_R + 0.5, (s, x, maxw)
        line = ""
        for word in s.split():
            trial = (line + " " + word).strip()
            if self.width(trial, font) <= maxw:
                line = trial
            else:
                self.text(x, y, line, font, fill); y += lead; line = word
        if line:
            assert self.width(line, font) <= maxw + 0.5, (line, "single word wider than its column")
            self.text(x, y, line, font, fill); y += lead
        return y

    def save(self, name):
        self.im.save(OUT / name)


def build(checks):
    OUT.mkdir(parents=True, exist_ok=True)

    # 1: the problem, why it is agentic, who the users are
    s = Slide(1, "THE PROBLEM")
    s.text(60, 128, "AI agents will trade", hn(78, LIGHT)); s.text(60, 214, "grid power.", hn(78, LIGHT))
    s.text(60, 316, "Who checks their promises?", hn(52, LIGHT), GREEN)
    s.wrap(64, 400, "Agents deal on their own, in seconds, with money at stake. No person can audit every promise.",
           hn(24, REG), INK, 1100, 34)
    for i, (h, t) in enumerate([("Buyers", "need energy"), ("Sellers", "promise it"), ("Auditors", "check the promise")]):
        x = 64 + i * 380
        s.line(x, 508, x + 331, 508, INK, 2)
        s.text(x, 524, h, hn(32, MED)); s.text(x, 570, t, hn(24, REG), MID)
    s.save("slide1.png")

    # 2: what we built, the architecture in one line, the demo video
    s = Slide(2, "WHAT WE BUILT")
    s.text(60, 120, "A referee for agents.", hn(70, LIGHT))
    for i, (num, h, t) in enumerate([("01", "Deposit", "A seller locks money behind its promise."),
                                     ("02", "Check", "An auditor catches false claims."),
                                     ("03", "Settle", "Plain code pays the buyer. No AI.")]):
        y = 252 + i * 98
        s.d.text((64 * S, y * S), num, font=ImageFont.truetype(DIN, 52 * S), fill=GREEN)
        s.text(160, y - 2, h, hn(34, MED)); s.text(160, y + 40, t, hn(23, REG), MID)
    s.line(64, 556, 640, 556)
    s.wrap(64, 570, "An MCP server, a hash-chained ledger, Haiku agents, and a bridge into Nanda Town.", hn(19, REG), INK, 576, 27)
    s.d.rounded_rectangle([700 * S, 262 * S, 1216 * S, 552 * S], radius=6 * S, fill=BOX, outline=HAIR, width=2 * S)
    s.text(724, 395, "30 SECOND VIDEO", hn(15, MED), MID, ls=2.4)
    s.wrap(700, 570, "Any agent connects over MCP from one written guide.", hn(19, REG), MID, 516, 27)
    s.save("slide2.png")

    # 3: the evidence, each number tied to its homework
    s = Slide(3, "THE EVIDENCE")
    s.text(60, 120, "Tested. Then repaired.", hn(70, LIGHT))
    cols = [("HW7", "50/50", "lying sellers caught"), ("HW7", "90%", "of the need delivered, up from 65%"),
            ("SCALE TEST", "1,520", "agents on one server, a full day in 6 seconds"), ("HW9", checks, "checks passed by a fresh agent, from our guide only")]
    for i, (hw, big, cap) in enumerate(cols):
        x = 64 + i * 292
        s.text(x, 246, hw, hn(14, MED), MID, ls=2.4)
        s.d.text((x * S, 272 * S), big, font=ImageFont.truetype(DIN, 84 * S), fill=GREEN)
        s.wrap(x, 388, cap, hn(22, REG), INK, 262, 30)
    s.line(64, 500, 1216, 500)
    s.wrap(64, 520, "Our tests found three real gaps. We fixed each one and reran it.", hn(28, REG), INK, 1100, 38)
    s.wrap(64, 576, "HW8: 36 of 36 Nanda Town profile runs passed with Haiku agents.", hn(20, REG), MID, 1100, 28)
    s.save("slide3.png")

    # 4: worked, failed, next
    s = Slide(4, "WORKED  ·  FAILED  ·  NEXT")
    s.text(60, 120, "What we learned.", hn(70, LIGHT))
    cols = [("Worked", GREEN, ["Lying loses money.", "Pre-registered tests, then reruns that passed.", "A fresh agent used it from the guide."]),
            ("Failed", INK, ["A second liar can slip through at scale.", "Delivery is estimated, not metered.", "Only one kind of lie tested."]),
            ("Next", INK, ["A second audit pass.", "Live meter data.", "A pilot with one ENGIE community."])]
    for i, (h, col, items) in enumerate(cols):
        x = 64 + i * 400
        s.line(x, 246, x + 336, 246, INK, 2)
        s.text(x, 262, h, hn(36, MED), col)
        y = 330
        for it in items:
            y = s.wrap(x, y, it, hn(23, REG), INK, 336, 31) + 22
    s.save("slide4.png")


def export():
    files = [OUT / f"slide{i}.png" for i in range(1, 5)]
    ims = [Image.open(f).convert("RGB") for f in files]
    ims[0].save(OUT / "GridPact_final_slides.pdf", save_all=True, append_images=ims[1:], resolution=2 * S * 36)
    prs = Presentation(); prs.slide_width, prs.slide_height = Emu(12191695), Emu(6858000)
    for f in files:
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        sl.shapes.add_picture(str(f), 0, 0, prs.slide_width, prs.slide_height)
    prs.save(OUT / "GridPact_final_slides.pptx")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--checks", default="16/16"); a = ap.parse_args()
    build(a.checks); export(); print("wrote", OUT)
