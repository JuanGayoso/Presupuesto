export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v !== undefined && v !== null && v !== false) node.setAttribute(k, v === true ? '' : v);
  }
  const arr = Array.isArray(children) ? children : [children];
  for (const c of arr) {
    if (c === undefined || c === null || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

export function fmt2(n) {
  if (n === null || n === undefined || n === '' || Number.isNaN(Number(n))) return '';
  return Number(n).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function toast(msg, type = 'ok') {
  const root = document.getElementById('toast-root');
  const node = el('div', { class: `toast ${type}` }, msg);
  root.appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

export function confirmDialog(message) {
  return new Promise((resolve) => {
    const backdrop = el('div', { class: 'modal-backdrop' });
    const modal = el('div', { class: 'modal', style: 'width:420px' }, [
      el('h3', {}, 'Confirmar'),
      el('p', {}, message),
      el('div', { class: 'modal-actions' }, [
        el('button', { onClick: () => { backdrop.remove(); resolve(false); } }, 'Cancelar'),
        el('button', { class: 'danger', onClick: () => { backdrop.remove(); resolve(true); } }, 'Eliminar'),
      ]),
    ]);
    backdrop.appendChild(modal);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) { backdrop.remove(); resolve(false); } });
    document.body.appendChild(backdrop);
  });
}

export function openModal(title, contentNode, { width } = {}) {
  const backdrop = el('div', { class: 'modal-backdrop' });
  const modal = el('div', { class: 'modal', style: width ? `width:${width}` : undefined }, [
    el('h3', {}, title),
    contentNode,
  ]);
  backdrop.appendChild(modal);
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) backdrop.remove(); });
  document.body.appendChild(backdrop);
  return { backdrop, modal, close: () => backdrop.remove() };
}
