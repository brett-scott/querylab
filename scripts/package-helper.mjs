import { createHash } from 'node:crypto';
import { deflateRawSync } from 'node:zlib';
import { lstat, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = join(root, 'frontend', 'public', 'downloads');
const version = '0.4.1';
const filename = 'querylab-helper-windows.zip';
const prefix = 'QueryLab-Helper/';

// Deliberate allowlist: runtime source, launcher and configuration templates.
// Never copy a checkout, environment file, Docker volume or generated state.
const sources = [
  ['backend/Dockerfile', 'backend/Dockerfile'],
  ['backend/requirements.txt', 'backend/requirements.txt'],
  ['backend/.dockerignore', 'backend/.dockerignore'],
  ['helper.env.example', 'helper.env.example'],
  ['scripts/setup-helper.ps1', 'scripts/setup-helper.ps1'],
  ['scripts/start-helper.ps1', 'scripts/start-helper.ps1'],
  ['scripts/show-helper-code.ps1', 'scripts/show-helper-code.ps1'],
  ['distribution/windows/launch-helper.ps1', 'scripts/launch-helper.ps1'],
  ['distribution/windows/Start-QueryLab-Helper.cmd', 'Start-QueryLab-Helper.cmd'],
  ['distribution/windows/README.txt', 'README.txt'],
];

async function pythonFiles(folder) {
  const files = [];
  for (const entry of await readdir(folder, { withFileTypes: true })) {
    if (entry.isSymbolicLink()) throw new Error('Symbolic links are not allowed in helper runtime source.');
    if (entry.isDirectory() && entry.name !== '__pycache__') files.push(...await pythonFiles(join(folder, entry.name)));
    else if (entry.isFile() && entry.name.endsWith('.py')) files.push(relative(root, join(folder, entry.name)).replaceAll('\\', '/'));
  }
  return files.sort();
}

function crc32(buffer) {
  let checksum = 0xffffffff;
  for (const byte of buffer) {
    checksum ^= byte;
    for (let bit = 0; bit < 8; bit++) checksum = (checksum >>> 1) ^ ((checksum & 1) ? 0xedb88320 : 0);
  }
  return (checksum ^ 0xffffffff) >>> 0;
}

// Small deterministic ZIP writer using standard DEFLATE/CRC32, no runtime or
// installation dependency. The archive is independently checked with Python's
// zipfile and Windows Expand-Archive in release verification.
function zip(entries) {
  const local = [], central = [];
  let offset = 0;
  for (const [path, content] of entries) {
    const name = Buffer.from(prefix + path);
    const compressed = deflateRawSync(content);
    const checksum = crc32(content);
    const header = Buffer.alloc(30);
    header.writeUInt32LE(0x04034b50);
    header.writeUInt16LE(20, 4);
    header.writeUInt16LE(0x800, 6); // UTF-8 names.
    header.writeUInt16LE(8, 8);
    header.writeUInt16LE(33, 12); // Fixed DOS date 1980-01-01.
    header.writeUInt32LE(checksum, 14);
    header.writeUInt32LE(compressed.length, 18);
    header.writeUInt32LE(content.length, 22);
    header.writeUInt16LE(name.length, 26);
    const directory = Buffer.alloc(46);
    directory.writeUInt32LE(0x02014b50);
    directory.writeUInt16LE(20, 4);
    directory.writeUInt16LE(20, 6);
    directory.writeUInt16LE(0x800, 8);
    directory.writeUInt16LE(8, 10);
    directory.writeUInt16LE(33, 14);
    directory.writeUInt32LE(checksum, 16);
    directory.writeUInt32LE(compressed.length, 20);
    directory.writeUInt32LE(content.length, 24);
    directory.writeUInt16LE(name.length, 28);
    directory.writeUInt32LE(offset, 42);
    local.push(header, name, compressed);
    central.push(directory, name);
    offset += header.length + name.length + compressed.length;
  }
  const index = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(index.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...local, index, end]);
}

async function packageHelper() {
  for (const file of await pythonFiles(join(root, 'backend', 'app'))) sources.push([file, file]);
  const entries = [];
  for (const [source, destination] of sources) {
    if (!(await lstat(join(root, source))).isFile()) throw new Error(`Expected a regular source file: ${source}`);
    let content = await readFile(join(root, source));
    // PowerShell 5.1 reads UTF-8 without BOM as ANSI. Ship a BOM for scripts;
    // Windows command launchers get conventional CRLF line endings.
    if (destination.endsWith('.ps1')) content = Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(content.toString('utf8').replace(/^\uFEFF/, '').replace(/\r?\n/g, '\r\n'))]);
    if (destination.endsWith('.cmd')) content = Buffer.from(content.toString('utf8').replace(/\r?\n/g, '\r\n'));
    entries.push([destination, content]);
  }
  const compose = (await readFile(join(root, 'compose.helper.yaml'), 'utf8')).replaceAll('\r\n', '\n');
  const website = compose.indexOf('\n  website:\n');
  const networks = compose.indexOf('\nnetworks:\n', website);
  if (website === -1 || networks === -1) throw new Error('Helper Compose layout changed; review the standalone package service selection.');
  const standalone = (compose.slice(0, website) + compose.slice(networks)).replace(/^name: .*$/m, 'name: querylab-helper-installed');
  entries.push(['compose.helper.yaml', Buffer.from(standalone)]);
  entries.push(['VERSION.txt', Buffer.from(version + '\n')]);
  entries.sort(([a], [b]) => a.localeCompare(b, 'en'));
  const archive = zip(entries);
  const manifest = {
    version, filename, platform: 'windows', requires: ['Docker Desktop'],
    bytes: archive.length, sha256: createHash('sha256').update(archive).digest('hex'),
    launcher: 'QueryLab-Helper/Start-QueryLab-Helper.cmd',
    files: entries.map(([path]) => prefix + path),
  };
  await mkdir(output, { recursive: true });
  await writeFile(join(output, filename), archive);
  await writeFile(join(output, 'querylab-helper-windows.json'), JSON.stringify(manifest, null, 2) + '\n');
  process.stdout.write(`Packaged Windows helper ${version}: ${entries.length} files, ${archive.length} bytes. No local configuration included.\n`);
}

await packageHelper();
