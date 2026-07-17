const wsUrl = `ws://${window.location.host}/ws`;
let ws = null;
let tree = null;
let active = false;

let settings = {
    device_id: null,
    wpm: 20,
    gain: parseFloat(localStorage.getItem('decoder_gain') || '2.0'),
    squelch: parseFloat(localStorage.getItem('decoder_squelch') || '0.08'),
};

function init() {
    tree = new MorseTree('morse-tree');
    connectWebSocket();
    loadSettings();
    fetchDevices();
    bindEvents();
    const ro = new ResizeObserver(() => tree.initDebounced());
    ro.observe(document.getElementById('tree-container'));
    tree.init();
}

function loadSettings() {
    document.getElementById('wpm').value = settings.wpm;
    document.getElementById('wpm-value').textContent = settings.wpm;
    document.getElementById('wpm-display').textContent = settings.wpm;
    document.getElementById('gain').value = settings.gain;
    document.getElementById('gain-value').textContent = settings.gain.toFixed(1);
    document.getElementById('squelch').value = Math.round(settings.squelch * 100);
    document.getElementById('squelch-value').textContent = Math.round(settings.squelch * 100);
}

function bindEvents() {
    document.getElementById('btn-start').addEventListener('click', startDecoding);
    document.getElementById('btn-stop').addEventListener('click', stopDecoding);
    document.getElementById('btn-settings').addEventListener('click', () => {
        document.getElementById('settings-panel').classList.remove('hidden');
        document.getElementById('settings-panel').classList.add('flex');
    });
    document.getElementById('btn-close-settings').addEventListener('click', closeSettings);
    document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
    document.getElementById('btn-clear').addEventListener('click', clearAll);
    document.getElementById('wpm').addEventListener('input', e => document.getElementById('wpm-value').textContent = e.target.value);
    document.getElementById('gain').addEventListener('input', e => document.getElementById('gain-value').textContent = parseFloat(e.target.value).toFixed(1));
    document.getElementById('squelch').addEventListener('input', e => document.getElementById('squelch-value').textContent = e.target.value);
}

function connectWebSocket() {
    if (ws) ws.close();
    ws = new WebSocket(wsUrl);
    ws.onopen = () => setStatus('已连接', 'bg-green-100 text-green-700');
    ws.onmessage = e => handleMessage(JSON.parse(e.data));
    ws.onclose = () => {
        setStatus('已断开', 'bg-gray-100 text-gray-500');
        active = false;
        updateButtons();
        setTimeout(connectWebSocket, 3000);
    };
    ws.onerror = () => ws.close();
}

function setStatus(label, cls) {
    document.getElementById('status-badge').textContent = label;
    document.getElementById('status-badge').className = `text-xs px-2 py-1 rounded-full ${cls}`;
}

function handleMessage(msg) {
    switch (msg.type) {
        case 'decoded_letter':
            if (tree) tree.goToLetter(msg.letter);
            document.getElementById('current-letter').textContent = msg.letter;
            appendLetter(msg.letter);
            break;
        case 'decoded_word':
            tree.resetPath();
            document.getElementById('current-letter').textContent = '-';
            if (msg.full_text) document.getElementById('decoded-text').textContent = msg.full_text;
            break;
        case 'signal_level':
            document.getElementById('signal-bar').style.width = `${msg.value * 100}%`;
            break;
        case 'wpm':
            document.getElementById('wpm-display').textContent = msg.value;
            break;
        case 'status':
            if (msg.state === 'listening') {
                setStatus('正在监听', 'bg-green-100 text-green-700');
                active = true;
            } else if (msg.state === 'stopped') {
                setStatus('已停止', 'bg-gray-100 text-gray-500');
                active = false;
            } else if (msg.state === 'already_running') {
                setStatus('已在运行', 'bg-yellow-100 text-yellow-700');
            }
            updateButtons();
            break;
    }
}

function appendLetter(letter) {
    const el = document.getElementById('decoded-text');
    let t = el.textContent;
    if (t === '—') t = '';
    el.textContent = t + letter;
}

function clearAll() {
    document.getElementById('decoded-text').textContent = '—';
}

function startDecoding() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    document.getElementById('decoded-text').textContent = '—';
    tree.resetPath();
    document.getElementById('current-letter').textContent = '-';
    ws.send(JSON.stringify({
        type: 'start',
        device_id: settings.device_id,
        wpm: settings.wpm,
        gain: settings.gain,
        squelch: settings.squelch,
    }));
}

function stopDecoding() {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }));
    tree.resetPath();
    active = false;
    updateButtons();
}

function updateButtons() {
    document.getElementById('btn-start').disabled = active;
    document.getElementById('btn-stop').disabled = !active;
}

function closeSettings() {
    document.getElementById('settings-panel').classList.add('hidden');
    document.getElementById('settings-panel').classList.remove('flex');
}

function saveSettings() {
    settings.wpm = parseInt(document.getElementById('wpm').value);
    settings.gain = parseFloat(document.getElementById('gain').value);
    settings.squelch = parseInt(document.getElementById('squelch').value) / 100;
    settings.device_id = document.getElementById('device-select').value
        ? parseInt(document.getElementById('device-select').value) : null;

    localStorage.setItem('decoder_gain', settings.gain.toString());
    localStorage.setItem('decoder_squelch', settings.squelch.toString());
    document.getElementById('wpm-display').textContent = settings.wpm;
    closeSettings();
}

async function fetchDevices() {
    try {
        const resp = await fetch('/api/devices');
        const data = await resp.json();
        const select = document.getElementById('device-select');
        select.innerHTML = '<option value="">默认设备</option>';
        data.devices.forEach(dev => {
            const opt = document.createElement('option');
            opt.value = dev.id;
            opt.textContent = `${dev.id}: ${dev.name}`;
            select.appendChild(opt);
        });
    } catch (e) { console.error(e); }
}

document.addEventListener('DOMContentLoaded', init);
