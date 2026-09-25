const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');
const http = require('http');
const url = require('url');
const config = require('../../config');

/**
 * YouTube OAuth2 Authentication Manager
 * Automatically supports:
 * - Existing client_secrets.json & youtube_token.json files
 * - GitHub Secrets (YOUTUBE_CLIENT_SECRETS & YOUTUBE_TOKEN environment variables)
 * - Standard .env YOUTUBE_CLIENT_ID & YOUTUBE_CLIENT_SECRET
 */
class YouTubeAuth {
  constructor() {
    this.tokenPath = config.youtube.tokenPath;
    this.credentialsDir = path.dirname(this.tokenPath);
    this.scopes = [
      'https://www.googleapis.com/auth/youtube.upload',
      'https://www.googleapis.com/auth/youtube',
      'https://www.googleapis.com/auth/youtube.force-ssl'
    ];
  }

  /**
   * Returns an authorized OAuth2 client
   */
  async getAuthClient() {
    const oauth2Client = this._createOAuth2Client();
    if (!oauth2Client) return null;

    // 1. Check if tokens are passed directly via environment variable (e.g. GitHub Actions)
    if (process.env.YOUTUBE_TOKEN) {
      try {
        const tokens = JSON.parse(process.env.YOUTUBE_TOKEN);
        oauth2Client.setCredentials(tokens);
        return oauth2Client;
      } catch (e) {}
    }

    // 2. Check all possible token file paths (root youtube_token.json or credentials/youtube_tokens.json)
    const tokenCandidates = [
      path.join(config.paths.root, 'youtube_token.json'),
      path.join(config.paths.credentials, 'youtube_token.json'),
      this.tokenPath
    ];

    for (const tokenFile of tokenCandidates) {
      if (fs.existsSync(tokenFile)) {
        try {
          const tokens = JSON.parse(fs.readFileSync(tokenFile, 'utf8'));
          oauth2Client.setCredentials(tokens);
          return oauth2Client;
        } catch (err) {
          console.warn(`[YouTubeAuth] Corrupted token file at ${tokenFile}: ${err.message}`);
        }
      }
    }

    return null; // Not authenticated yet
  }

  /**
   * Generates authentication URL for user to log in
   */
  getAuthUrl() {
    const oauth2Client = this._createOAuth2Client();
    if (!oauth2Client) {
      throw new Error('Cannot generate auth URL: Missing client_secrets.json or client ID/secret.');
    }
    return oauth2Client.generateAuthUrl({
      access_type: 'offline',
      prompt: 'consent',
      scope: this.scopes
    });
  }

  /**
   * Exchanges authorization code for tokens and saves to disk
   */
  async saveAuthCode(code) {
    const oauth2Client = this._createOAuth2Client();
    const { tokens } = await oauth2Client.getToken(code);
    oauth2Client.setCredentials(tokens);

    // Save in both locations for maximum compatibility
    const rootTokenFile = path.join(config.paths.root, 'youtube_token.json');
    fs.writeFileSync(rootTokenFile, JSON.stringify(tokens, null, 2));

    if (!fs.existsSync(this.credentialsDir)) {
      fs.mkdirSync(this.credentialsDir, { recursive: true });
    }
    fs.writeFileSync(this.tokenPath, JSON.stringify(tokens, null, 2));

    return tokens;
  }

  /**
   * Starts a local temporary HTTP listener to automatically capture OAuth code from browser redirect
   */
  startLocalAuthServer(port = 3000) {
    return new Promise((resolve, reject) => {
      const server = http.createServer(async (req, res) => {
        try {
          const parsedUrl = url.parse(req.url, true);
          if (parsedUrl.pathname === '/oauth2callback' && parsedUrl.query.code) {
            const code = parsedUrl.query.code;
            await this.saveAuthCode(code);

            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(`
              <div style="font-family: Arial; text-align: center; padding: 40px; background: #E8F5E9;">
                <h1 style="color: #2E7D32;">🎉 YouTube Authentication Successful!</h1>
                <p>Your tokens have been saved to <b>youtube_token.json</b>. You can close this window and return to your terminal.</p>
              </div>
            `);

            server.close();
            resolve(true);
          } else {
            res.writeHead(400);
            res.end('Missing authorization code');
          }
        } catch (err) {
          res.writeHead(500);
          res.end(`Auth error: ${err.message}`);
          server.close();
          reject(err);
        }
      });

      server.listen(port, () => {
        const authUrl = this.getAuthUrl();
        console.log(`\n🔗 Please authorize your YouTube channel by visiting:\n${authUrl}\n`);
      });

      server.on('error', reject);
    });
  }

  /**
   * Resolves OAuth2 client from client_secrets.json, env vars, or config
   */
  _createOAuth2Client() {
    let clientId = config.youtube.clientId || process.env.YOUTUBE_CLIENT_ID;
    let clientSecret = config.youtube.clientSecret || process.env.YOUTUBE_CLIENT_SECRET;
    let redirectUri = config.youtube.redirectUri || 'http://localhost:3000/oauth2callback';

    // 1. Check if YOUTUBE_CLIENT_SECRETS is provided as an env string (GitHub Actions)
    if (process.env.YOUTUBE_CLIENT_SECRETS) {
      try {
        const parsed = JSON.parse(process.env.YOUTUBE_CLIENT_SECRETS);
        const creds = parsed.installed || parsed.web || parsed;
        clientId = creds.client_id || clientId;
        clientSecret = creds.client_secret || clientSecret;
        if (creds.redirect_uris && creds.redirect_uris.length > 0) {
          redirectUri = creds.redirect_uris[0];
        }
      } catch (e) {}
    }

    // 2. Check if client_secrets.json exists on disk
    const secretCandidates = [
      path.join(config.paths.root, 'client_secrets.json'),
      path.join(config.paths.credentials, 'client_secrets.json')
    ];

    for (const secretFile of secretCandidates) {
      if (fs.existsSync(secretFile)) {
        try {
          const parsed = JSON.parse(fs.readFileSync(secretFile, 'utf8'));
          const creds = parsed.installed || parsed.web || parsed;
          clientId = creds.client_id || clientId;
          clientSecret = creds.client_secret || clientSecret;
          if (creds.redirect_uris && creds.redirect_uris.length > 0) {
            redirectUri = creds.redirect_uris[0];
          }
          break;
        } catch (e) {}
      }
    }

    if (!clientId || !clientSecret) {
      return null;
    }

    return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
  }
}

module.exports = new YouTubeAuth();
