// 01_extract_feishu.js
// 在目标飞书多维表格页面内执行（浏览器控制台 / CDP Runtime.evaluate）。
// 作用：直接复用页面自身的数据接口取回全部记录，解压后 POST 到本地接收服务落盘。
//
// 为什么要这么绕：该接口需要页面会话 Cookie（直接 curl 返回 "Login Required"），
// 而飞书返回的 data.records 字段是 base64(gzip(json))，必须在页面内解压。
//
// 前置：先跑 `python3 src/00_local_receiver.py 8899`

(async () => {
  const HOST = 'https://<你的租户>.feishu.cn';
  const APP_TOKEN = '<base token>';      // 形如 GtSxxxxxxxxxxxxxxxx
  const TABLE_ID = '<table id>';         // 形如 tblXXXXXXXXXXXX
  const VIEW_ID = '<view id>';           // 形如 vewXXXXXXXXXXXX
  const RECV = 'http://127.0.0.1:8899';  // 本地接收服务

  const base = `${HOST}/space/api/v1/bitable/${APP_TOKEN}`;

  // 1) 字段元数据（字段名 + 单选/多选选项标签）
  const cvUrl = `${base}/clientvars?tableID=${TABLE_ID}&viewID=${VIEW_ID}`
    + `&recordLimit=200&ondemandLimit=200&needBase=true&viewLazyLoad=true`
    + `&ondemandVer=2&openType=0&noMissCS=true&optimizationFlag=1&removeFmlExtra=true`;
  const cvResp = await fetch(cvUrl, { credentials: 'include' });
  const cvText = await cvResp.text();
  await fetch(`${RECV}/clientvars.json`, { method: 'POST', body: cvText, headers: { 'Content-Type': 'text/plain' } });

  // 2) 分页取记录（limit 上限 3000，offset 步进）
  const offsets = [0, 3000, 6000];
  const stat = [];
  for (const off of offsets) {
    const url = `${base}/records?tableId=${TABLE_ID}&viewId=${VIEW_ID}`
      + `&offset=${off}&limit=3000&removeFmlExtra=true`;
    const resp = await fetch(url, { credentials: 'include' });
    const j = await resp.json();
    const d = j.data || {};

    let text;
    if (typeof d.records === 'string') {
      // base64 -> Uint8Array -> gunzip -> JSON 文本
      const bin = atob(d.records);
      const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const stream = new Blob([u8]).stream().pipeThrough(new DecompressionStream('gzip'));
      text = await new Response(stream).text();
    } else {
      text = JSON.stringify(d);
    }

    await fetch(`${RECV}/records_${off}.json`, { method: 'POST', body: text, headers: { 'Content-Type': 'text/plain' } });
    let n = 0;
    try { n = Object.keys(JSON.parse(text).recordMap || {}).length; } catch (e) {}
    stat.push({ offset: off, code: j.code, bytes: text.length, records: n });
  }
  return JSON.stringify(stat);
})();
