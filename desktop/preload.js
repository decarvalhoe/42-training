/**
 * Preload script — runs in renderer context before web content loads.
 * Exposes a minimal API surface via contextBridge.
 */
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("desktop", {
  platform: process.platform,
  isDesktop: true,
});
