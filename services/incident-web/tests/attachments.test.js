import { describe, expect, it } from 'vitest';
import { readAttachment } from '../src/attachments.js';

function file(name, content, extra = {}) {
  const encoded = new TextEncoder().encode(content);
  return { name, size: encoded.length, type: 'text/plain',
    arrayBuffer: async () => encoded.buffer, ...extra };
}

describe('report attachments', () => {
  it('preserves text context and bounds it', async () => {
    expect(await readAttachment(file('error.log', 'Timeout '.repeat(1000))))
      .toMatchObject({ name: 'error.log', isImage: false });
    expect((await readAttachment(file('error.log', 'a'.repeat(3000)))).content).toHaveLength(2500);
  });

  it('rejects malformed JSON, empty, binary and oversized files', async () => {
    await expect(readAttachment(file('bad.json', '{broken'))).rejects.toThrow('malformed');
    await expect(readAttachment(file('empty.log', ' '))).rejects.toThrow('no valid text');
    await expect(readAttachment(file('binary.txt', '\0'))).rejects.toThrow('no valid text');
    await expect(readAttachment(file('bad.exe', 'binary'))).rejects.toThrow('Choose');
    await expect(readAttachment(file('large.log', 'ok', { size: 3000000 }))).rejects.toThrow('2 MB');
    await expect(readAttachment(file('bad.txt', '', {
      arrayBuffer: async () => new Uint8Array([255]).buffer,
    }))).rejects.toThrow('UTF-8');
  });

  it('keeps valid JSON, CSV and image behavior', async () => {
    expect((await readAttachment(file('report.json', '{"error":"timeout"}'))).content).toContain('timeout');
    expect((await readAttachment(file('report.csv', 'code,message\n42,timeout'))).content).toContain('42');
    expect(await readAttachment(file('screen.png', 'png-bytes', { type: 'image/png' })))
      .toMatchObject({ isImage: true, dataUrl: 'data:image/png;base64,cG5nLWJ5dGVz' });
    await expect(readAttachment(file('empty.png', '', { type: 'image/png' })))
      .rejects.toThrow('empty or unreadable');
    await expect(readAttachment(file('screen.svg', '<svg/>', { type: 'image/svg+xml' })))
      .rejects.toThrow('Choose');
  });
});