// Install the locked test tools outside cloud-synced node_modules directories.
import { mkdtempSync, copyFileSync, realpathSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, delimiter } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const frontend = join(root, 'front_end');
const npm = process.env.npm_execpath;
if (!npm) {
  console.error('Run through npm: npm --prefix front_end test');
  process.exit(1);
}

const tempRoot = realpathSync(tmpdir());
const tools = mkdtempSync(join(tempRoot, 'cosmic-frontend-'));
let status = 1;
try {
  copyFileSync(join(frontend, 'package.json'), join(tools, 'package.json'));
  copyFileSync(join(frontend, 'package-lock.json'), join(tools, 'package-lock.json'));
  console.log('Installing locked frontend test tools outside the checkout.');
  const install = spawnSync(process.execPath, [npm, 'ci', '--prefix', tools,
    '--ignore-scripts', '--no-audit', '--no-fund'], { stdio: 'inherit' });
  if (install.error) throw install.error;
  status = install.status ?? 1;
  if (status === 0) {
    const result = spawnSync(process.execPath, [join(tools, 'node_modules/jest/bin/jest.js'),
      '--config', join(frontend, 'package.json'), '--forceExit', ...process.argv.slice(2)], {
      // Jest's import-local lookup must start in the isolated installation.
      cwd: tools,
      stdio: 'inherit',
      env: { ...process.env, NODE_PATH: [join(tools, 'node_modules'),
        process.env.NODE_PATH].filter(Boolean).join(delimiter) },
    });
    if (result.error) throw result.error;
    status = result.status ?? 1;
  }
} finally {
  // Only remove the unique directory this invocation created beneath tempRoot.
  const resolved = realpathSync(tools);
  if (dirname(resolved) !== tempRoot) throw new Error('Unexpected temporary directory');
  rmSync(resolved, { recursive: true, force: true });
}
process.exitCode = status;
