const MORSE_TREE = {
    char: null, dit: null, dah: null,
};
MORSE_TREE.dit = { char: 'E', dit: null, dah: null };
MORSE_TREE.dah = { char: 'T', dit: null, dah: null };
// Level 2
MORSE_TREE.dit.dit = { char: 'I', dit: null, dah: null };
MORSE_TREE.dit.dah = { char: 'A', dit: null, dah: null };
MORSE_TREE.dah.dit = { char: 'N', dit: null, dah: null };
MORSE_TREE.dah.dah = { char: 'M', dit: null, dah: null };
// Level 3
MORSE_TREE.dit.dit.dit = { char: 'S', dit: null, dah: null };
MORSE_TREE.dit.dit.dah = { char: 'U', dit: null, dah: null };
MORSE_TREE.dit.dah.dit = { char: 'R', dit: null, dah: null };
MORSE_TREE.dit.dah.dah = { char: 'W', dit: null, dah: null };
MORSE_TREE.dah.dit.dit = { char: 'D', dit: null, dah: null };
MORSE_TREE.dah.dit.dah = { char: 'K', dit: null, dah: null };
MORSE_TREE.dah.dah.dit = { char: 'G', dit: null, dah: null };
MORSE_TREE.dah.dah.dah = { char: 'O', dit: null, dah: null };
// Level 4
MORSE_TREE.dit.dit.dit.dit = { char: 'H', dit: null, dah: null };
MORSE_TREE.dit.dit.dit.dah = { char: 'V', dit: null, dah: null };
MORSE_TREE.dit.dit.dah.dit = { char: 'F', dit: null, dah: null };
MORSE_TREE.dit.dit.dah.dah = { char: ' ', dit: null, dah: null };
MORSE_TREE.dit.dah.dit.dit = { char: 'L', dit: null, dah: null };
MORSE_TREE.dit.dah.dit.dah = { char: ' ', dit: null, dah: null };
MORSE_TREE.dit.dah.dah.dit = { char: 'P', dit: null, dah: null };
MORSE_TREE.dit.dah.dah.dah = { char: 'J', dit: null, dah: null };
MORSE_TREE.dah.dit.dit.dit = { char: 'B', dit: null, dah: null };
MORSE_TREE.dah.dit.dit.dah = { char: 'X', dit: null, dah: null };
MORSE_TREE.dah.dit.dah.dit = { char: 'C', dit: null, dah: null };
MORSE_TREE.dah.dit.dah.dah = { char: 'Y', dit: null, dah: null };
MORSE_TREE.dah.dah.dit.dit = { char: 'Z', dit: null, dah: null };
MORSE_TREE.dah.dah.dit.dah = { char: 'Q', dit: null, dah: null };
MORSE_TREE.dah.dah.dah.dit = { char: ' ', dit: null, dah: null };
MORSE_TREE.dah.dah.dah.dah = { char: ' ', dit: null, dah: null };
// Level 5
MORSE_TREE.dit.dit.dit.dit.dit = { char: '5', dit: null, dah: null };
MORSE_TREE.dit.dit.dit.dit.dah = { char: '4', dit: null, dah: null };
MORSE_TREE.dit.dit.dit.dah.dah = { char: '3', dit: null, dah: null };
MORSE_TREE.dit.dit.dah.dah.dah = { char: '2', dit: null, dah: null };
MORSE_TREE.dit.dah.dah.dah.dah = { char: '1', dit: null, dah: null };
MORSE_TREE.dah.dit.dit.dit.dit = { char: '6', dit: null, dah: null };
MORSE_TREE.dah.dit.dit.dit.dah = { char: '=', dit: null, dah: null };
MORSE_TREE.dah.dit.dit.dah.dit = { char: '/', dit: null, dah: null };
MORSE_TREE.dah.dit.dah.dit.dah = { char: ';', dit: null, dah: null };
MORSE_TREE.dah.dit.dah.dah.dit = { char: '(', dit: null, dah: null };
MORSE_TREE.dah.dah.dit.dit.dit = { char: '7', dit: null, dah: null };
MORSE_TREE.dah.dah.dah.dit.dit = { char: '8', dit: null, dah: null };
MORSE_TREE.dah.dah.dah.dah.dit = { char: '9', dit: null, dah: null };
MORSE_TREE.dah.dah.dah.dah.dah = { char: '0', dit: null, dah: null };

class MorseTree {
    constructor(svgId) {
        this.svg = document.getElementById(svgId);
        this.nodes = new Map();
        this.lines = new Map();
        this.activePath = [];
        this.positions = new Map();
        this._resizeTimer = null;
    }

    init() {
        this.svg.innerHTML = '';
        this.nodes.clear();
        this.lines.clear();
        this.positions.clear();

        const rect = this.svg.parentElement.getBoundingClientRect();
        const width = Math.max(rect.width, 300);
        const height = Math.max(rect.height, 400);
        this.svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const centerX = width / 2;
        const topY = 50;
        const maxY = height - 60;
        const levels = 6;
        const levelH = (maxY - topY) / levels;

        // Layout: assign positions
        const layout = (node, depth, x, span) => {
            const y = topY + depth * levelH;
            this.positions.set(node, { x, y });
            if (node.dit) {
                layout(node.dit, depth + 1, x + span, span * 0.45);
            }
            if (node.dah) {
                layout(node.dah, depth + 1, x - span, span * 0.45);
            }
        };
        layout(MORSE_TREE, 0, centerX, width * 0.38);

        // Clamp positions to viewport
        this.positions.forEach((pos, node) => {
            pos.x = Math.max(25, Math.min(width - 25, pos.x));
        });

        // Draw connections (behind nodes)
        const drawLine = (parent, child, type) => {
            const pp = this.positions.get(parent);
            const cp = this.positions.get(child);
            if (!pp || !cp) return;

            const midX = (pp.x + cp.x) / 2;
            const d = `M ${pp.x} ${pp.y} L ${midX} ${pp.y} L ${midX} ${cp.y} L ${cp.x} ${cp.y}`;
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', d);
            path.setAttribute('class', 'tree-line');
            path.setAttribute('data-type', type);
            this.svg.appendChild(path);
            this.lines.set(`${parent}_${type}`, { path, child, parent });

            // Branch label (· or −)
            const lbl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            lbl.setAttribute('x', midX + (type === 'dit' ? 5 : -5));
            lbl.setAttribute('y', (pp.y + cp.y) / 2 - 4);
            lbl.setAttribute('text-anchor', type === 'dit' ? 'start' : 'end');
            lbl.setAttribute('class', 'branch-label');
            lbl.textContent = type === 'dit' ? '·' : '−';
            this.svg.appendChild(lbl);
        };

        const drawAllLines = (node) => {
            if (node.dit) { drawLine(node, node.dit, 'dit'); drawAllLines(node.dit); }
            if (node.dah) { drawLine(node, node.dah, 'dah'); drawAllLines(node.dah); }
        };
        drawAllLines(MORSE_TREE);

        // Draw nodes
        const drawNode = (node) => {
            const pos = this.positions.get(node);
            if (!pos) return;

            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('class', 'tree-node');

            const char = node.char;
            const r = (char && char !== ' ') ? 14 : 8;

            const pad = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            pad.setAttribute('cx', pos.x);
            pad.setAttribute('cy', pos.y);
            pad.setAttribute('r', r);
            pad.setAttribute('class', 'node-pad');
            g.appendChild(pad);

            if (char && char !== ' ') {
                const hole = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                hole.setAttribute('cx', pos.x);
                hole.setAttribute('cy', pos.y);
                hole.setAttribute('r', 5);
                hole.setAttribute('class', 'node-hole');
                g.appendChild(hole);

                const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                txt.setAttribute('x', pos.x);
                txt.setAttribute('y', pos.y + 26);
                txt.setAttribute('class', 'tree-label');
                txt.textContent = char;
                g.appendChild(txt);
            }

            this.svg.appendChild(g);
            this.nodes.set(node, { g, pad, text: g.querySelector('.tree-label') || null, pos });
        };

        const drawAllNodes = (node) => {
            drawNode(node);
            if (node.dit) drawAllNodes(node.dit);
            if (node.dah) drawAllNodes(node.dah);
        };
        drawAllNodes(MORSE_TREE);

        document.getElementById('current-letter').textContent = '-';
        document.getElementById('current-path').textContent = '路径: -';
    }

    initDebounced(delayMs = 150) {
        if (this._resizeTimer) clearTimeout(this._resizeTimer);
        this._resizeTimer = setTimeout(() => this.init(), delayMs);
    }

    resetPath() {
        this.activePath = [];
        this.svg.querySelectorAll('.active').forEach(el => el.classList.remove('active'));
        this._updatePathDisplay();
    }

    addToPath(symbol) {
        this.activePath.push(symbol);
        this._highlightPath();
    }

    goToLetter(letter) {
        // Trace path from root to the letter, highlight each step
        this.svg.querySelectorAll('.active').forEach(el => el.classList.remove('active'));

        const walk = (node, path) => {
            if (node.char === letter) {
                return path; // path and target node
            }
            if (node.dit) {
                const result = walk(node.dit, [...path, { node: node, symbol: '.', next: node.dit }]);
                if (result) return result;
            }
            if (node.dah) {
                const result = walk(node.dah, [...path, { node: node, symbol: '-', next: node.dah }]);
                if (result) return result;
            }
            return null;
        };

        const result = walk(MORSE_TREE, []);
        if (!result) {
            // Letter not in tree, just flash root
            const rootInfo = this.nodes.get(MORSE_TREE);
            if (rootInfo) {
                rootInfo.pad.classList.add('active');
                setTimeout(() => rootInfo.pad.classList.remove('active'), 300);
            }
            return;
        }

        // Animate the path step by step
        let delay = 0;
        for (const step of result) {
            const lineKey = `${step.node}_${step.symbol === '.' ? 'dit' : 'dah'}`;
            const lineInfo = this.lines.get(lineKey);
            if (lineInfo) {
                setTimeout(() => lineInfo.path.classList.add('active'), delay);
            }
            const childInfo = this.nodes.get(step.next);
            if (childInfo) {
                setTimeout(() => {
                    childInfo.pad.classList.add('active');
                    if (childInfo.text) childInfo.text.classList.add('active');
                }, delay + 50);
            }
            delay += 80;
        }

        // After the animation, flash the leaf node
        setTimeout(() => {
            this._ripple(result[result.length - 1].next);
        }, delay);

        const pathStr = result.map(s => s.symbol === '.' ? '·' : '−').join('');
        document.getElementById('current-path').textContent = `路径: ${pathStr || '-'}`;
    }

    _highlightPath() {
        this.svg.querySelectorAll('.active').forEach(el => el.classList.remove('active'));

        let node = MORSE_TREE;
        let pathStr = '';
        for (const symbol of this.activePath) {
            const type = symbol === '.' ? 'dit' : 'dah';
            const lineInfo = this.lines.get(`${node}_${type}`);
            if (!lineInfo) break;
            lineInfo.path.classList.add('active');
            node = lineInfo.child;
            pathStr += symbol === '.' ? '·' : '−';

            const nodeInfo = this.nodes.get(node);
            if (nodeInfo) {
                nodeInfo.pad.classList.add('active');
                if (nodeInfo.text) nodeInfo.text.classList.add('active');
            }
        }

        if (node && node.char && node.char !== ' ') {
            document.getElementById('current-letter').textContent = node.char;
            this._ripple(node);
        }
        this._updatePathDisplay(pathStr);
    }

    _ripple(node) {
        const nodeInfo = this.nodes.get(node);
        if (!nodeInfo) return;
        const ripple = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        ripple.setAttribute('cx', nodeInfo.pos.x);
        ripple.setAttribute('cy', nodeInfo.pos.y);
        ripple.setAttribute('r', 8);
        ripple.setAttribute('class', 'ripple');
        ripple.setAttribute('fill', 'none');
        ripple.setAttribute('stroke', '#E8450C');
        ripple.setAttribute('stroke-width', '2');
        this.svg.appendChild(ripple);
        setTimeout(() => ripple.remove(), 650);
    }

    _updatePathDisplay(pathStr = '') {
        document.getElementById('current-path').textContent = `路径: ${pathStr || '-'}`;
    }
}

window.MorseTree = MorseTree;
window.MORSE_TREE = MORSE_TREE;
