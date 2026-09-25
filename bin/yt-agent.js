#!/usr/bin/env node

const { Command } = require('commander');
const _chalk = require('chalk');
const chalk = _chalk.default || _chalk;
const figlet = require('figlet');
const Table = require('cli-table3');
const fs = require('fs');
const path = require('path');
const config = require('../src/config');
const orchestrator = require('../src/orchestrator');
const thumbnailMaker = require('../src/services/thumbnail/thumbnail_maker');
const seoOptimizer = require('../src/services/seo/seo_optimizer');
const youtubeAuth = require('../src/services/youtube/auth');
const youtubeUploader = require('../src/services/youtube/uploader');
const autopilotScheduler = require('../src/services/autopilot/scheduler');
const { SONGS_DATABASE } = require('../src/config/songs_database');

const program = new Command();

function printBanner() {
  console.log(chalk.bold.yellow(figlet.textSync('YT AGENT', { horizontalLayout: 'full' })));
  console.log(chalk.bold.cyan('  👶 Automated Children\'s Cartoon YouTube Workflow Engine'));
  console.log(chalk.dim('  Autonomous Song Generation • 1080p Animations • High-CTR Thumbnails • Top SEO • Direct Upload\n'));
}

program
  .name('yt-agent')
  .description('Autonomous YouTube Children\'s Cartoon Compilation Workflow')
  .version('1.0.0');

// 1. COMPILE LONG-FORM VIDEO
program
  .command('compile')
  .description('Generate and stitch a full long-form children\'s cartoon nursery rhyme compilation')
  .option('-n, --count <number>', 'Number of songs to include in compilation', (v) => parseInt(v), 3)
  .option('-t, --theme <theme>', 'Theme category (vehicles, animals, dinosaurs, colors, counting, bedtime)', null)
  .option('-u, --upload', 'Automatically upload to YouTube upon compilation', false)
  .option('-p, --privacy <status>', 'YouTube privacy status (private, unlisted, public)', 'unlisted')
  .action(async (options) => {
    printBanner();
    try {
      console.log(chalk.bold.green(`🎬 Starting Compilation Workflow for ${options.count} songs...`));
      const result = await orchestrator.generateCompilation({
        songCount: options.count,
        themeCategory: options.theme,
        autoUpload: options.upload,
        privacyStatus: options.privacy
      });

      console.log(chalk.bold.green('\n🎉 COMPILATION SUCCEEDED!'));
      console.log(chalk.cyan(`📹 Video: ${result.masterVideoPath}`));
      console.log(chalk.yellow(`🖼️ Thumbnail: ${result.thumbnailPath}`));
      console.log(chalk.magenta(`⏱️ Duration: ${result.durationFormatted}`));
      console.log(chalk.blue(`📝 Title: ${result.title}`));
    } catch (err) {
      console.error(chalk.bold.red('\n❌ Error generating compilation:'), err.message);
      process.exit(1);
    }
  });

// 2. GENERATE SINGLE SONG
program
  .command('song')
  .description('Generate a single complete cartoon nursery rhyme song video')
  .option('--topic <topic>', 'Topic or keyword for the song', 'bus')
  .option('--voice <voice>', 'Voice ID (en-US-AnaNeural, en-US-JennyNeural, etc.)', 'en-US-AnaNeural')
  .action(async (options) => {
    printBanner();
    try {
      console.log(chalk.bold.green(`🎵 Generating cartoon song for topic: "${options.topic}"...`));
      const songRecord = await orchestrator.generateSong({
        topic: options.topic,
        voice: options.voice,
        onProgress: (p) => console.log(chalk.dim(`   ${p.step} (${p.percent}%)`))
      });

      console.log(chalk.bold.green('\n🎉 SONG GENERATED SUCCESSFULLY!'));
      console.log(chalk.cyan(`📹 Video: ${songRecord.videoPath}`));
      console.log(chalk.magenta(`⏱️ Duration: ${songRecord.durationFormatted}`));
    } catch (err) {
      console.error(chalk.bold.red('\n❌ Error generating song:'), err.message);
      process.exit(1);
    }
  });

// 3. THUMBNAIL STUDIO
program
  .command('thumbnail')
  .description('Generate high-CTR 1280x720 cartoon thumbnail with 3D bubble typography')
  .option('--title <title>', 'Main title text', 'WHEELS ON THE BUS')
  .option('--badge <badge>', 'Top ribbon badge text', '⭐ 30 MINS NON-STOP ⭐')
  .option('--theme <theme>', 'Theme (bus, animals, dino, colors)', 'bus')
  .option('-o, --out <path>', 'Output image path', path.join(config.paths.thumbnails, `thumb_${Date.now()}.jpg`))
  .action(async (options) => {
    printBanner();
    try {
      console.log(chalk.bold.green(`🎨 Generating 1280x720 High-CTR Cartoon Thumbnail...`));
      const outputPath = await thumbnailMaker.generateThumbnail({
        title: options.title,
        badgeText: options.badge,
        characterTheme: options.theme,
        outputPath: options.out
      });

      console.log(chalk.bold.green('✅ Thumbnail created:'), chalk.cyan(outputPath));
    } catch (err) {
      console.error(chalk.bold.red('\n❌ Error creating thumbnail:'), err.message);
      process.exit(1);
    }
  });

// 4. SEO OPTIMIZER
program
  .command('seo')
  .description('Generate algorithmic YouTube titles, timestamped chapter descriptions, and 45+ tags')
  .option('--title <title>', 'Lead song title', 'The Wheels on the Bus')
  .option('--duration <duration>', 'Duration string', '20 Mins')
  .action(async (options) => {
    printBanner();
    try {
      const dummySongs = SONGS_DATABASE.slice(0, 4);
      const dummyChapters = [
        { timestamp: '00:00', title: 'Welcome & Sing-Along Intro 🎵' },
        { timestamp: '00:04', title: 'The Wheels on the Bus 🚌' },
        { timestamp: '02:40', title: 'Old MacDonald Had a Farm 🐮' },
        { timestamp: '05:15', title: 'Baby Dino Stomp & Dance 🦕' }
      ];

      const seo = await seoOptimizer.generateSEOPackage({
        compilationTitle: options.title,
        songs: dummySongs,
        chapters: dummyChapters,
        totalDurationFormatted: options.duration
      });

      console.log(chalk.bold.yellow('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
      console.log(chalk.bold.cyan('🎯 HIGH-RANKING YOUTUBE TITLE:'));
      console.log(chalk.bold.white(seo.title));
      console.log(chalk.bold.yellow('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
      console.log(chalk.bold.cyan('🏷️ TARGET SEARCH TAGS (Count: ' + seo.tags.length + '):'));
      console.log(chalk.dim(seo.tags.join(', ')));
      console.log(chalk.bold.yellow('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
      console.log(chalk.bold.cyan('📝 COMPLETE YOUTUBE DESCRIPTION WITH CHAPTERS & LYRICS:'));
      console.log(seo.description);
      console.log(chalk.bold.yellow('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
    } catch (err) {
      console.error(chalk.bold.red('❌ SEO error:'), err.message);
    }
  });

// 5. YOUTUBE OAUTH SETUP
program
  .command('auth')
  .description('Authorize and connect your YouTube Channel via Google OAuth2')
  .option('--port <number>', 'Local redirect server port', (v) => parseInt(v), 3000)
  .action(async (options) => {
    printBanner();
    try {
      console.log(chalk.bold.yellow('🔐 YouTube Channel OAuth2 Authorization Helper\n'));

      const clientId = config.youtube.clientId;
      const clientSecret = config.youtube.clientSecret;

      if (!clientId || !clientSecret) {
        console.log(chalk.red('⚠️ Missing YOUTUBE_CLIENT_ID or YOUTUBE_CLIENT_SECRET in .env file!'));
        console.log(chalk.yellow('\nHow to get Google YouTube API credentials:'));
        console.log(chalk.dim('1. Visit https://console.cloud.google.com/'));
        console.log(chalk.dim('2. Create a project and enable "YouTube Data API v3"'));
        console.log(chalk.dim('3. Create OAuth 2.0 Client ID (Web Application)'));
        console.log(chalk.dim('4. Add Authorized redirect URI: http://localhost:3000/oauth2callback'));
        console.log(chalk.dim('5. Copy Client ID and Secret to .env file in project root\n'));
        return;
      }

      console.log(chalk.green('Starting local auth receiver server on port ' + options.port + '...'));
      await youtubeAuth.startLocalAuthServer(options.port);
      console.log(chalk.bold.green('✅ Channel successfully authenticated and ready for auto-uploading!'));
    } catch (err) {
      console.error(chalk.bold.red('❌ Auth error:'), err.message);
    }
  });

// 6. UPLOAD EXISTING VIDEO
program
  .command('upload')
  .description('Upload an existing video and thumbnail to YouTube')
  .requiredOption('-v, --video <path>', 'Video file path')
  .option('-t, --thumbnail <path>', 'Thumbnail image path')
  .option('--title <title>', 'Video Title', 'Kids Songs Compilation')
  .option('-p, --privacy <status>', 'Privacy status (private, unlisted, public)', 'unlisted')
  .action(async (options) => {
    printBanner();
    try {
      const seo = {
        title: options.title,
        description: 'Enjoy this exciting cartoon nursery rhymes compilation for kids!',
        tags: ['nursery rhymes', 'kids songs', 'children cartoon'],
        categoryId: '27'
      };

      const result = await youtubeUploader.uploadCompilation({
        videoPath: options.video,
        thumbnailPath: options.thumbnail,
        seo: seo,
        privacyStatus: options.privacy
      });

      console.log(chalk.bold.green('\n✅ Upload complete:'), result);
    } catch (err) {
      console.error(chalk.bold.red('❌ Upload failed:'), err.message);
    }
  });

// 7. AUTOPILOT SCHEDULER
program
  .command('autopilot')
  .description('Start autonomous background cron scheduler for automatic generation and publishing')
  .option('-c, --cron <expression>', 'Cron schedule expression', config.autopilot.schedule)
  .option('-n, --count <number>', 'Songs per compilation', (v) => parseInt(v), 5)
  .option('-u, --upload', 'Auto-publish to YouTube on each run', config.autopilot.autoPublish)
  .option('-p, --privacy <status>', 'YouTube privacy', config.youtube.defaultPrivacy)
  .action((options) => {
    printBanner();
    console.log(chalk.bold.magenta('🤖 STARTING AUTONOMOUS AUTOPILOT SCHEDULER'));
    autopilotScheduler.start(options.cron, {
      songCount: options.count,
      autoPublish: options.upload,
      privacyStatus: options.privacy
    });
  });

// 8. LIST PAST COMPILATIONS
program
  .command('list')
  .description('List past generated compilations and projects')
  .action(() => {
    printBanner();
    const historyFile = path.join(config.paths.data, 'compilations_history.json');
    if (!fs.existsSync(historyFile)) {
      console.log(chalk.yellow('No compilations generated yet. Run: "node bin/yt-agent.js compile" to start!'));
      return;
    }

    const history = JSON.parse(fs.readFileSync(historyFile, 'utf8'));
    const table = new Table({
      head: [
        chalk.cyan('ID'),
        chalk.cyan('Title'),
        chalk.cyan('Duration'),
        chalk.cyan('Songs'),
        chalk.cyan('Created At'),
        chalk.cyan('YouTube URL')
      ]
    });

    history.forEach(item => {
      table.push([
        item.id,
        item.title.substring(0, 35) + '...',
        item.durationFormatted,
        item.songCount,
        new Date(item.createdAt).toLocaleDateString(),
        item.youtubeUrl || chalk.dim('Local Only')
      ]);
    });

    console.log(table.toString());
  });

// 9. STORYBOARD & CHARACTER GENERATOR
program
  .command('storyboard')
  .description('Generate character specification sheet and Google Flow / Veo 2 motion storyboard')
  .option('-t, --topic <topic>', 'Song topic or theme', 'bus')
  .action(async (options) => {
    printBanner();
    try {
      const lyricsGenerator = require('../src/services/lyrics/generator');
      const characterCreator = require('../src/services/visuals/character_creator');
      const storyboardGenerator = require('../src/services/visuals/storyboard_generator');

      console.log(chalk.bold.green(`🎬 Generating Cartoon Character & Storyboard for topic: "${options.topic}"...`));
      const song = await lyricsGenerator.generateSong({ topic: options.topic });
      const character = characterCreator.getCharacterForSong(song);

      const outDir = path.join(config.paths.output, `storyboard_${Date.now()}`);
      fs.mkdirSync(outDir, { recursive: true });

      const cardPath = path.join(outDir, 'character_card.png');
      await characterCreator.generateCharacterCard(character, cardPath);

      const sb = await storyboardGenerator.generateStoryboard(song);
      const { jsonPath, htmlPath } = await storyboardGenerator.saveStoryboard(sb, outDir);

      console.log(chalk.bold.green('\n🎉 STORYBOARD & CHARACTER CREATED!'));
      console.log(chalk.cyan(`⭐ Character: ${character.name} (${character.species})`));
      console.log(chalk.yellow(`🖼️ Character Card: ${cardPath}`));
      console.log(chalk.magenta(`📜 Storyboard JSON: ${jsonPath}`));
      console.log(chalk.blue(`🌐 Visual HTML Storyboard: ${htmlPath}`));
      console.log(chalk.cyan(`\n⚡ Google Flow / Veo 2 Prompt Sample (Scene 1):`));
      console.log(chalk.dim(sb.scenes[0].veoPrompt));
    } catch (err) {
      console.error(chalk.bold.red('\n❌ Error generating storyboard:'), err.message);
      process.exit(1);
    }
  });

// 10. INSTANT DEMO VERIFICATION
program
  .command('demo')
  .description('Run a rapid end-to-end test verification of audio synthesis, cartoon art, and thumbnail')
  .action(async () => {
    printBanner();
    console.log(chalk.bold.cyan('🧪 RUNNING FAST END-TO-END VERIFICATION TEST...\n'));

    const demoDir = path.join(config.paths.output, 'demo_test');
    if (!fs.existsSync(demoDir)) fs.mkdirSync(demoDir, { recursive: true });

    try {
      // 1. Test thumbnail maker
      console.log(chalk.yellow('1/3 Testing High-CTR Thumbnail generation (1280x720)...'));
      const thumbPath = path.join(demoDir, 'demo_thumbnail.jpg');
      await thumbnailMaker.generateThumbnail({
        title: 'WHEELS ON THE BUS',
        badgeText: '⭐ 20 MINS NON-STOP ⭐',
        characterTheme: 'bus',
        outputPath: thumbPath
      });
      console.log(chalk.green(`   ✔ Thumbnail rendered (${(fs.statSync(thumbPath).size / 1024).toFixed(0)} KB)`));

      // 2. Test single verse song generation
      console.log(chalk.yellow('2/3 Testing Vocal Singer, Instrumental Mix & 1080p Cartoon Animation...'));
      const demoSong = {
        id: 'demo-bus',
        title: 'The Wheels on the Bus',
        theme: 'vehicles',
        bpm: 115,
        musicalStyle: 'bounce',
        verses: [
          {
            verseNumber: 1,
            lyrics: 'The wheels on the bus go round and round! All through the town!',
            sceneDescription: 'Sunny cartoon school bus on hillside'
          }
        ]
      };

      const sceneGenerator = require('../src/services/visuals/scene_generator');
      const cartoonAnimator = require('../src/services/visuals/animator');
      const ttsSinger = require('../src/services/music/tts_singer');
      const audioMixer = require('../src/services/music/mixer');

      const scenePath = path.join(demoDir, 'demo_scene.png');
      await sceneGenerator.generateScene(demoSong.verses[0], demoSong, scenePath);
      console.log(chalk.green('   ✔ 1920x1080 3D Cartoon scene generated'));

      const vocalResult = await ttsSinger.generateVocals(demoSong, demoDir, {});
      console.log(chalk.green(`   ✔ Studio children vocal synthesized (${vocalResult.totalDurationSec.toFixed(1)}s)`));

      const mixed = await audioMixer.produceSongAudio({
        vocalPath: vocalResult.vocalPath,
        totalDurationSec: vocalResult.totalDurationSec,
        song: demoSong,
        outputDir: demoDir
      });
      console.log(chalk.green('   ✔ Vocal + Polyphonic nursery chimes mixed & normalized'));

      const clipPath = path.join(demoDir, 'demo_clip.mp4');
      await cartoonAnimator.createVerseClip(
        scenePath,
        vocalResult.totalDurationSec,
        demoSong.verses[0].lyrics,
        clipPath,
        { motionIndex: 0 }
      );
      console.log(chalk.green('   ✔ Ken Burns camera motion & sing-along lyric subtitle applied'));

      const finalDemoVideo = path.join(demoDir, 'demo_final.mp4');
      await cartoonAnimator.stitchSongVideo([clipPath], mixed.audioPath, finalDemoVideo);
      console.log(chalk.green(`   ✔ 1080p Video stitched (${(fs.statSync(finalDemoVideo).size / 1024).toFixed(0)} KB)`));

      // 3. Test SEO
      console.log(chalk.yellow('3/3 Testing YouTube SEO optimizer...'));
      const seo = await seoOptimizer.generateSEOPackage({
        compilationTitle: demoSong.title,
        songs: [demoSong],
        chapters: [{ timestamp: '00:00', title: 'The Wheels on the Bus 🚌' }],
        totalDurationFormatted: '1 Min'
      });
      console.log(chalk.green(`   ✔ Title: ${seo.title}`));
      console.log(chalk.green(`   ✔ Generated ${seo.tags.length} high-traffic tags`));

      console.log(chalk.bold.green('\n🎉 ALL PIPELINE MODULES VERIFIED & WORKING FLAWLESSLY!'));
      console.log(chalk.cyan(`   Test Video: ${finalDemoVideo}`));
      console.log(chalk.cyan(`   Test Thumbnail: ${thumbPath}\n`));
    } catch (err) {
      console.error(chalk.bold.red('\n❌ Demo verification failed:'), err);
    }
  });

program.parse(process.argv);
