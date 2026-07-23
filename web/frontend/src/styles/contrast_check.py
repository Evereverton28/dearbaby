"""
Verify the palette without eyes (architecture brief §4).

Targets: 4.5:1 for body text, 3:1 for large/bold text and UI elements.
Run:  python design/contrast_check.py
"""


def srgb_to_linear(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * srgb_to_linear(r)
            + 0.7152 * srgb_to_linear(g)
            + 0.0722 * srgb_to_linear(b))


def ratio(fg, bg):
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


LIGHT = {
    "--bg":            "#F4EDE3",  # oat
    "--surface":       "#FBF7F0",  # linen
    "--border":        "#EADFCF",  # sand
    "--text":          "#40352E",  # espresso
    "--text-muted":    "#6E6157",  # taupe (darkened from #8C7C6E — see report)
    "--accent-text":   "#7A5A60",  # mauve, DARKENED for text contrast
    "--accent-solid":  "#8E6C72",  # mauve as BUTTON BACKGROUND
    "--accent-on":     "#FFFFFF",  # text sitting on accent-solid
    "--secondary-text": "#5F6B51",  # sage for text
    "--secondary-solid": "#6E7A5E",  # sage as background
    "--border-control": "#9C8768",  # input/control outlines (needs 3:1)
}

DARK = {
    "--bg":            "#1C1913",
    "--surface":       "#262119",
    "--border":        "#3A332A",
    "--text":          "#ECE5D5",
    "--text-muted":    "#B3A797",
    "--accent-text":   "#D9AEB3",  # LIGHTER: mauve as text on a dark bg
    "--accent-solid":  "#8E6C72",  # STAYS DARK: white text must remain readable
    "--accent-on":     "#FFFFFF",
    "--secondary-text": "#B6C3A4",
    "--secondary-solid": "#5C6850",
    "--border-control": "#7A6F5E",
}

# (label, foreground token, background token, target ratio)
PAIRS = [
    ("body text on bg",            "--text",           "--bg",           4.5),
    ("body text on surface",       "--text",           "--surface",      4.5),
    ("muted text on bg",           "--text-muted",     "--bg",           4.5),
    ("muted text on surface",      "--text-muted",     "--surface",      4.5),
    ("accent link on bg",          "--accent-text",    "--bg",           4.5),
    ("accent link on surface",     "--accent-text",    "--surface",      4.5),
    ("secondary text on surface",  "--secondary-text", "--surface",      4.5),
    ("text on accent button",      "--accent-on",      "--accent-solid", 4.5),
    ("text on secondary button",   "--accent-on",      "--secondary-solid", 4.5),
    ("control border on surface",  "--border-control", "--surface",      3.0),
    # NOTE: --border is a decorative hairline (card edges). WCAG 1.4.11 applies
    # to UI components and meaningful graphics, not decorative separators, so it
    # is intentionally not tested. Anything a user must SEE to operate a control
    # uses --border-control instead.
]


def audit(name, palette):
    print(f"\n{name}")
    print("-" * 62)
    failures = []
    for label, fg, bg, target in PAIRS:
        r = ratio(palette[fg], palette[bg])
        ok = r >= target
        flag = "PASS" if ok else "FAIL"
        print(f"  {flag}  {label:<28} {r:5.2f}:1  (need {target}:1)")
        if not ok:
            failures.append((label, r, target))
    return failures


if __name__ == "__main__":
    print("DearBaby palette — WCAG contrast audit")
    f_light = audit("LIGHT THEME", LIGHT)
    f_dark = audit("DARK THEME", DARK)

    print("\n" + "=" * 62)
    total = len(f_light) + len(f_dark)
    if total == 0:
        print("All pairings meet their target.")
    else:
        print(f"{total} pairing(s) below target:")
        for label, r, t in f_light + f_dark:
            print(f"  - {label}: {r:.2f}:1 (need {t}:1)")
