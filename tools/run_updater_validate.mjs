import fs from 'node:fs';
import { webcrypto } from 'node:crypto';

const [updaterPath, packagePath, expectedVersion, expectedBuild, expectedChannel] = process.argv.slice(2);
if (!updaterPath || !packagePath) {
  console.error('usage: node run_updater_validate.mjs <updater.js> <package.json> <version> <build> <channel>');
  process.exit(2);
}

globalThis.window = {};
if (!globalThis.crypto) globalThis.crypto = webcrypto;
if (!globalThis.atob) globalThis.atob = s => Buffer.from(String(s), 'base64').toString('binary');
if (!globalThis.btoa) globalThis.btoa = s => Buffer.from(String(s), 'binary').toString('base64');

const updaterCode = fs.readFileSync(updaterPath, 'utf8');
(0, eval)(updaterCode);
const updater = globalThis.window?.VienaLocalUpdater;
if (!updater?.validatePackage) {
  console.error('Historical updater did not expose validatePackage');
  process.exit(3);
}

const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
try {
  const result = await updater.validatePackage(pkg, {
    expectedVersion,
    expectedBuild,
    expectedChannel
  });
  console.log(JSON.stringify({
    ok: true,
    version: result.version,
    build: result.build,
    channel: result.channel,
    mode: result.mode,
    files: result.files?.size
  }));
} catch (error) {
  console.error(String(error?.stack || error?.message || error));
  process.exit(1);
}
