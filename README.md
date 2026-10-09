# McKitrick

![McKitrick specimen](documentation/specimen.png)

McKitrick is a condensed display typeface drawn from a single sheet of hand-cut marker sketches. Every letter is built from separate, flat-ended strokes that stop short of one another where they meet, the way the originals were drawn. The dots on i and j are tapered, wider at the top, and the same dot carries through the punctuation and accents. The name comes from an old Celtic surname.

It works best at display sizes: headings, posters, signs, labels and short lines of text.

## Features

- **Regular** weight, 220 glyphs
- Full **ASCII**, **Latin-1** and **Windows-1252** coverage, which covers English, French, German, Spanish, Italian, Portuguese, Dutch and the Scandinavian languages
- Optical spacing and around 6,500 kerning pairs
- Stylistic set 1 (`ss01`, also `salt`): an alternative **f** with a long descender

![McKitrick character set](documentation/charset.png)

## Download and install

The fonts are in [`fonts/`](fonts):

| Folder | Format | Use |
|---|---|---|
| `fonts/otf` | OpenType (CFF) | Desktop apps on macOS and Windows |
| `fonts/ttf` | TrueType | Desktop apps, Android, older software |
| `fonts/webfonts` | WOFF2 | Websites |

- **macOS:** double-click `McKitrick-Regular.otf`, then choose **Install Font**.
- **Windows:** right-click the file and choose **Install**.
- **Web:**

```css
@font-face {
  font-family: "McKitrick";
  src: url("McKitrick-Regular.woff2") format("woff2");
}
.descending-f { font-feature-settings: "ss01" 1; }
```

## Where it came from

McKitrick began as ten pencil letters on apricot paper: **i t r i j c k l g m f**. The rest of the alphabet, the capitals, figures, punctuation and accented letters were drawn to match. The descending f is the alternative sketched in the margin of that first sheet.

![The original sketch](documentation/original-sketch.jpg)

## Building from source

The outlines, spacing and kerning are generated in Python from stroke definitions in [`sources/glyphs.py`](sources/glyphs.py). An editable UFO source, [`sources/McKitrick-Regular.ufo`](sources/McKitrick-Regular.ufo), is written alongside the fonts.

```sh
pip install -r sources/requirements.txt
./build.sh
```

| File | Purpose |
|---|---|
| `sources/glyphs.py` | Every glyph, drawn as centre-line strokes with flat ends |
| `sources/spacing.py` | Optical sidebearings and kerning measured from the outlines |
| `sources/build.py` | Builds the TTF, OTF, WOFF2 and UFO |
| `sources/sketch/` | The original hand-drawn sketch |

## Licence

Copyright 2026 The McKitrick Project Authors.

This font software is licensed under the [SIL Open Font License, Version 1.1](OFL.txt). You can use it freely in personal and commercial work, and modify and redistribute it, as long as the fonts are not sold on their own and derivatives keep the same licence. The licence is available with a FAQ at <https://openfontlicense.org>.

## Author

Designed by [Ian Lawton](https://github.com/ianlawton). See [FONTLOG.txt](FONTLOG.txt) for the change history.
