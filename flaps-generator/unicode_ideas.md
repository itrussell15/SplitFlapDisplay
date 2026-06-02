  ## Arrows & Direction

  ```
    ← → ↑ ↓ ↔ ↕ ↖ ↗ ↘ ↙
  ```

  Unicode:

  ```
    \u2190 \u2192 \u2191 \u2193 \u2194 \u2195 \u2196 \u2197 \u2198 \u2199
  ```

  Usage: Navigation, trends (up/down), UI indicators

  ────────────────────────────────────────────────────────────────────────────────

  ## Weather Symbols

  ```
    ☀ ☁ ☂ ☔ ⚡ ❄ ☃ ☄
  ```

  Unicode:

  ```
    \u2600 \u2601 \u2602 \u2614 \u26A1 \u2744 \u2603 \u2604
  ```

  Usage: Weather display, forecasts

  ────────────────────────────────────────────────────────────────────────────────

  ## Currency Symbols

  ```
    $ € £ ¥ ¢ ₹ ₿
  ```

  Unicode:

  ```
    $ \u20AC \u00A3 \u00A5 \u00A2 \u20B9 \u20BF
  ```

  Usage: Stock/crypto prices, financial data

  ────────────────────────────────────────────────────────────────────────────────

  ## Card Suits & Games

  ```
    ♠ ♡ ♢ ♣ ♤ ♥ ♦ ♧
  ```

  Unicode:

  ```
    \u2660 \u2661 \u2662 \u2663 \u2664 \u2665 \u2666 \u2667
  ```

  Usage: Games, status indicators

  ────────────────────────────────────────────────────────────────────────────────

  ## Check Marks & Crosses

  ```
    ✓ ✗ ✘ ✔ ✖ ✚ ✛
  ```

  Unicode:

  ```
    \u2713 \u2717 \u2718 \u2714 \u2716 \u271A \u271B
  ```

  Usage: Todo lists, status, completion

  ────────────────────────────────────────────────────────────────────────────────

  ## Stars & Ratings

  ```
    ★ ☆ ✦ ✧ ✩ ✪ ✫ ✬
  ```

  Unicode:

  ```
    \u2605 \u2606 \u2726 \u2727 \u2729 \u272A \u272B \u272C
  ```

  Usage: Ratings, favorites, highlights

  ────────────────────────────────────────────────────────────────────────────────

  ## Faces & Emoticons

  ```
    ☺ ☹ ☻ シ
  ```

  Unicode:

  ```
    \u263A \u2639 \u263B \u30B7
  ```

  Usage: Mood, status, fun indicators

  ────────────────────────────────────────────────────────────────────────────────

  ## Math Symbols

  ```
    ± × ÷ = ≠ ≈ ∞ √
  ```

  Unicode:

  ```
    \u00B1 \u00D7 \u00F7 = \u2260 \u2248 \u221E \u221A
  ```

  Usage: Calculations, data display

  ────────────────────────────────────────────────────────────────────────────────

  ## Geometric Shapes

  ```
    ■ □ ▲ △ ▼ ▽ ◆ ◇ ● ○
  ```

  Unicode:

  ```
    \u25A0 \u25A1 \u25B2 \u25B3 \u25BC \u25BD \u25C6 \u25C7 \u25CF \u25CB
  ```

  Usage: Progress bars, indicators, simple graphics

  ────────────────────────────────────────────────────────────────────────────────

  ## Warning & Symbols

  ```
    ⚠ ☢ ☣ ☤ ⚕ ⚖ ⚗
  ```

  Unicode:

  ```
    \u26A0 \u2622 \u2623 \u2624 \u2695 \u2696 \u2697
  ```

  Usage: Alerts, status, categories

  ────────────────────────────────────────────────────────────────────────────────

  ## Music & Audio

  ```
    ♪ ♫ ♬ ♩ ♭ ♮ ♯
  ```

  Unicode:

  ```
    \u266A \u266B \u266C \u2669 \u266D \u266E \u266F
  ```

  Usage: Music info, audio status

  ────────────────────────────────────────────────────────────────────────────────

  ## Time & Clock

  ```
    ⌚ ⌛ ⏰ ⏱ ⏲
  ```

  Unicode:

  ```
    \u231A \u231B \u23F0 \u23F1 \u23F2
  ```

  Usage: Time, timers, schedules

  ────────────────────────────────────────────────────────────────────────────────

  ## Communication

  ```
    ✉ ✆ ☎ ☏
  ```

  Unicode:

  ```
    \u2709 \u2706 \u260E \u260F
  ```

  Usage: Messages, calls, notifications

  ────────────────────────────────────────────────────────────────────────────────

  ## Complete Example Character Set

  Here's a full 64-character set with useful symbols:

  ```scad
    // 64-character set with symbols
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    // Add 28 more symbols (total 64):
    // " ?!@#$&[]-+=:%'\"\u20AC\u2191\u2193\u00B0\u263A.♥☀☁⚡★☆✓✗♠♥♦♣←→";
  ```

  Full string:

  ```scad
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789?!@#$&[]-+=:%'\"\u20AC\u2191\u2193\u00B0\u263A.♥☀☁⚡★☆✓✗♠♥♦♣←→    ";
  ```

  Breakdown:
  - 0-25: A-Z (26 chars)
  - 26-35: 0-9 (10 chars)
  - 36-63: 28 symbols/spaces

  ────────────────────────────────────────────────────────────────────────────────

  ## Alternative: Minimalist Symbol Set

  If you want more symbols and fewer letters:

  ```scad
    // 26 letters + 10 numbers + 28 symbols = 64
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    chars = str(chars, "?!.,:-+=/*%\$#@&\u2190\u2191\u2192\u2193\u2600\u2601\u26A1\u2605\u2606\u2713\u2717\u2660\u2665\u2666\u2663    ");
  ```

  ────────────────────────────────────────────────────────────────────────────────

  ## Testing Unicode Characters

  Before committing to a full print:

  1. Test in OpenSCAD:
    ```scad
      // Temporarily change chars to test specific symbols
      chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789?!@#\u2190\u2191\u2192\u2193\u2600\u2601\u26A1\u2605\u2606\u2713\u2717\u2660\u2665\u2666\u2663    ";
    ```
  2. Preview (F5) to see if characters render
  3. Check console for warnings about missing glyphs
  4. Render one test flap (F6) to verify appearance

  ## Font Support Notes

  Consolas (primary font) supports:
  - ✅ Arrows, geometric shapes, box drawing
  - ✅ Most math symbols
  - ✅ Card suits, stars, checks
  - ⚠️ Some emoji may not render (use Arial for those)

  Arial (secondary font) supports:
  - ✅ Weather symbols, emoji, faces
  - ✅ Currency symbols
  - ✅ Wider Unicode coverage

  If a character shows as a box or question mark, it's not supported by the font. Try:
  1. Switching that character to Arial (update charFont array)
  2. Choosing a different Unicode symbol
  3. Using a font with better Unicode support

  ## Updating charFont for Mixed Fonts

  If you want specific symbols in Arial:

  ```scad
    // 0 = Consolas, 1 = Arial
    charFont = [
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  // A-P: Consolas
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  // Q-Z: Consolas
        0,0,0,0,0,0,0,0,0,0,              // 0-9: Consolas
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  // Symbols: Consolas
        0,0,1,1,1,1,1,1,1,1,1,1,          // Weather/emoji: Arial
        0,0,0,0                            // Spaces: Consolas
    ];
  ```

  Indices 50-60 would use Arial for better symbol support.

  ## Recommended 64-Character Set

  Here's a practical set for general use:

  ```
    ABCDEFGHIJKLMNOPQRSTUVWXYZ
    0123456789
    ?!@#$%&*+-=
    .:,;/\|
    ←↑→↓
    ☀☁⚡
    ★☆✓✗
    ♠♥♦♣
    (4 spaces)
  ```

  As a string:

  ```scad
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789?!@#$%&*+-=.:\,;/\\|\u2190\u2191\u2192\u2193\u2600\u2601\u26A1\u2605\u2606\u2713\u2717\u2660\u2665\u2666\u2663    ";
