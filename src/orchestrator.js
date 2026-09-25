const fs = require('fs');
const path = require('path');
const config = require('./config');
const lyricsGenerator = require('./services/lyrics/generator');
const ttsSinger = require('./services/music/tts_singer');
const audioMixer = require('./services/music/mixer');
const sceneGenerator = require('./services/visuals/scene_generator');
const cartoonAnimator = require('./services/visuals/animator');
const compilationBuilder = require('./services/compiler/video_compiler');
const thumbnailMaker = require('./services/thumbnail/thumbnail_maker');
const seoOptimizer = require('./services/seo/seo_optimizer');
const youtubeUploader = require('./services/youtube/uploader');

/**
 * Master YouTube Workflow Orchestrator
 * End-to-end automation connecting song generation, visual animation,
 * long-form compilation compilation, high-CTR thumbnail design, SEO, and YouTube publishing.
 */
class WorkflowOrchestrator {
  constructor() {
    this.ensureDirectories();
  }

  ensureDirectories() {
    [
      config.paths.output,
      config.paths.compilations,
      config.paths.songs,
      config.paths.thumbnails,
      config.paths.data,
      config.paths.credentials
    ].forEach(dir => {
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    });
  }

  /**
   * Generates a single complete cartoon nursery rhyme song video
   * @param {Object} options { songId, topic, voice, onProgress }
   */
  async generateSong(options = {}) {
    const { songId, topic, voice, onProgress } = options;

    const report = (step, percent) => {
      if (onProgress) onProgress({ step, percent });
    };

    report('1/5: Generating Rhyming Song Script & Verses...', 10);
    const song = await lyricsGenerator.generateSong({ songId, topic });
    const songDir = path.join(config.paths.songs, `${song.id}_${Date.now()}`);
    fs.mkdirSync(songDir, { recursive: true });

    report('2/5: Synthesizing Vocal Singer Audio (Edge TTS)...', 30);
    const vocalResult = await ttsSinger.generateVocals(song, songDir, { voice });

    report('3/5: Synthesizing & Mixing Children Instrumental Music...', 50);
    const mixedAudio = await audioMixer.produceSongAudio({
      vocalPath: vocalResult.vocalPath,
      totalDurationSec: vocalResult.totalDurationSec,
      song: song,
      outputDir: songDir
    });

    report('4/5: Generating 1920x1080 Cartoon Scenes & Animations...', 70);
    const verseClipPaths = [];
    for (let i = 0; i < vocalResult.verses.length; i++) {
      const v = vocalResult.verses[i];
      const sceneImgPath = path.join(songDir, `scene_v${v.verseNumber}.png`);
      const clipPath = path.join(songDir, `clip_v${v.verseNumber}.mp4`);

      // 1. Generate 3D Cartoon Scene
      await sceneGenerator.generateScene(v, song, sceneImgPath);

      // 2. Animate with Ken Burns motion & sing-along lyric subtitle
      await cartoonAnimator.createVerseClip(
        sceneImgPath,
        v.durationSec + 1.5,
        v.lyrics,
        clipPath,
        { motionIndex: i }
      );

      verseClipPaths.push(clipPath);
    }

    report('5/5: Stitching Complete Song Video...', 90);
    const finalVideoPath = path.join(songDir, `${song.id}_video.mp4`);
    await cartoonAnimator.stitchSongVideo(verseClipPaths, mixedAudio.audioPath, finalVideoPath);

    report('Completed Song Generation!', 100);

    const songRecord = {
      id: song.id,
      title: song.title,
      theme: song.theme,
      durationSec: vocalResult.totalDurationSec,
      durationFormatted: `${Math.floor(vocalResult.totalDurationSec / 60)}m ${Math.round(vocalResult.totalDurationSec % 60)}s`,
      audioPath: mixedAudio.audioPath,
      videoPath: finalVideoPath,
      songDir: songDir,
      verses: song.verses,
      seoKeywords: song.seoKeywords,
      createdAt: new Date().toISOString()
    };

    // Save song project metadata
    fs.writeFileSync(path.join(songDir, 'song_metadata.json'), JSON.stringify(songRecord, null, 2));
    return songRecord;
  }

  /**
   * Generates a Full Long-Form YouTube Compilation (e.g. 3-8 songs stacked)
   * Complete with Bumper Cards, High-CTR Thumbnail, High-Ranking SEO, and YouTube Upload
   * @param {Object} options
   */
  async generateCompilation(options = {}) {
    const {
      songCount = config.video.defaultCompilationSongCount || 5,
      themeCategory = null,
      autoUpload = false,
      privacyStatus = config.youtube.defaultPrivacy || 'unlisted',
      onProgress
    } = options;

    const report = (step, percent) => {
      if (onProgress) onProgress({ step, percent });
    };

    console.log(`\n======================================================`);
    console.log(`🌟 STARTING CHILDREN CARTOON YOUTUBE COMPILATION PIPELINE`);
    console.log(`🎬 Target: Long-Form Video (${songCount} Songs Compilation)`);
    console.log(`======================================================\n`);

    // 1. Generate Playlist of Songs
    report(`Planning compilation playlist (${songCount} songs)...`, 5);
    const playlistSongs = await lyricsGenerator.generateCompilationPlaylist(songCount, themeCategory);
    const renderedSongs = [];

    // 2. Generate Each Song Video
    for (let i = 0; i < playlistSongs.length; i++) {
      const pSong = playlistSongs[i];
      report(`Generating Song ${i + 1}/${songCount}: "${pSong.title}"...`, 10 + Math.round((i / songCount) * 50));
      console.log(`\n🎵 [Song ${i + 1}/${songCount}] Producing: "${pSong.title}"...`);

      const songRecord = await this.generateSong({
        songId: pSong.id,
        topic: pSong.theme,
        onProgress: (p) => {
          console.log(`   └─ ${p.step} (${p.percent}%)`);
        }
      });

      renderedSongs.push(songRecord);
    }

    // 3. Compile Master Long-Form Video with Bumper Cards & Chapters
    report('Stitching Long-Form Master Video with Cartoon Bumpers...', 65);
    console.log(`\n🎞️ Compiling ${renderedSongs.length} songs into 1080p Master Compilation...`);
    const compilationDir = path.join(config.paths.compilations, `compilation_${Date.now()}`);
    fs.mkdirSync(compilationDir, { recursive: true });

    const compilationResult = await compilationBuilder.buildCompilation(
      renderedSongs,
      compilationDir,
      `${renderedSongs[0].title} & Best Kids Songs`
    );

    // 4. Generate High-Ranking YouTube SEO Package
    report('Generating YouTube High-Ranking SEO & Chapters...', 80);
    console.log(`\n🔍 Generating Algorithmic YouTube SEO & Chapter Timestamps...`);
    const seoPackage = await seoOptimizer.generateSEOPackage({
      compilationTitle: compilationResult.compilationTitle,
      songs: renderedSongs,
      chapters: compilationResult.chapters,
      totalDurationFormatted: compilationResult.totalDurationFormatted
    });

    // 5. Generate High-CTR Cartoon Thumbnail
    report('Rendering High-CTR 1280x720 3D Cartoon Thumbnail...', 88);
    console.log(`\n🎨 Designing High-CTR YouTube Thumbnail (1280x720)...`);
    const thumbnailPath = path.join(compilationDir, 'thumbnail_master.jpg');
    await thumbnailMaker.generateThumbnail({
      title: renderedSongs[0].title,
      badgeText: `⭐ ${compilationResult.totalDurationFormatted.toUpperCase()} NON-STOP ⭐`,
      characterTheme: renderedSongs[0].theme,
      outputPath: thumbnailPath
    });

    // 6. Save Full Compilation Project Summary
    const compilationProject = {
      id: compilationResult.compilationId,
      title: seoPackage.title,
      masterVideoPath: compilationResult.videoPath,
      thumbnailPath: thumbnailPath,
      durationSec: compilationResult.totalDurationSec,
      durationFormatted: compilationResult.totalDurationFormatted,
      songCount: renderedSongs.length,
      chapters: compilationResult.chapters,
      seo: seoPackage,
      songs: renderedSongs,
      createdAt: new Date().toISOString()
    };

    fs.writeFileSync(
      path.join(compilationDir, 'compilation_project.json'),
      JSON.stringify(compilationProject, null, 2)
    );

    // Save also to global compilations index
    this._saveToHistory(compilationProject);

    // 7. Auto-Upload to YouTube if requested
    let uploadResult = null;
    if (autoUpload) {
      report('Uploading Video & Thumbnail to YouTube Channel...', 94);
      console.log(`\n📡 Publishing to YouTube Channel...`);
      uploadResult = await youtubeUploader.uploadCompilation({
        videoPath: compilationResult.videoPath,
        thumbnailPath: thumbnailPath,
        seo: seoPackage,
        privacyStatus: privacyStatus
      });
      compilationProject.youtube = uploadResult;
    }

    report('Workflow Pipeline Completed Successfully!', 100);
    console.log(`\n======================================================`);
    console.log(`🎉 COMPILATION READY!`);
    console.log(`📹 Video: ${compilationResult.videoPath}`);
    console.log(`🖼️ Thumbnail: ${thumbnailPath}`);
    console.log(`⏱️ Duration: ${compilationResult.totalDurationFormatted}`);
    console.log(`📝 Title: ${seoPackage.title}`);
    if (uploadResult && uploadResult.videoUrl) {
      console.log(`🔗 YouTube URL: ${uploadResult.videoUrl}`);
    }
    console.log(`======================================================\n`);

    return compilationProject;
  }

  _saveToHistory(compilation) {
    const historyFile = path.join(config.paths.data, 'compilations_history.json');
    let history = [];
    if (fs.existsSync(historyFile)) {
      try {
        history = JSON.parse(fs.readFileSync(historyFile, 'utf8'));
      } catch (e) {}
    }
    history.unshift({
      id: compilation.id,
      title: compilation.title,
      durationFormatted: compilation.durationFormatted,
      songCount: compilation.songCount,
      videoPath: compilation.masterVideoPath,
      thumbnailPath: compilation.thumbnailPath,
      createdAt: compilation.createdAt,
      youtubeUrl: compilation.youtube?.videoUrl || null
    });
    fs.writeFileSync(historyFile, JSON.stringify(history, null, 2));
  }
}

module.exports = new WorkflowOrchestrator();
