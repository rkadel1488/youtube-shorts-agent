const sharp = require('sharp');
const fs = require('fs');
const path = require('path');
const config = require('../../config');

/**
 * High-CTR Children's Cartoon YouTube Thumbnail Generator
 * Creates 1280x720 thumbnails with hyper-vibrant 3D cartoon visuals,
 * giant bubble 3D typography, starburst badges, and high-contrast styling.
 */
class ThumbnailMaker {
  constructor() {
    this.width = config.thumbnail.width || 1280;
    this.height = config.thumbnail.height || 720;
  }

  /**
   * Generates a YouTube thumbnail for a song or compilation
   * @param {Object} options
   *   title: Main title (e.g. "WHEELS ON THE BUS")
   *   badgeText: Badge stamp (e.g. "30 MINS COMPILATION")
   *   characterTheme: 'bus' | 'animals' | 'dino' | 'colors' | 'ducks' | 'star' | 'general'
   *   outputPath: Target .png / .jpg file
   */
  async generateThumbnail(options = {}) {
    const {
      title = 'WHEELS ON THE BUS',
      badgeText = '⭐ 30 MINS NON-STOP ⭐',
      characterTheme = 'bus',
      outputPath
    } = options;

    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    const escapeXml = (str) => (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const safeTitle = escapeXml(title.toUpperCase());
    const safeBadge = escapeXml(badgeText.toUpperCase());

    // Generate theme character graphic in thumbnail
    const characterSvg = this._getThumbnailCharacter(characterTheme);

    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${this.width}" height="${this.height}" viewBox="0 0 ${this.width} ${this.height}">
  <defs>
    <!-- Vibrant Background Sky -->
    <linearGradient id="thumbBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00D2FF" />
      <stop offset="60%" stop-color="#3A7BD5" />
      <stop offset="100%" stop-color="#1E3C72" />
    </linearGradient>

    <!-- Starburst Glow -->
    <radialGradient id="sunburst" cx="70%" cy="40%" r="65%">
      <stop offset="0%" stop-color="#FFF9C4" stop-opacity="1" />
      <stop offset="40%" stop-color="#FFEE58" stop-opacity="0.8" />
      <stop offset="80%" stop-color="#FDD835" stop-opacity="0.3" />
      <stop offset="100%" stop-color="#FBC02D" stop-opacity="0" />
    </radialGradient>

    <!-- Hill Gradient -->
    <linearGradient id="thumbHills" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#76FF03" />
      <stop offset="100%" stop-color="#388E3C" />
    </linearGradient>

    <!-- 3D Typography Shadow Filter -->
    <filter id="text3D" x="-15%" y="-15%" width="130%" height="130%">
      <feDropShadow dx="0" dy="10" stdDeviation="6" flood-color="#000000" flood-opacity="0.9" />
    </filter>

    <filter id="badgeShadow" x="-15%" y="-15%" width="130%" height="130%">
      <feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#000000" flood-opacity="0.65" />
    </filter>
  </defs>

  <!-- Background Sky & Sunburst -->
  <rect width="${this.width}" height="${this.height}" fill="url(#thumbBg)" />
  <circle cx="890" cy="280" r="550" fill="url(#sunburst)" />

  <!-- Rolling Lush Green Hills -->
  <path d="M -50 480 Q 400 350 850 490 T 1350 450 L 1350 720 L -50 720 Z" fill="url(#thumbHills)" />
  <path d="M -50 560 Q 600 440 1350 560 L 1350 720 L -50 720 Z" fill="#2E7D32" />

  <!-- Cartoon Character Hero Graphic -->
  ${characterSvg}

  <!-- Floating Sparkles & Music Notes -->
  <text x="80" y="260" font-size="80" fill="#FF4081" font-weight="bold" filter="url(#badgeShadow)">♪</text>
  <text x="1140" y="160" font-size="95" fill="#FFE57F" font-weight="bold" filter="url(#badgeShadow)">♫</text>
  <text x="1200" y="320" font-size="70" fill="#00E676" font-weight="bold" filter="url(#badgeShadow)">★</text>

  <!-- Top Attention Badge / Ribbon -->
  <g transform="translate(60, 45)" filter="url(#badgeShadow)">
    <rect x="0" y="0" width="540" height="75" rx="37" fill="#FF1744" stroke="#FFFFFF" stroke-width="6" />
    <text x="270" y="52" font-family="'Arial Rounded MT Bold', 'Impact', sans-serif" font-weight="900" font-size="34" fill="#FFFFFF" text-anchor="middle" letter-spacing="1">
      ${safeBadge}
    </text>
  </g>

  <!-- Big 3D Punchy Headline Typography -->
  <g filter="url(#text3D)">
    <!-- Main 3D Text Stroke (Deep Outline) -->
    <text x="70" y="640" font-family="'Arial Rounded MT Bold', 'Impact', sans-serif" font-weight="900" font-size="82" fill="#FFE600" stroke="#0D001A" stroke-width="22" paint-order="stroke fill" letter-spacing="2">
      ${safeTitle}
    </text>
    <!-- Foreground Text Glow -->
    <text x="70" y="640" font-family="'Arial Rounded MT Bold', 'Impact', sans-serif" font-weight="900" font-size="82" fill="#FFE600" letter-spacing="2">
      ${safeTitle}
    </text>
  </g>

  <!-- Subtle Yellow Contrast Border around entire Thumbnail -->
  <rect x="0" y="0" width="${this.width}" height="${this.height}" fill="none" stroke="#FFE600" stroke-width="12" />
</svg>
    `;

    await sharp(Buffer.from(svg))
      .resize(this.width, this.height)
      .jpeg({ quality: 95 })
      .toFile(outputPath);

    return outputPath;
  }

  /**
   * Character illustration sub-graphics for thumbnail
   */
  _getThumbnailCharacter(theme) {
    if (theme === 'bus' || theme.includes('vehicle')) {
      return `
    <g transform="translate(540, 200) scale(0.9)" filter="url(#text3D)">
      <!-- School Bus Body -->
      <rect x="0" y="0" width="680" height="340" rx="50" fill="#FFD600" stroke="#E65100" stroke-width="14" />
      <rect x="0" y="200" width="680" height="30" fill="#E53935" />
      <!-- Windows -->
      <rect x="40" y="40" width="160" height="130" rx="20" fill="#E0F7FA" stroke="#37474F" stroke-width="8" />
      <rect x="230" y="40" width="130" height="130" rx="20" fill="#E0F7FA" stroke="#37474F" stroke-width="8" />
      <rect x="390" y="40" width="130" height="130" rx="20" fill="#E0F7FA" stroke="#37474F" stroke-width="8" />
      <!-- Huge Smiling Eyes -->
      <ellipse cx="95" cy="105" rx="16" ry="24" fill="#263238" /><circle cx="100" cy="98" r="6" fill="#FFFFFF" />
      <ellipse cx="150" cy="105" rx="16" ry="24" fill="#263238" /><circle cx="155" cy="98" r="6" fill="#FFFFFF" />
      <circle cx="75" cy="130" r="14" fill="#FF8A80" opacity="0.8" />
      <circle cx="170" cy="130" r="14" fill="#FF8A80" opacity="0.8" />
      <path d="M 105 125 Q 122 145 140 125" stroke="#263238" stroke-width="7" stroke-linecap="round" fill="#E53935" />
      <!-- Cute Bear in Middle Window -->
      <circle cx="295" cy="105" r="34" fill="#8D6E63" />
      <circle cx="280" cy="78" r="12" fill="#6D4C41" /><circle cx="310" cy="78" r="12" fill="#6D4C41" />
      <circle cx="288" cy="100" r="5" fill="#000000" /><circle cx="302" cy="100" r="5" fill="#000000" />
      <!-- Wheels -->
      <circle cx="140" cy="330" r="60" fill="#263238" /><circle cx="140" cy="330" r="35" fill="#CFD8DC" />
      <circle cx="540" cy="330" r="60" fill="#263238" /><circle cx="540" cy="330" r="35" fill="#CFD8DC" />
    </g>
      `;
    }

    if (theme === 'dino' || theme.includes('dinosaur')) {
      return `
    <g transform="translate(680, 180)" filter="url(#text3D)">
      <!-- Cute Baby Green T-Rex -->
      <ellipse cx="200" cy="240" rx="130" ry="150" fill="#66BB6A" stroke="#2E7D32" stroke-width="12" />
      <ellipse cx="220" cy="260" rx="70" ry="90" fill="#FFF59D" />
      <!-- Big Head -->
      <circle cx="200" cy="110" r="95" fill="#66BB6A" stroke="#2E7D32" stroke-width="12" />
      <circle cx="240" cy="95" r="28" fill="#FFFFFF" stroke="#2E7D32" stroke-width="6" />
      <circle cx="248" cy="95" r="16" fill="#1B5E20" /><circle cx="254" cy="90" r="6" fill="#FFFFFF" />
      <!-- Big Cute Open Smile -->
      <path d="M 170 140 Q 220 180 260 140" stroke="#1B5E20" stroke-width="8" stroke-linecap="round" fill="#E53935" />
      <polygon points="200,145 208,158 216,145" fill="#FFFFFF" />
      <polygon points="225,145 233,158 241,145" fill="#FFFFFF" />
      <circle cx="160" cy="130" r="16" fill="#FF8A80" opacity="0.8" />
    </g>
      `;
    }

    // Default Animal Farm / Cow
    return `
    <g transform="translate(620, 200)" filter="url(#text3D)">
      <ellipse cx="240" cy="220" rx="160" ry="120" fill="#FFFFFF" stroke="#263238" stroke-width="12" />
      <path d="M 160 170 Q 200 140 230 180 Q 260 220 200 240 Z" fill="#263238" />
      <!-- Head -->
      <circle cx="100" cy="110" r="85" fill="#FFFFFF" stroke="#263238" stroke-width="10" />
      <ellipse cx="70" cy="100" rx="14" ry="20" fill="#263238" /><circle cx="74" cy="94" r="5" fill="#FFFFFF" />
      <ellipse cx="130" cy="100" rx="14" ry="20" fill="#263238" /><circle cx="134" cy="94" r="5" fill="#FFFFFF" />
      <ellipse cx="100" cy="140" rx="55" ry="32" fill="#F8BBD0" stroke="#EC407A" stroke-width="6" />
      <circle cx="85" cy="136" r="6" fill="#C2185B" /><circle cx="115" cy="136" r="6" fill="#C2185B" />
      <circle cx="45" cy="120" r="14" fill="#FF8A80" opacity="0.7" />
      <circle cx="155" cy="120" r="14" fill="#FF8A80" opacity="0.7" />
    </g>
    `;
  }
}

module.exports = new ThumbnailMaker();
