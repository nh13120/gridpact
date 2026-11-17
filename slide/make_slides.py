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
        self.label = label

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

    def save(self, name, dy=0):
        """dy: move everything below the section label down by dy (layout units) to use the space the header and footer rows left."""
        if dy:
            top = 100 * S
            body = self.im.crop((0, top, W * S, (H - dy) * S))
            self.im.paste(PAPER, (0, top, W * S, H * S))
            self.im.paste(body, (0, top + dy * S))
        self.text(64, 64 + dy // 2, self.label, hn(15, MED), GREEN, ls=3)       # the label moves half as far, so it stays close to the title
        self.im.save(OUT / name)


def build(checks):
    OUT.mkdir(parents=True, exist_ok=True)

    # 1: the problem, in plain words: what is being traded, who is involved, why no person is in the loop
    s = Slide(1, "THE PROBLEM")
    s.text(60, 112, "Soon, AI agents will", hn(72, LIGHT)); s.text(60, 192, "trade electricity.", hn(72, LIGHT))
    s.text(60, 288, "What if one of them lies?", hn(48, LIGHT), GREEN)
    s.wrap(64, 372, "A battery owner promises power for 5 pm. A community plans around that promise. "
           "No person can check every deal, so AI agents will make them on their own, in seconds, with real money at stake.",
           hn(23, REG), INK, 980, 33)
    for i, (h, t) in enumerate([("Buyer", "a community that needs power"), ("Seller", "a battery owner who promises it"),
                                ("Auditor", "an AI that checks the promise")]):
        x = 64 + i * 380
        s.line(x, 506, x + 331, 506, INK, 2)
        s.text(x, 522, h, hn(32, MED)); s.text(x, 568, t, hn(22, REG), MID)
    s.save("slide1.png", 30)

    # 2: what we built, with the terms explained, and the architecture as a small diagram
    s = Slide(2, "WHAT WE BUILT")
    s.text(60, 112, "GridPact: a referee for AI energy deals.", hn(54, LIGHT))
    for i, (num, h, t) in enumerate([("01", "Deposit", "The seller puts money down behind its promise."),
                                     ("02", "Check", "An auditor compares the claim with the battery's real size."),
                                     ("03", "Settle", "If the promise fails, the deposit pays the buyer.")]):
        y = 206 + i * 84
        s.d.text((64 * S, y * S), num, font=ImageFont.truetype(DIN, 46 * S), fill=GREEN)
        s.text(150, y - 4, h, hn(30, MED)); s.wrap(150, y + 34, t, hn(20, REG), MID, 600, 28)
    s.d.rounded_rectangle([796 * S, 206 * S, 1216 * S, 442 * S], radius=6 * S, fill=BOX, outline=HAIR, width=2 * S)   # 16:9 slot for the video
    s.text(820, 314, "30 SECOND VIDEO", hn(15, MED), MID, ls=2.4)
    s.text(64, 472, "HOW IT FITS TOGETHER", hn(12, MED), MID, ls=2.4)
    bw, gap, y0, bh = 250, (1152 - 4 * 250) / 3, 498, 82
    for i, (h, sub, col) in enumerate([("AI agents", "buyers, sellers, auditors", INK), ("GridPact server", "takes deposits, runs checks", GREEN),
                                       ("Tamper-proof record", "every step logged and linked", INK), ("Payout", "ordinary software, no AI", INK)]):
        x = 64 + i * (bw + gap)
        s.d.rounded_rectangle([x * S, y0 * S, (x + bw) * S, (y0 + bh) * S], radius=5 * S, fill=PAPER, outline=col, width=int((3 if col == GREEN else 2) * S))
        s.text(x + 16, y0 + 12, h, hn(22, MED), col); s.text(x + 16, y0 + 48, sub, hn(16, REG), MID)
        if i < 3:
            x1, x2, yc = x + bw + 8, x + bw + gap - 8, y0 + bh / 2
            s.line(x1, yc, x2 - 6, yc, INK, 2)
            s.d.polygon([(x2 * S, yc * S), ((x2 - 11) * S, (yc - 6) * S), ((x2 - 11) * S, (yc + 6) * S)], fill=INK)
    s.wrap(64, 596, "Any AI agent can plug in through a standard connector (called MCP), using one written guide. "
           "We also connected it to Nanda Town, an open network of AI agents.", hn(17, REG), MID, 1152, 25)
    s.save("slide2.png", 30)

    # 3: the evidence, every number explained
    s = Slide(3, "THE EVIDENCE")
    s.text(60, 112, "Did it work? We tested it.", hn(60, LIGHT))
    s.wrap(64, 196, "275 simulated trading days on real ENGIE grid data, with Claude Haiku AI agents playing every role.", hn(21, REG), MID, 1100, 30)
    cols = [("50 / 50", "lying sellers caught before they could cheat"),
            ("0 / 160", "honest sellers wrongly accused"),
            ("90%", "of the energy buyers needed arrived, up from 65% before we fixed a gap"),
            (checks, "checks passed by brand-new AI agents using only our written guide")]
    for i, (big, cap) in enumerate(cols):
        x = 64 + i * 292
        s.d.text((x * S, 262 * S), big, font=ImageFont.truetype(DIN, 76 * S), fill=GREEN)
        s.wrap(x, 370, cap, hn(20, REG), INK, 262, 28)
    s.line(64, 500, 1216, 500)
    s.wrap(64, 518, "The tests also found three gaps in our own system. We fixed all three and ran them again.", hn(25, REG), INK, 1152, 34)
    s.wrap(64, 558, "Buyers could not see when their deal was cut. Nothing told them. Auditors needed a separate data file.", hn(19, REG), MID, 1152, 27)
    s.wrap(64, 592, "It also works inside Nanda Town: 36 of 36 test runs passed.", hn(19, REG), MID, 1152, 27)
    s.save("slide3.png", 30)

    # 4: worked, to improve, next
    s = Slide(4, "WHAT WE LEARNED")
    s.text(60, 112, "What worked, what to improve, what is next.", hn(46, LIGHT))
    cols = [("Worked", GREEN, ["Lying costs the liar money.", "Our tests found problems, and we fixed them.", "A brand-new AI agent used it from our guide alone."]),
            ("To improve", INK, ["A second liar can still slip through at large scale.", "Delivery is estimated, not read from real meters.", "We have tested only one kind of lie."]),
            ("Next", INK, ["A second round of checks.", "Live meter data.", "A pilot with one ENGIE community, with no real money moving."])]
    for i, (h, col, items) in enumerate(cols):
        x = 64 + i * 400
        s.line(x, 230, x + 336, 230, INK, 2)
        s.text(x, 246, h, hn(36, MED), col)
        y = 314
        for it in items:
            y = s.wrap(x, y, it, hn(23, REG), INK, 336, 31) + 24
    s.save("slide4.png", 50)


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
