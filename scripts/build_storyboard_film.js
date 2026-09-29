const fs = require('fs');
const path = require('path');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const { MsEdgeTTS, OUTPUT_FORMAT } = require('msedge-tts');
const sharp = require('sharp');

ffmpeg.setFfmpegPath(ffmpegPath);

const BASE_DIR = path.join(__dirname, '..', 'output', 'google_flow_storyboard');
const IMAGES_DIR = path.join(BASE_DIR, 'images');
const CLIPS_DIR = path.join(BASE_DIR, 'clips');
const AUDIO_DIR = path.join(BASE_DIR, 'audio');

if (!fs.existsSync(CLIPS_DIR)) fs.mkdirSync(CLIPS_DIR, { recursive: true });
if (!fs.existsSync(AUDIO_DIR)) fs.mkdirSync(AUDIO_DIR, { recursive: true });

// Storyboard scenes data matching the Pixar Thanksgiving Blackout story
const scenes = [
  {
    id: 1,
    title: "The Golden Turkey",
    image: "scene1_happy_chef_1790682833186.jpg",
    narration: "Thanksgiving morning began with pure culinary ambition. Leo spent hours seasoning the golden turkey to absolute perfection.",
    subtitle: "Thanksgiving morning: Leo prepares the perfect golden roast turkey.",
    cameraMotion: "dolly_in",
    duration: 6,
    flowPrompt: "Pixar 3D animation style. A passionate young chef with neat dark hair, beard, wearing apron basting a golden roasted turkey in a sunlit cozy suburban kitchen. Warm volumetric godrays, rich textures, 4k render, cinematic 35mm lens."
  },
  {
    id: 2,
    title: "Family on the Way",
    image: "scene2_family_traveling_1790682850193.jpg",
    narration: "Miles away, Maya was navigating the highway home, while little brother Toby counted down the minutes at the cafe.",
    subtitle: "Across town, Maya drives home while Toby watches the clock at work.",
    cameraMotion: "pan_right",
    duration: 6,
    flowPrompt: "Pixar 3D animation style. Split screen showing cheerful sister driving blue car down autumn highway, and younger brother wiping cafe counter watching the wall clock. Golden hour lighting, vibrant colors, expressive Disney faces."
  },
  {
    id: 3,
    title: "The Sudden Blackout",
    image: "scene3_blackout_panic_1790682871834.jpg",
    narration: "Then, disaster struck. A neighborhood-wide blackout plunged the house into darkness, killing the oven mid-roast.",
    subtitle: "CRISIS! A sudden power outage shuts off the oven and darkens the street.",
    cameraMotion: "slow_zoom",
    duration: 6,
    flowPrompt: "Pixar 3D animation style. Shocked chef standing in dark kitchen with whisk and spatula as oven turns black. Outside window the whole street is in blackout. Dramatic dark blue moonlight, comic panic expression, cinematic lighting."
  },
  {
    id: 4,
    title: "Backup Plan Fails",
    image: "scene4_empty_grill_sos_1790682890274.jpg",
    narration: "Leo scrambled to the backyard BBQ grill for salvation—only to find the propane gauge pointing dead empty. In panic, he sent an urgent SOS.",
    subtitle: "No power, no gas! The propane tank is empty. Leo sends a frantic SOS!",
    cameraMotion: "push_tilt",
    duration: 6,
    flowPrompt: "Pixar 3D animation style. Young chef crouching in dark backyard shining flashlight on BBQ grill gauge reading EMPTY. Panicked face clutching glowing smartphone to ear. Atmospheric night lighting, suspenseful comedy."
  },
  {
    id: 5,
    title: "Operation Food Rescue",
    image: "scene5_family_food_rescue_1790682906438.jpg",
    narration: "The family rallied immediately! Maya raided the grocery market, Toby and Chef Luigi packed hot gourmet dishes, and Sarah secured bakery pies.",
    subtitle: "Operation Food Rescue: The family mobilizes to gather a gourmet feast!",
    cameraMotion: "pan_left",
    duration: 6,
    flowPrompt: "Pixar 3D animation style. Multi-panel rescue mission: sister buying roasted sides at deli, brother and Italian chef packing hot roasted meats, sister packing fresh warm pies. Cheerful determination, warm neon store lighting."
  },
  {
    id: 6,
    title: "The Rescue Arrives",
    image: "scene6_door_rescue_arrival_1790683539979.jpg",
    narration: "Just as Leo sat in tears of despair, the front door burst open with warm light, joyful laughter, and bags overflowing with steaming food!",
    subtitle: "Surprise! The front door opens with steaming boxes and tears of joy!",
    cameraMotion: "dolly_in",
    duration: 6,
    flowPrompt: "Pixar 3D animation style. Front door opens revealing three smiling siblings holding grocery bags and steaming roasted food containers. Host chef weeps tears of joy and disbelief. Warm amber doorway illumination, emotional Pixar reunion."
  },
  {
    id: 7,
    title: "The Candlelit Feast",
    image: "scene7_candlelit_family_feast_1790683561945.jpg",
    narration: "Lit by glowing candlelight, they shared the most unforgettable Thanksgiving feast ever. It wasn't about the oven—it was about being together.",
    subtitle: "The happiest Thanksgiving: A glorious candlelit feast shared with family!",
    cameraMotion: "slow_pullback",
    duration: 7,
    flowPrompt: "Pixar 3D animation style. Entire loving family gathered around a long candlelit rustic dinner table laughing, toasting, eating roast turkey and sides. Warm fireplace, glowing fairy lights, heartwarming holiday atmosphere."
  }
];

async function generateNarration(text, outputPath) {
  const dir = path.dirname(outputPath);
  const tempDir = path.join(dir, `tts_tmp_${Date.now()}_${Math.random().toString(36).substring(7)}`);
  fs.mkdirSync(tempDir, { recursive: true });

  const tts = new MsEdgeTTS();
  await tts.setMetadata('en-US-GuyNeural', OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);
  const res = await tts.toFile(tempDir, text);

  if (res && res.audioFilePath && fs.existsSync(res.audioFilePath)) {
    fs.copyFileSync(res.audioFilePath, outputPath);
    try { fs.rmSync(tempDir, { recursive: true, force: true }); } catch (e) {}
    return outputPath;
  }
  throw new Error('Failed to generate narration audio');
}

async function createSubtitleBanner(text, title, outputPath) {
  const width = 1920;
  const height = 1080;
  const escapeXml = (str) => str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const safeText = escapeXml(text);
  const safeTitle = escapeXml(title.toUpperCase());

  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.9" />
    </filter>
    <linearGradient id="badgeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FF5722" />
      <stop offset="100%" stop-color="#FF9800" />
    </linearGradient>
  </defs>

  <!-- Top Left Scene Tag -->
  <g filter="url(#shadow)">
    <rect x="70" y="60" width="340" height="54" rx="14" fill="#0D1117" opacity="0.85" stroke="#FFB74D" stroke-width="2" />
    <circle cx="102" cy="87" r="10" fill="#FF5722" />
    <text x="125" y="94" font-family="'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="900" fill="#FFF8E1" letter-spacing="1.5">🎬 SCENE: ${safeTitle}</text>
  </g>

  <!-- Bottom Subtitle Pill Banner -->
  <g filter="url(#shadow)">
    <rect x="140" y="930" width="1640" height="95" rx="28" fill="#0D1117" opacity="0.88" stroke="#FFE082" stroke-width="2.5" />
    <text x="960" y="990" text-anchor="middle" font-family="'Segoe UI', Roboto, sans-serif" font-size="34" font-weight="800" fill="#FFFFFF" stroke="#000000" stroke-width="3" paint-order="stroke fill">${safeText}</text>
  </g>
</svg>`;

  await sharp(Buffer.from(svg)).resize(width, height).png().toFile(outputPath);
  return outputPath;
}

// Generate animated clip with camera motion and subtitles
async function renderSceneClip(scene, inputImagePath, audioPath, subtitlePath, outputPath) {
  const fps = 30;
  const totalFrames = scene.duration * fps;
  const width = 1920;
  const height = 1080;

  // Cinematic camera movement formulas
  let zoomExpr = '';
  if (scene.cameraMotion === 'dolly_in') {
    zoomExpr = `zoompan=z='min(zoom+0.0008,1.15)':d=${totalFrames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
  } else if (scene.cameraMotion === 'pan_right') {
    zoomExpr = `zoompan=z='1.10':d=${totalFrames}:x='(iw-iw/zoom)*(on/${totalFrames})':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
  } else if (scene.cameraMotion === 'pan_left') {
    zoomExpr = `zoompan=z='1.10':d=${totalFrames}:x='(iw-iw/zoom)*(1-on/${totalFrames})':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
  } else if (scene.cameraMotion === 'push_tilt') {
    zoomExpr = `zoompan=z='min(zoom+0.0010,1.16)':d=${totalFrames}:x='iw/2-(iw/zoom/2)+sin(2*PI*on/${totalFrames})*25':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
  } else if (scene.cameraMotion === 'slow_pullback') {
    zoomExpr = `zoompan=z='if(lte(on,1),1.14,max(1.0,zoom-0.0007))':d=${totalFrames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
  } else {
    zoomExpr = `zoompan=z='min(zoom+0.0006,1.12)':d=${totalFrames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
  }

  return new Promise((resolve, reject) => {
    ffmpeg()
      .input(inputImagePath)
      .inputOptions(['-loop 1'])
      .input(subtitlePath)
      .inputOptions(['-loop 1'])
      .input(audioPath)
      .complexFilter([
        `[0:v]${zoomExpr}[cam]`,
        `[cam][1:v]overlay=0:0[v]`
      ])
      .outputOptions([
        '-map [v]',
        '-map 2:a',
        '-pix_fmt yuv420p',
        '-preset fast',
        '-crf 20',
        `-t ${scene.duration}`,
        '-c:v libx264',
        '-c:a aac'
      ])
      .save(outputPath)
      .on('end', () => resolve(outputPath))
      .on('error', (err) => reject(err));
  });
}

// Combine all clips with ffmpeg concat demuxer and mix gentle background music
async function combineClips(clipPaths, finalOutputPath) {
  const listFile = path.join(BASE_DIR, 'clips_concat.txt');
  const tempConcatPath = path.join(BASE_DIR, 'temp_raw_concat.mp4');
  const fileLines = clipPaths.map(p => `file '${p.replace(/\\/g, '/')}'`).join('\n');
  fs.writeFileSync(listFile, fileLines);

  // 1. Concat all scene clips
  await new Promise((resolve, reject) => {
    ffmpeg()
      .input(listFile)
      .inputOptions(['-f concat', '-safe 0'])
      .outputOptions(['-c copy'])
      .save(tempConcatPath)
      .on('end', () => {
        try { fs.unlinkSync(listFile); } catch(e) {}
        resolve(tempConcatPath);
      })
      .on('error', reject);
  });

  // 2. Mix with gentle ambient background music
  const bgMusicPath = path.join(AUDIO_DIR, 'bg_music.wav');
  if (fs.existsSync(bgMusicPath)) {
    console.log('   🎵 Mixing gentle holiday acoustic soundtrack under voiceover...');
    await new Promise((resolve, reject) => {
      ffmpeg()
        .input(tempConcatPath)
        .input(bgMusicPath)
        .complexFilter([
          '[1:a]volume=0.20[music]',
          '[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[a_out]'
        ])
        .outputOptions([
          '-map 0:v',
          '-map [a_out]',
          '-c:v copy',
          '-c:a aac',
          '-shortest'
        ])
        .save(finalOutputPath)
        .on('end', () => {
          try { fs.unlinkSync(tempConcatPath); } catch (e) {}
          resolve(finalOutputPath);
        })
        .on('error', (err) => {
          console.warn('   ⚠️ Audio mix notice, falling back to raw video:', err.message);
          fs.copyFileSync(tempConcatPath, finalOutputPath);
          try { fs.unlinkSync(tempConcatPath); } catch (e) {}
          resolve(finalOutputPath);
        });
    });
  } else {
    fs.copyFileSync(tempConcatPath, finalOutputPath);
    try { fs.unlinkSync(tempConcatPath); } catch (e) {}
  }

  return finalOutputPath;
}

async function main() {
  console.log('🎬 [Google Flow Storyboard Engine] Starting Video Production...');
  const clipPaths = [];

  for (let i = 0; i < scenes.length; i++) {
    const s = scenes[i];
    console.log(`\n▶️ Generating Scene ${s.id}/${scenes.length}: "${s.title}"...`);

    const imgPath = path.join(IMAGES_DIR, s.image);
    const audioPath = path.join(AUDIO_DIR, `narration_s${s.id}.mp3`);
    const subPath = path.join(CLIPS_DIR, `sub_overlay_s${s.id}.png`);
    const clipPath = path.join(CLIPS_DIR, `scene_${s.id}_clip.mp4`);

    // 1. Synthesize narration
    process.stdout.write('   🎙️ Generating AI voiceover narration...');
    await generateNarration(s.narration, audioPath);
    console.log(' Done.');

    // 2. Build subtitle graphic
    process.stdout.write('   🖼️ Creating cinematic subtitle banner...');
    await createSubtitleBanner(s.subtitle, s.title, subPath);
    console.log(' Done.');

    // 3. Render motion clip with dynamic camera
    process.stdout.write(`   🎥 Rendering 1080p motion video clip (${s.cameraMotion})...`);
    await renderSceneClip(s, imgPath, audioPath, subPath, clipPath);
    console.log(' Done.');

    // Clean up temporary subtitle overlay
    try { fs.unlinkSync(subPath); } catch (e) {}

    clipPaths.push(clipPath);
  }

  // Combine clips
  const finalVideoPath = path.join(BASE_DIR, 'final_holiday_film.mp4');
  console.log(`\n🎞️ Combining all ${clipPaths.length} scene clips into final movie: ${finalVideoPath}...`);
  await combineClips(clipPaths, finalVideoPath);
  console.log(`✅ Combined video created successfully!`);
  console.log(`📍 Path: ${finalVideoPath}`);

  // Save full Storyboard JSON
  const sbJsonPath = path.join(BASE_DIR, 'storyboard.json');
  fs.writeFileSync(sbJsonPath, JSON.stringify({
    title: "The Great Holiday Blackout: A Family Thanksgiving Rescue",
    style: "Disney Pixar 3D Animated Feature",
    totalScenes: scenes.length,
    aspectRatio: "16:9",
    resolution: "1920x1080",
    combinedVideoPath: finalVideoPath,
    scenes: scenes
  }, null, 2));
  console.log(`📜 Storyboard JSON saved: ${sbJsonPath}`);
}

main().catch(err => {
  console.error('❌ Pipeline failed:', err);
  process.exit(1);
});
