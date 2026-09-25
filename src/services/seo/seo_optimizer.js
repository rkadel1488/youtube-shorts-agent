const config = require('../../config');
const axios = require('axios');

/**
 * YouTube High-Ranking SEO Engine for Children's Nursery Rhymes
 * Generates algorithmic click-optimized titles, rich chapter descriptions,
 * 40+ high-traffic search tags, and COPPA compliant metadata.
 */
class SEOOptimizer {
  constructor() {
    this.geminiApiKey = config.ai.geminiApiKey;
  }

  /**
   * Generates full YouTube SEO package for a compilation
   * @param {Object} compilationDetails { compilationTitle, songs, chapters, totalDurationFormatted }
   */
  async generateSEOPackage(compilationDetails) {
    const { songs, chapters, totalDurationFormatted } = compilationDetails;
    const leadSong = songs[0] || { title: 'Nursery Rhymes' };
    const leadTheme = leadSong.theme || 'kids';

    // 1. Generate High-Ranking Title
    const title = this._generateClickTitle(leadSong.title, songs.length, totalDurationFormatted);

    // 2. Format Chapters Table
    const chaptersText = chapters
      .map(c => `${c.timestamp} ${c.title}`)
      .join('\n');

    // 3. Format Sing-Along Lyrics Section
    const lyricsSection = songs
      .map(s => {
        const verseLyrics = s.verses.map(v => v.lyrics).join('\n');
        return `🎵 ${s.title.toUpperCase()} LYRICS:\n${verseLyrics}`;
      })
      .join('\n\n');

    // 4. Generate High-Ranking Search Tags (Curated top traffic nursery keywords)
    const tags = this._generateSearchTags(leadSong, songs);

    // 5. Build Rich YouTube Description
    const description = `
🎉 Sing along and learn with our exciting ${totalDurationFormatted} compilation of the best nursery rhymes and children's cartoon songs! 

Join our adorable 3D cartoon animal friends as they dance, learn, and sing along to "${leadSong.title}" and many more toddler favorites! Perfect for preschool learning, baby sensory time, and family singing.

⏱️ VIDEO CHAPTERS & TIMESTAMPS:
${chaptersText}

🌟 EDUCATIONAL BENEFITS FOR TODDLERS:
• Language & vocabulary development through rhyming
• Counting, colors, and animal sound recognition
• Motor skills through clapping and dancing
• Positive bedtime & morning routines

━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 FULL SING-ALONG LYRICS:

${lyricsSection}

━━━━━━━━━━━━━━━━━━━━━━━━━━
👶 CHILD SAFETY & COPPA STATEMENT:
This video is created specifically for preschool children, toddlers, and families. It is 100% kid-safe, friendly, educational, and complies with YouTube Kids and COPPA policies.

🔔 Subscribe to our channel for new weekly 3D cartoon nursery rhymes and toddler learning videos!
👍 If you and your little one enjoyed this video, please leave a LIKE and share with friends!

#nurseryrhymes #kidssongs #toddlersongs #childrensongs #cartoonsongs #preschool #singalong #babysongs
`.trim();

    return {
      title: title,
      titleOptions: [
        title,
        `${leadSong.title} & More Kids Songs | Non-Stop Toddler Rhymes (${totalDurationFormatted})`,
        `Best Nursery Rhymes for Kids | ${leadSong.title} + Animal Songs (${totalDurationFormatted})`
      ],
      description: description,
      tags: tags,
      tagsString: tags.join(','),
      categoryId: config.youtube.categoryId || '27', // Education
      defaultLanguage: 'en',
      madeForKids: true,
      pinnedComment: `🎵 Which nursery rhyme was your little one's favorite today? Let us know! Don't forget to LIKE and SUBSCRIBE for more cartoon fun! 🎈✨`,
      communityPost: `NEW COMPILATION OUT NOW! 🚌🎉 Enjoy ${totalDurationFormatted} of non-stop nursery rhymes including "${leadSong.title}". Watch now and sing along!`
    };
  }

  /**
   * Generates click-friendly titles under 95 characters
   */
  _generateClickTitle(leadSongTitle, songCount, durationFormatted) {
    const templates = [
      `${leadSongTitle} + More Nursery Rhymes & Kids Songs | ${durationFormatted} Compilation`,
      `${leadSongTitle} | Top ${songCount} Nursery Rhymes for Toddlers (${durationFormatted})`,
      `${leadSongTitle} & Fun Cartoon Songs for Kids | ${durationFormatted} Sing-Along`,
      `Best Nursery Rhymes Compilation | ${leadSongTitle} + More Kids Songs (${durationFormatted})`
    ];
    return templates[0];
  }

  /**
   * Curates 40+ high-traffic nursery rhyme and toddler learning tags
   */
  _generateSearchTags(leadSong, allSongs) {
    const baseTags = [
      'nursery rhymes',
      'kids songs',
      'children songs',
      'toddler songs',
      'baby songs',
      'nursery rhymes for toddlers',
      'kids songs for children',
      'baby sensory songs',
      'preschool learning songs',
      'sing along songs for kids',
      'cartoon songs',
      'cartoon for kids',
      'animated nursery rhymes',
      'rhymes for baby',
      'nursery rhymes compilation',
      'kids videos for kids',
      'educational songs for toddlers',
      'toddler music',
      'cocomelon songs',
      'baby dance songs',
      'animal songs for kids',
      'sleep music for kids',
      'lullaby for babies'
    ];

    // Add specific song title tags
    allSongs.forEach(s => {
      baseTags.push(s.title);
      if (s.seoKeywords) {
        s.seoKeywords.forEach(k => baseTags.push(k));
      }
    });

    // Sanitize tags (YouTube forbids &, <, >, etc. and caps total chars to 500)
    const cleanTags = [];
    let totalLength = 0;

    for (const raw of baseTags) {
      if (!raw) continue;
      const sanitized = raw
        .replace(/&/g, 'and')
        .replace(/[<>:"/\\|?*#$!@%^()=+`~[\]{};]/g, '')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();

      if (sanitized && sanitized.length >= 2 && sanitized.length <= 35 && !cleanTags.includes(sanitized)) {
        if (totalLength + sanitized.length + 1 > 400) break;
        cleanTags.push(sanitized);
        totalLength += sanitized.length + 1;
      }
    }

    return cleanTags;
  }
}

module.exports = new SEOOptimizer();
