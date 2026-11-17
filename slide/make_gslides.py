"""Build the final slides as a .pptx with real, editable text (for upload to Google Slides, which converts it).

    python slide/make_gslides.py [--checks 17/17]      (needs python-pptx)

Same four slides and wording as slide/make_slides.py (which draws pictures); this one keeps text, boxes and arrows
as shapes so the deck can be edited. Fonts are Google fonts (Arial, Roboto Condensed). Layout units are the 1280 x 720 grid
of make_slides.py, converted to inches (96 per inch). The grey box on slide 2 is where the YouTube video goes.
"""
import argparse
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

OUT = Path(__file__).resolve().parent / "final" / "GridPact_final_slides_editable.pptx"
PAPER, INK, MID, HAIR, GREEN, BOX = "F4F4F1", "121212", "706F6C", "CECEC8", "00A65A", "ECECE7"
BODY, NUM = "Arial", "Roboto Condensed"
PX = 1 / 96                                                  # layout px -> inches


def rgb(h):
    return RGBColor.from_string(h)


def pt(px):                                                  # layout px -> font points
    return Pt(round(px * 0.75, 1))


def inch(v):
    return Inches(v * PX)


def text(slide, x, y, w, h, paras, size, color=INK, bold=False, font=BODY, space_after=0, spc=None, line=None):
    """paras: a string or a list of strings (one paragraph each). Zero insets, wrapping on."""
    tb = slide.shapes.add_textbox(inch(x), inch(y), inch(w), inch(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, s in enumerate([paras] if isinstance(paras, str) else paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT; p.space_after = Pt(space_after)
        if line:
            p.line_spacing = line
        r = p.add_run(); r.text = s
        r.font.size = pt(size); r.font.bold = bold; r.font.name = font; r.font.color.rgb = rgb(color)
        if spc:
            r._r.get_or_add_rPr().set("spc", str(spc))
    return tb


def rule(slide, x, y, w, color=INK, thick=2):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, inch(x), inch(y), inch(w), Emu(int(thick * PX * 914400)))
    sh.fill.solid(); sh.fill.fore_color.rgb = rgb(color); sh.line.fill.background(); sh.shadow.inherit = False
    return sh


def box(slide, x, y, w, h, fill=None, outline=None, thick=2, radius=True):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, inch(x), inch(y), inch(w), inch(h))
    if radius:
        sh.adjustments[0] = 0.06
    if fill:
        sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
    else:
        sh.fill.background()
    if outline:
        sh.line.color.rgb = rgb(outline); sh.line.width = Pt(thick)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def arrow(slide, x, y, w=34, h=16):
    sh = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, inch(x), inch(y - h / 2), inch(w), inch(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = rgb(INK); sh.line.fill.background(); sh.shadow.inherit = False


def new_slide(prs, label, ly):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid(); s.background.fill.fore_color.rgb = rgb(PAPER)
    text(s, 64, ly, 600, 20, label, 15, GREEN, True, spc=300)
    return s


def build(checks):
    prs = Presentation(); prs.slide_width, prs.slide_height = Emu(12191695), Emu(6858000)

    # 1: the problem
    s = new_slide(prs, "THE PROBLEM", 79)
    text(s, 60, 138, 1100, 190, ["Soon, AI agents will", "trade electricity."], 72, INK)
    text(s, 60, 318, 1100, 70, "What if one of them lies?", 48, GREEN)
    text(s, 64, 402, 1060, 110, "A battery owner promises power for 5 pm. A community plans around that promise. "
         "No person can check every deal, so AI agents will make them on their own, in seconds, with real money at stake.", 23, INK)
    for i, (h, t) in enumerate([("Buyer", "a community that needs power"), ("Seller", "a battery owner who promises it"),
                                ("Auditor", "an AI that checks the promise")]):
        x = 64 + i * 380
        rule(s, x, 536, 331)
        text(s, x, 552, 340, 44, h, 32, INK, True)
        text(s, x, 598, 340, 34, t, 22, MID)

    # 2: what we built (the grey box is the video slot)
    s = new_slide(prs, "WHAT WE BUILT", 79)
    text(s, 60, 142, 1150, 80, "GridPact: a referee for AI energy deals.", 54, INK)
    for i, (num, h, t) in enumerate([("01", "Deposit", "The seller puts money down behind its promise."),
                                     ("02", "Check", "An auditor compares the claim with the battery's real size."),
                                     ("03", "Settle", "If the promise fails, the deposit pays the buyer.")]):
        y = 236 + i * 84
        text(s, 64, y - 2, 80, 60, num, 46, GREEN, True, font=NUM)
        text(s, 150, y - 4, 600, 40, h, 30, INK, True)
        text(s, 150, y + 34, 620, 30, t, 20, MID)
    v = box(s, 796, 236, 420, 236, fill=BOX, outline=HAIR)
    v.name = "Video slot: insert the YouTube video here"
    text(s, 820, 344, 380, 24, "30 SECOND VIDEO", 15, MID, True, spc=240)
    text(s, 64, 502, 400, 18, "HOW IT FITS TOGETHER", 12, MID, True, spc=240)
    bw, gap, y0, bh = 250, (1152 - 4 * 250) / 3, 528, 82
    for i, (h, sub, col) in enumerate([("AI agents", "buyers, sellers, auditors", INK), ("GridPact server", "takes deposits, runs checks", GREEN),
                                       ("Tamper-proof record", "every step logged and linked", INK), ("Payout", "ordinary software, no AI", INK)]):
        x = 64 + i * (bw + gap)
        box(s, x, y0, bw, bh, fill=PAPER, outline=col, thick=3 if col == GREEN else 2)
        text(s, x + 16, y0 + 12, bw - 28, 30, h, 22, col, True)
        text(s, x + 16, y0 + 48, bw - 28, 26, sub, 16, MID)
        if i < 3:
            arrow(s, x + bw + 8, y0 + bh / 2, gap - 16)
    text(s, 64, 626, 1152, 56, "Any AI agent can plug in through a standard connector (called MCP), using one written guide. "
         "We also connected it to Nanda Town, an open network of AI agents.", 17, MID)

    # 3: the evidence
    s = new_slide(prs, "THE EVIDENCE", 79)
    text(s, 60, 142, 1100, 80, "Did it work? We tested it.", 60, INK)
    text(s, 64, 226, 1150, 36, "275 simulated trading days on real ENGIE grid data, with Claude Haiku AI agents playing every role.", 21, MID)
    for i, (big, cap) in enumerate([("50 / 50", "lying sellers caught before they could cheat"), ("0 / 160", "honest sellers wrongly accused"),
                                    ("90%", "of the energy buyers needed arrived, up from 65% before we fixed a gap"),
                                    (checks, "checks passed by brand-new AI agents using only our written guide")]):
        x = 64 + i * 292
        text(s, x, 286, 280, 90, big, 76, GREEN, True, font=NUM)
        text(s, x, 400, 262, 110, cap, 20, INK)
    rule(s, 64, 530, 1152, HAIR, 1)
    text(s, 64, 548, 1152, 40, "The tests also found three gaps in our own system. We fixed all three and ran them again.", 25, INK)
    text(s, 64, 590, 1152, 30, "Buyers could not see when their deal was cut. Nothing told them. Auditors needed a separate data file.", 19, MID)
    text(s, 64, 624, 1152, 30, "It also works inside Nanda Town: 36 of 36 test runs passed.", 19, MID)

    # 4: worked, to improve, next
    s = new_slide(prs, "WHAT WE LEARNED", 89)
    text(s, 60, 162, 1150, 70, "What worked, what to improve, what is next.", 46, INK)
    cols = [("Worked", GREEN, ["Lying costs the liar money.", "Our tests found problems, and we fixed them.", "A brand-new AI agent used it from our guide alone."]),
            ("To improve", INK, ["A second liar can still slip through at large scale.", "Delivery is estimated, not read from real meters.", "We have tested only one kind of lie."]),
            ("Next", INK, ["A second round of checks.", "Live meter data.", "A pilot with one ENGIE community, with no real money moving."])]
    for i, (h, col, items) in enumerate(cols):
        x = 64 + i * 400
        rule(s, x, 280, 336)
        text(s, x, 296, 340, 50, h, 36, col, True)
        text(s, x, 364, 336, 300, items, 23, INK, space_after=14)

    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--checks", default="17/17"); a = ap.parse_args()
    print("wrote", build(a.checks))
