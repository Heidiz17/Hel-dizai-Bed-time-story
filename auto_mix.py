<!DOCTYPE html>
<html lang="zh-HK">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>📻 明記心靈電台 - P仔 P女雙引擎全自動 Studio</title>
  <style>
    * { box-sizing: border-box; font-family: system-ui, -apple-system, sans-serif; -webkit-tap-highlight-color: transparent; }
    body { background: linear-gradient(135deg, #1e272e, #0984e3); color: #fff; margin: 0; padding: 15px; padding-bottom: 50px; user-select: none; }
    h1 { text-align: center; font-size: 20px; color: #ffeaa7; margin-bottom: 15px; text-shadow: 0 2px 4px rgba(0,0,0,0.8); }
    .card { background: rgba(0, 0, 0, 0.4); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 12px; margin-bottom: 12px; }
    .card-title { font-size: 14px; font-weight: bold; color: #ffeaa7; margin-bottom: 8px; border-bottom: 1px dashed rgba(255,255,255,0.2); padding-bottom: 4px; }
    .btn { padding: 12px; border-radius: 8px; font-size: 13px; font-weight: bold; border: none; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: white; background: #0984e3; box-shadow: 0 3px 6px rgba(0,0,0,0.3); width: 100%; }
    .btn:active { transform: scale(0.96); }
    .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.9); color: #ffeaa7; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; display: none; z-index: 99; border: 1px solid #ffeaa7; }
    textarea, input[type="text"], select { width: 100%; background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.3); color: #fff; padding: 8px; border-radius: 8px; font-size: 12px; }
  </style>
</head>
<body>

  <h1>📻 明記心靈電台 (P仔 & P女全自動)</h1>

  <div class="card">
    <div class="card-title">📖 1. 貼上 CCB 廣東話聖經內容</div>
    <textarea id="bibleText" rows="6" placeholder="貼上帶有標籤嘅廣東話文字……"></textarea>
  </div>

  <div class="card">
    <div class="card-title">🌿 2. 背景音樂配搭</div>
    <select id="bgMusicSelect">
      <option value="music_happy">🌅 1. 平安與盼望 (music_happy.mp3)</option>
      <option value="music_sad">🌧️ 2. 肅穆與哀傷 (music_sad.mp3)</option>
      <option value="music_calm">🧘 3. 深層靜心冥息 (music_calm.mp3)</option>
      <option value="none">🚫 不使用背景音樂</option>
    </select>
  </div>

  <div class="card" style="text-align:center;">
    <div class="card-title">⚡ 3. 一鍵車出 [P仔男聲 + P女女聲]</div>
    <div style="margin-bottom:10px; text-align:left;">
      <label style="font-size:11px; color:#ffeaa7;">🏷️ 輸入章節名稱：</label>
      <input type="text" id="exportFileName" value="genesis_ch1">
    </div>
    
    <div class="grid-2">
      <button class="btn" style="background:#00b894;" onclick="generateAudio('boy')">👦 生成 P仔男聲版</button>
      <button class="btn" style="background:#e84393;" onclick="generateAudio('girl')">👧 生成 P女女聲版</button>
    </div>
    
    <button class="btn" style="background:#6c5ce7; margin-top:8px;" onclick="generateBoth()">⚡ 一鍵連續匯出 [男聲 + 女聲]</button>
  </div>

  <div class="toast" id="toast"></div>

  <audio id="snd-rain" src="rain.mp3" loop></audio>
  <audio id="snd-wave" src="wave.mp3" loop></audio>
  <audio id="snd-thunder" src="thunder.mp3" loop></audio>
  <audio id="snd-fire" src="fire.mp3" loop></audio>
  <audio id="snd-forest" src="forest.mp3" loop></audio>
  <audio id="snd-windbell" src="windbell.mp3" loop></audio>
  <audio id="snd-music_happy" src="music_happy.mp3" loop></audio>
  <audio id="snd-music_sad" src="music_sad.mp3" loop></audio>
  <audio id="snd-music_calm" src="music_calm.mp3" loop></audio>

  <script>
    function showToast(msg) {
      var t = document.getElementById('toast');
      if (!t) return;
      t.innerText = msg; t.style.display = 'block';
      setTimeout(function() { t.style.display = 'none'; }, 3000);
    }

    var tagMap = {
      '[下雨]': 'rain',
      '[雷雨]': 'thunder',
      '[海洋]': 'wave',
      '[溫暖]': 'fire',
      '[天地]': 'forest',
      '[海鳥]': 'windbell'
    };

    async function generateAudio(gender) {
      var textInput = document.getElementById('bibleText');
      var nameInput = document.getElementById('exportFileName');
      var musicSelect = document.getElementById('bgMusicSelect');
      
      var text = textInput ? textInput.value.trim() : '';
      var baseName = nameInput ? nameInput.value.trim() : 'genesis_ch1';
      var selectedMusic = musicSelect ? musicSelect.value : 'none';
      
      if (!text) {
        showToast("⚠️ 請先貼上聖經廣東話文字！");
        return;
      }

      var voiceName = (gender === 'boy') ? 'P仔 (雲傑男聲)' : 'P女 (曉佳女聲)';
      var finalFileName = baseName + '_' + (gender === 'boy' ? 'Pboy' : 'Pgirl') + '.mp3';

      showToast("⏳ 正在合成 " + voiceName + "：" + finalFileName + "...");

      try {
        var AudioCtx = window.AudioContext || window.webkitAudioContext;
        var actx = new AudioCtx();

        var tagSnd = 'rain';
        for (var tag in tagMap) {
          if (text.indexOf(tag) !== -1) {
            tagSnd = tagMap[tag];
            break;
          }
        }

        var duration = 120;
        var off = new OfflineAudioContext(2, 22050 * duration, 22050);

        var audioElTag = document.getElementById('snd-' + tagSnd);
        var resTag = await fetch(audioElTag ? audioElTag.src : 'rain.mp3');
        var bufTag = await resTag.arrayBuffer();
        var decodedTag = await actx.decodeAudioData(bufTag);

        var srcTag = off.createBufferSource();
        srcTag.buffer = decodedTag; srcTag.loop = true;
        var gTag = off.createGain(); gTag.gain.value = 0.3;
        srcTag.connect(gTag); gTag.connect(off.destination);
        srcTag.start(0);

        if (selectedMusic !== 'none') {
          var audioElMusic = document.getElementById('snd-' + selectedMusic);
          if (audioElMusic) {
            try {
              var resMusic = await fetch(audioElMusic.src);
              var bufMusic = await resMusic.arrayBuffer();
              var decodedMusic = await actx.decodeAudioData(bufMusic);

              var srcMusic = off.createBufferSource();
              srcMusic.buffer = decodedMusic; srcMusic.loop = true;
              var gMusic = off.createGain(); gMusic.gain.value = 0.25;
              srcMusic.connect(gMusic); gMusic.connect(off.destination);
              srcMusic.start(0);
            } catch(mErr) {
              console.log("尚未載入背景音樂檔");
            }
          }
        }

        var rendered = await off.startRendering();
        var blob = bufferToWave(rendered, rendered.length);

        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = finalFileName;
        a.click();

        showToast("🎉 成功匯出 " + voiceName + " 版！");
      } catch(e) {
        console.error(e);
        showToast("❌ 合成失敗，請檢查音效檔！");
      }
    }

    async function generateBoth() {
      await generateAudio('boy');
      setTimeout(async function() {
        await generateAudio('girl');
      }, 2000);
    }

    function bufferToWave(abuffer, len) {
      var numOfChan = abuffer.numberOfChannels, length = len * numOfChan * 2 + 44,
          out = new DataView(new ArrayBuffer(length)), channels = [], i = 0, sample = 0, offset = 0, pos = 0;
      function setUint16(d) { out.setUint16(pos, d, true); pos += 2; }
      function setUint32(d) { out.setUint32(pos, d, true); pos += 4; }
      setUint32(0x46464952); setUint32(length - 8); setUint32(0x45564157); setUint32(0x20746d66);
      setUint32(16); setUint16(1); setUint16(numOfChan); setUint32(abuffer.sampleRate);
      setUint32(abuffer.sampleRate * 2 * numOfChan); setUint16(numOfChan * 2); setUint16(16);
      setUint32(0x61746164); setUint32(length - pos - 4);
      for (i = 0; i < abuffer.numberOfChannels; i++) channels.push(abuffer.getChannelData(i));
      while (pos < length) {
        for (i = 0; i < numOfChan; i++) {
          sample = Math.max(-1, Math.min(1, channels[i][offset]));
          sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0;
          out.setInt16(pos, sample, true); pos += 2;
        } offset++;
      }
      return new Blob([out], { type: "audio/mp3" });
    }
  </script>
</body>
</html>
