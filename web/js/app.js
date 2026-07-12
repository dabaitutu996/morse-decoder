const ws = new WebSocket(`ws://${window.location.host}/ws`);

ws.onopen = () => {
    console.log('WebSocket connected');
    ws.send(JSON.stringify({ type: 'start' }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = (err) => {
    console.error('WebSocket error:', err);
};
