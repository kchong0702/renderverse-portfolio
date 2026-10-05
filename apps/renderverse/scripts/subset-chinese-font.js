#!/usr/bin/env node
/* eslint-disable no-undef */

/**
 * Subset a Chinese TTF font to only the characters used in the zh.json translations,
 * then convert to Three.js FontLoader JSON format for use with TextGeometry.
 *
 * Usage:
 *   node scripts/subset-chinese-font.js <path-to-ttf-font> [output-font-name]
 *
 * Examples:
 *   node scripts/subset-chinese-font.js ./fonts/NotoSansSC-Regular.ttf
 *   node scripts/subset-chinese-font.js ./fonts/NotoSansSC-Regular.ttf notoSansSC
 *
 * Output: <output-font-name>.json  ->  public/fonts/
 *
 * Three.js Font format:
 *   - glyphs keyed by actual character (not unicode number)
 *   - glyph.o is a space-separated string of commands
 *   - Commands: m(x,y) l(x,y) q(cx,cy,x,y) b(cx,cy,cx1,cy1,x,y)
 */

import opentype from "opentype.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");

const LOCALE_FILE = path.join(rootDir, "src", "i18n", "locales", "zh.json");
const OUTPUT_DIR = path.join(rootDir, "public", "fonts");

/**
 * Extract all unique CJK Unified Ideographs from the zh.json locale file.
 */
function extractChineseChars(localePath) {
  const data = JSON.parse(fs.readFileSync(localePath, "utf-8"));

  // Flatten all string values
  const strings = [];
  const walk = (obj) => {
    for (const v of Object.values(obj)) {
      if (typeof v === "string") strings.push(v);
      else if (typeof v === "object" && v !== null) walk(v);
    }
  };
  walk(data);

  const allText = strings.join("");
  const regex = /[\u3400-\u9FFF]/gu;
  const chars = [...new Set(allText.match(regex) || "")];

  console.log(`\n🔤 Extracted ${chars.length} unique Chinese characters:`);
  console.log(chars.join(""));
  console.log("");

  return chars.join("");
}

/**
 * Convert opentype.js glyph commands to Three.js font outline string format.
 *
 * Three.js format: space-separated lowercase commands
 *   m x y          -> moveTo
 *   l x y          -> lineTo
 *   q cx cy x y    -> quadraticCurveTo
 *   b cx cy cx1 cy1 x y -> bezierCurveTo
 */
function convertGlyphToThreeString(glyph) {
  if (!glyph.path || glyph.path.commands.length === 0) return "";

  const parts = [];

  for (const cmd of glyph.path.commands) {
    switch (cmd.type) {
      case "M":
        parts.push("m", cmd.x, cmd.y);
        break;
      case "L":
        parts.push("l", cmd.x, cmd.y);
        break;
      case "Q":
        // Three.js q: control point first, then end point
        parts.push("q", cmd.x, cmd.y, cmd.x1, cmd.y1);
        break;
      case "C":
        // Three.js b: end point first, then cp1, then cp2
        // Wait, let me re-read the Three.js parser:
        //   case 'b':
        //     cpx = outline[i++] * scale + offsetX;
        //     cpy = outline[i++] * scale + offsetY;
        //     cpx1 = outline[i++] * scale + offsetX;
        //     cpy1 = outline[i++] * scale + offsetY;
        //     cpx2 = outline[i++] * scale + offsetX;
        //     cpy2 = outline[i++] * scale + offsetY;
        //     path.bezierCurveTo(cpx1, cpy1, cpx2, cpy2, cpx, cpy);
        // So order is: endX, endY, cp1x, cp1y, cp2x, cp2y
        parts.push("b", cmd.x, cmd.y, cmd.x1, cmd.y1, cmd.x2, cmd.y2);
        break;
      case "Z":
        // Three.js doesn't have a closePath command in the outline.
        // Paths are implicitly closed by the geometry generation.
        // We can skip Z commands.
        break;
      case "A":
        // Arc — opentype.js curves() already converts arcs to cubic beziers.
        // If we still see A, approximate as a line to the endpoint.
        parts.push("l", cmd.x, cmd.y);
        break;
      case "H":
        // Horizontal line
        parts.push("l", cmd.x, 0);
        break;
      case "V":
        // Vertical line
        parts.push("l", 0, cmd.y);
        break;
      case "S":
        // Smooth cubic bezier — treat as regular C
        parts.push("b", cmd.x, cmd.y, cmd.x1, cmd.y1, cmd.x, cmd.y);
        break;
      case "T":
        // Smooth quadratic — treat as regular Q
        parts.push("q", cmd.x, cmd.y, cmd.x, cmd.y);
        break;
      default:
        break;
    }
  }

  return parts.join(" ");
}

/**
 * Safely get the font family name, handling both standard and variable fonts.
 * Standard fonts: font.names.fontFamily.values[0].text
 * Variable fonts: font.names.windows.fontFamily.en
 */
function getFontFamilyName(font) {
  // Standard Three.js font format (e.g. from typeface.js)
  if (font.names.fontFamily?.values?.[0]?.text) {
    return font.names.fontFamily.values[0].text;
  }
  // Variable font format (opentype.js internal)
  if (font.names.windows?.fontFamily?.en) {
    return font.names.windows.fontFamily.en;
  }
  if (font.names.windows?.preferredFamily?.en) {
    return font.names.windows.preferredFamily.en;
  }
  return "ChineseFont";
}

function getFontSubfamilyName(font) {
  if (font.names.fontSubfamily?.values?.[0]?.text) {
    return font.names.fontSubfamily.values[0].text;
  }
  if (font.names.windows?.fontSubfamily?.en) {
    return font.names.windows.fontSubfamily.en;
  }
  return "Regular";
}

/**
 * Build the Three.js FontLoader JSON structure from an opentype.js font
 * subset to the given characters.
 */
function buildThreeFontJSON(font, chars) {
  const glyphs = {};

  for (const char of chars) {
    addGlyph(font, glyphs, char);
  }

  const asciiChars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?;:()[]{}\"'\\/-+%=&@#$*^_~`\n ";
  for (const char of asciiChars) {
    if (!(char in glyphs)) {
      addGlyph(font, glyphs, char);
    }
  }

  const punctChars = "，。、；：！？（）【】《》「」『』—·～…";
  for (const char of punctChars) {
    if (!(char in glyphs)) {
      addGlyph(font, glyphs, char);
    }
  }

  let xMin = Infinity,
    yMin = Infinity,
    xMax = -Infinity,
    yMax = -Infinity;
  for (const g of Object.values(glyphs)) {
    if (g.x_min !== undefined && !isNaN(g.x_min)) {
      xMin = Math.min(xMin, g.x_min);
      xMax = Math.max(xMax, g.x_max);
    }
  }

  yMin = font.descender;
  yMax = font.ascender;

  return {
    glyphs: glyphs,
    familyName: getFontFamilyName(font),
    ascender: font.ascender,
    descender: font.descender,
    resolution: font.unitsPerEm,
    boundingBox: {
      yMin: yMin === Infinity ? font.descender : yMin,
      xMin: xMin === Infinity ? 0 : xMin,
      yMax: yMax === -Infinity ? font.ascender : yMax,
      xMax: xMax === -Infinity ? 1000 : xMax,
    },
    underlinePosition: font.tables.os2?.usUnderlinePosition ?? font.descender,
    underlineThickness:
      font.tables.os2?.usUnderlineThickness ?? Math.floor(font.unitsPerEm / 14),
    cssFontWeight: "normal",
    cssFontStyle: "normal",
    lineHeight: font.ascender - font.descender,
  };
}

function addGlyph(font, glyphs, char) {
  const glyph = font.charToGlyph(char);
  const outline = convertGlyphToThreeString(glyph);

  const xMin = glyph.xMin ?? 0;
  const xMax = glyph.xMax ?? glyph.advanceWidth;

  glyphs[char] = {
    x_min: Math.round(xMin),
    x_max: Math.round(xMax),
    ha: Math.round(glyph.advanceWidth),
    o: outline,
  };
}

async function main() {
  const args = process.argv.slice(2);
  const fontPath = args[0];
  const outputName = args[1] || "chineseSubset";

  if (!fontPath) {
    console.error("Usage: node scripts/subset-chinese-font.js <path-to-ttf-font> [output-name]");
    console.error("Example: node scripts/subset-chinese-font.js ./fonts/NotoSansSC-Regular.ttf");
    process.exit(1);
  }

  const resolvedFontPath = path.resolve(rootDir, fontPath);

  if (!fs.existsSync(resolvedFontPath)) {
    console.error(`❌ Font file not found: ${resolvedFontPath}`);
    console.error("\n💡 Download a free Chinese font, e.g.:");
    console.error(
      "   Noto Sans SC: https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC[wght].ttf"
    );
    console.error("   Or any .ttf file that supports Chinese characters.");
    process.exit(1);
  }

  console.log(`\n📂 Loading font: ${resolvedFontPath}`);

  const chars = extractChineseChars(LOCALE_FILE);

  const fontBuffer = fs.readFileSync(resolvedFontPath);
  const font = opentype.parse(fontBuffer);

  console.log(`🔤 Font: "${getFontFamilyName(font)}"`);
  console.log(`📐 Units per em: ${font.unitsPerEm}`);
  console.log(`📊 Total glyphs in font: ${font.glyphs.length}`);

  console.log("\n✂️  Building subset JSON...");
  const result = buildThreeFontJSON(font, chars);

  const glyphCount = Object.keys(result.glyphs).filter(
    (k) => result.glyphs[k].o && result.glyphs[k].o.length > 0
  ).length;
  console.log(`✅ Subset contains ${glyphCount} glyphs (Chinese + ASCII + punctuation)`);

  const outputPath = path.join(OUTPUT_DIR, `${outputName}.json`);
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf-8");

  const fileSize = fs.statSync(outputPath).size;
  const fileSizeKB = (fileSize / 1024).toFixed(1);

  console.log(`\n💾 Written to: ${outputPath}`);
  console.log(`📦 File size: ${fileSizeKB} KB`);
  console.log("\n✨ Done! Use this font in your Three.js TextGeometry:");
  console.log(`   const font = useLoader(FontLoader, "./fonts/${outputName}.json");`);
}

main().catch((err) => {
  console.error("❌ Error:", err.message);
  process.exit(1);
});
