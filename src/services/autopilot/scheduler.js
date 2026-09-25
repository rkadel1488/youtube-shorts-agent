const cron = require('node-cron');
const fs = require('fs');
const path = require('path');
const config = require('../../config');
const orchestrator = require('../../orchestrator');

/**
 * Autonomous Autopilot Scheduler
 * Executes scheduled cron jobs that automatically generate, compile, and publish nursery rhymes.
 */
class AutopilotScheduler {
  constructor() {
    this.cronTask = null;
    this.logFile = path.join(config.paths.root, 'logs', 'autopilot.log');
    this.ensureLogDir();
  }

  ensureLogDir() {
    const dir = path.dirname(this.logFile);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  }

  log(message) {
    const timestamp = new Date().toISOString();
    const line = `[${timestamp}] ${message}\n`;
    console.log(line.trim());
    try {
      fs.appendFileSync(this.logFile, line);
    } catch (e) {}
  }

  /**
   * Starts the cron scheduler
   * @param {string} cronExpression Standard 5-field cron string
   * @param {Object} options { songCount, autoPublish, privacyStatus }
   */
  start(cronExpression = config.autopilot.schedule, options = {}) {
    if (this.cronTask) {
      this.cronTask.stop();
    }

    const {
      songCount = 5,
      autoPublish = config.autopilot.autoPublish || false,
      privacyStatus = config.youtube.defaultPrivacy || 'unlisted'
    } = options;

    this.log(`🚀 Autopilot Scheduler initialized!`);
    this.log(`📅 Schedule Expression: "${cronExpression}"`);
    this.log(`⚙️ Settings: ${songCount} songs per compilation, autoPublish=${autoPublish}, privacy=${privacyStatus}`);

    const themesRotation = ['vehicles', 'animals', 'dinosaurs', 'colors', 'counting', 'bedtime'];
    let rotationIndex = 0;

    this.cronTask = cron.schedule(cronExpression, async () => {
      const currentTheme = themesRotation[rotationIndex % themesRotation.length];
      rotationIndex++;

      this.log(`\n⏰ Autopilot Triggered! Target Theme: "${currentTheme.toUpperCase()}"`);

      try {
        const result = await orchestrator.generateCompilation({
          songCount: songCount,
          themeCategory: currentTheme,
          autoUpload: autoPublish,
          privacyStatus: privacyStatus
        });

        this.log(`✅ Autopilot Run Completed! Compilation ID: ${result.id}`);
        this.log(`📹 Video File: ${result.masterVideoPath}`);
        this.log(`🖼️ Thumbnail: ${result.thumbnailPath}`);
        if (result.youtube?.videoUrl) {
          this.log(`🔗 YouTube URL: ${result.youtube.videoUrl}`);
        }
      } catch (err) {
        this.log(`❌ Autopilot Run Failed: ${err.message}\n${err.stack}`);
      }
    });

    this.log(`⏳ Autopilot is now actively running in the background. Press Ctrl+C to stop.\n`);
    return this.cronTask;
  }

  stop() {
    if (this.cronTask) {
      this.cronTask.stop();
      this.log('🛑 Autopilot Scheduler stopped.');
    }
  }
}

module.exports = new AutopilotScheduler();
