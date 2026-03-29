/**
 * Electron preload script.
 *
 * Exposes a minimal API to the renderer via contextBridge.
 * Keeps contextIsolation enabled for security.
 */

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("desktop", {
  platform: process.platform,
  isElectron: true,
});
