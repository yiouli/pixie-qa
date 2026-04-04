"use strict";
/**
 * Barrel export for the web module.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.watchArtifacts = exports.getServerStatus = exports.openWebui = exports.runServer = exports.buildUrl = exports.buildManifest = exports.createApp = exports.SSEManager = void 0;
var app_1 = require("./app");
Object.defineProperty(exports, "SSEManager", { enumerable: true, get: function () { return app_1.SSEManager; } });
Object.defineProperty(exports, "createApp", { enumerable: true, get: function () { return app_1.createApp; } });
Object.defineProperty(exports, "buildManifest", { enumerable: true, get: function () { return app_1.buildManifest; } });
var server_1 = require("./server");
Object.defineProperty(exports, "buildUrl", { enumerable: true, get: function () { return server_1.buildUrl; } });
Object.defineProperty(exports, "runServer", { enumerable: true, get: function () { return server_1.runServer; } });
Object.defineProperty(exports, "openWebui", { enumerable: true, get: function () { return server_1.openWebui; } });
Object.defineProperty(exports, "getServerStatus", { enumerable: true, get: function () { return server_1.getServerStatus; } });
var watcher_1 = require("./watcher");
Object.defineProperty(exports, "watchArtifacts", { enumerable: true, get: function () { return watcher_1.watchArtifacts; } });
//# sourceMappingURL=index.js.map