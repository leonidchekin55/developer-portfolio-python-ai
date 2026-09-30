import assert from 'node:assert/strict';
const base = new URL(process.argv[2] || 'https://leonid-portfolio.onrender.com/');
const pages = ['/', '/en.html', '/pulseboard.html', '/ai-engineer-tour.html', '/privacy.html', '/terms.html', '/privacy-en.html', '/terms-en.html'];
const checked = new Set();
for (const path of pages) {
  const response = await fetch(new URL(path, base), { redirect: 'follow', signal: AbortSignal.timeout(60000) });
  assert.equal(response.status, 200, `${path}: HTTP ${response.status}`);
  const html = await response.text();
  assert.match(html, /<html[^>]+lang=/i, `${path}: missing document language`);
  assert.match(html, /<meta[^>]+name=["']viewport/i, `${path}: missing mobile viewport`);
  console.log('PASS', path, response.status, response.headers.get('content-type'));
  if (path === '/ai-engineer-tour.html') {
    for (const asset of ['/assets/ai-engineer-portfolio-tour.mp4', '/assets/ai-engineer-portfolio-tour.srt', '/assets/ai-engineer-portfolio-tour-poster.png']) checked.add(asset);
    assert.match(html, /kind="captions"/, 'tour: captions track missing');
  }
  if (path === '/pulseboard.html') {
    const script = html.match(/<script[^>]+src="([^"]*pulseboard-ui\.js[^"]*)/);
    assert.ok(script, 'pulseboard: UI script missing');
    const scriptUrl = new URL(script[1], base);
    const scriptResponse = await fetch(scriptUrl, { signal: AbortSignal.timeout(60000) });
    assert.equal(scriptResponse.status, 200, 'pulseboard: UI script failed to load');
    assert.match(await scriptResponse.text(), /sessionStorage/, 'pulseboard: session token should not persist across browser restarts');
  }
  if (path === '/') for (const resume of ['Leonid_Chekin_Resume_AI_RAG_ATS.pdf', 'Leonid_Chekin_Resume_Backend_ATS.pdf', 'Leonid_Chekin_Resume_English_ATS.pdf']) checked.add(`/downloads/${resume}`);
}
for (const path of checked) {
  const response = await fetch(new URL(path, base), { method: 'HEAD', redirect: 'follow', signal: AbortSignal.timeout(60000) });
  assert.equal(response.status, 200, `${path}: HTTP ${response.status}`);
  console.log('PASS linked asset', path, response.status);
}
console.log('Website smoke checks passed.');
