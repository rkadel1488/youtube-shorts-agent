const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');
const authManager = require('./auth');
const config = require('../../config');

/**
 * YouTube Data API v3 Uploader
 * Manages video uploads, metadata injection, COPPA compliance flags, and custom thumbnail attachment.
 */
class YouTubeUploader {
  /**
   * Uploads a video and thumbnail to YouTube
   * @param {Object} uploadPayload
   *   videoPath: Path to .mp4 master compilation
   *   thumbnailPath: Path to .jpg/.png thumbnail
   *   seo: SEO package { title, description, tags, madeForKids, categoryId }
   *   privacyStatus: 'private' | 'unlisted' | 'public' | 'scheduled'
   *   publishAt: Optional ISO timestamp for scheduled publishing
   *   onProgress: Callback function for upload progress
   */
  async uploadCompilation(uploadPayload) {
    const {
      videoPath,
      thumbnailPath,
      seo,
      privacyStatus = config.youtube.defaultPrivacy || 'unlisted',
      publishAt = null,
      onProgress = null
    } = uploadPayload;

    if (!fs.existsSync(videoPath)) {
      throw new Error(`Video file not found at: ${videoPath}`);
    }

    // 1. Get authenticated client
    const authClient = await authManager.getAuthClient();

    // If no credentials or not authorized, return dry-run simulation object
    if (!authClient) {
      console.warn('\n⚠️ [YouTubeUploader] YouTube channel not yet authenticated! Video rendered & saved locally.');
      console.warn('💡 To enable auto-uploading, run: "node bin/yt-agent.js auth" or configure .env\n');

      return {
        uploaded: false,
        simulated: true,
        videoId: `local_draft_${Date.now()}`,
        videoUrl: `file://${videoPath}`,
        privacyStatus: privacyStatus,
        message: 'Compilation rendered successfully. Ready for manual or automated upload.'
      };
    }

    const youtube = google.youtube({ version: 'v3', auth: authClient });

    // 2. Prepare Video Metadata
    const requestBody = {
      snippet: {
        title: seo.title.substring(0, 99), // Max 100 chars
        description: seo.description.substring(0, 4999), // Max 5000 chars
        tags: (seo.tags || []).map(t => String(t).replace(/&/g, 'and').replace(/[<>]/g, '').trim()).filter(Boolean),
        categoryId: seo.categoryId || '27', // Education
        defaultLanguage: 'en',
        defaultAudioLanguage: 'en'
      },
      status: {
        privacyStatus: publishAt ? 'private' : privacyStatus,
        selfDeclaredMadeForKids: true, // MANDATORY for COPPA compliance
        publishAt: publishAt || undefined
      }
    };

    const fileSize = fs.statSync(videoPath).size;

    // 3. Upload Video File
    console.log(`\n🚀 Uploading video to YouTube (${(fileSize / (1024 * 1024)).toFixed(1)} MB)...`);

    const videoResponse = await youtube.videos.insert(
      {
        part: ['snippet', 'status'],
        requestBody: requestBody,
        media: {
          body: fs.createReadStream(videoPath)
        }
      },
      {
        // Custom upload progress handling
        onUploadProgress: (evt) => {
          const progress = Math.round((evt.bytesRead / fileSize) * 100);
          if (onProgress) onProgress({ percent: progress, bytesRead: evt.bytesRead, totalBytes: fileSize });
        }
      }
    );

    const videoId = videoResponse.data.id;
    const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
    console.log(`✅ Video uploaded successfully! Video ID: ${videoId}`);
    console.log(`🔗 Watch URL: ${videoUrl}`);

    // 4. Upload Custom Thumbnail if provided
    if (thumbnailPath && fs.existsSync(thumbnailPath)) {
      try {
        console.log(`🖼️ Uploading custom 1280x720 thumbnail...`);
        await youtube.thumbnails.set({
          videoId: videoId,
          media: {
            mimeType: 'image/jpeg',
            body: fs.createReadStream(thumbnailPath)
          }
        });
        console.log(`✅ Custom thumbnail applied!`);
      } catch (thumbErr) {
        console.warn(`[YouTubeUploader] Thumbnail upload warning (channel may require phone verification for custom thumbnails): ${thumbErr.message}`);
      }
    }

    return {
      uploaded: true,
      videoId: videoId,
      videoUrl: videoUrl,
      title: seo.title,
      privacyStatus: privacyStatus,
      publishAt: publishAt
    };
  }
}

module.exports = new YouTubeUploader();
