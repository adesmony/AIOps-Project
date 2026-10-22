export async function readAttachment(file) {
  if (file.size > 2 * 1024 * 1024) throw new Error('Attachments must be 2 MB or smaller.');
  const isImage = /\.(png|jpe?g)$/i.test(file.name) && /^image\/(png|jpeg)$/.test(file.type);
  if (isImage) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (!bytes.length) throw new Error('The screenshot is empty or unreadable.');
    if (bytes.length > 2 * 1024 * 1024) throw new Error('Attachments must be 2 MB or smaller.');
    let binary = '';
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return { name: file.name, content: '', isImage: true,
      dataUrl: `data:${file.type};base64,${btoa(binary)}` };
  }
  if (!/\.(json|csv|txt|log)$/i.test(file.name)) {
    throw new Error('Choose a JSON, CSV, TXT, LOG, JPEG or PNG report.');
  }
  let content;
  try {
    content = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer());
  } catch {
    throw new Error('The report must contain valid UTF-8 text.');
  }
  if (!content.trim() || content.includes('\0')) throw new Error('The report contains no valid text.');
  if (/\.json$/i.test(file.name)) {
    try {
      JSON.parse(content);
    } catch {
      throw new Error('The JSON report is malformed.');
    }
  }
  return { name: file.name, content: content.slice(0, 2500), isImage: false };
}