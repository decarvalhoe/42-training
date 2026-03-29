/**
 * electron-builder afterSign hook for Apple notarization.
 *
 * Requires environment variables:
 *   APPLE_ID          — Apple Developer account email
 *   APPLE_APP_PASSWORD — App-specific password (appleid.apple.com)
 *   APPLE_TEAM_ID     — 10-character Team ID
 *
 * Skipped when these variables are absent (local development builds).
 */

const { notarize } = require("@electron/notarize");

module.exports = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;

  if (electronPlatformName !== "darwin") return;

  const appleId = process.env.APPLE_ID;
  const applePassword = process.env.APPLE_APP_PASSWORD;
  const teamId = process.env.APPLE_TEAM_ID;

  if (!appleId || !applePassword || !teamId) {
    console.log("[notarize] Skipping — APPLE_ID, APPLE_APP_PASSWORD, or APPLE_TEAM_ID not set");
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  console.log(`[notarize] Submitting ${appPath} to Apple...`);

  await notarize({
    appPath,
    appleId,
    appleIdPassword: applePassword,
    teamId,
  });

  console.log("[notarize] Done");
};
