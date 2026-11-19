import { el, clear } from './dom.js';
import { renderTemplatesList } from './views/templatesList.js';
import { renderTemplateDetail } from './views/templateDetail.js';
import { renderProjectsList } from './views/projectsList.js';
import { renderProjectDetail } from './views/projectDetail.js';

const NAV = [
  { path: '#/proyectos', label: 'Proyectos' },
  { path: '#/plantillas', label: 'Plantillas' },
];

const nav = document.getElementById('nav');
const main = document.getElementById('main');

function renderNav(currentHash) {
  clear(nav);
  nav.appendChild(el('div', { class: 'nav-group' }, 'Navegación'));
  for (const item of NAV) {
    const active = currentHash.startsWith(item.path);
    nav.appendChild(el('a', { class: `nav-link ${active ? 'active' : ''}`, href: item.path }, item.label));
  }
}

function navigate(hash) {
  if (location.hash === hash) { router(); return; }
  location.hash = hash;
}

async function router() {
  const hash = location.hash || '#/proyectos';
  renderNav(hash);
  const parts = hash.replace(/^#\//, '').split('/').filter(Boolean);

  try {
    if (parts[0] === 'proyectos' && parts.length === 1) {
      await renderProjectsList(main, navigate);
    } else if (parts[0] === 'proyectos' && parts.length >= 2) {
      await renderProjectDetail(main, navigate, Number(parts[1]));
    } else if (parts[0] === 'plantillas' && parts.length === 1) {
      await renderTemplatesList(main, navigate);
    } else if (parts[0] === 'plantillas' && parts.length >= 2) {
      await renderTemplateDetail(main, navigate, Number(parts[1]));
    } else {
      navigate('#/proyectos');
    }
  } catch (err) {
    clear(main);
    main.appendChild(el('div', { class: 'empty' }, `Error inesperado: ${err.message}`));
    console.error(err);
  }
}

window.addEventListener('hashchange', router);
router();
