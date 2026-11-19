import { el, clear, toast, confirmDialog, openModal } from '../dom.js';
import { api } from '../api.js';
import { buildForm } from '../form.js';

export async function renderProjectsList(container, navigate) {
  clear(container);
  container.appendChild(el('h1', {}, 'Proyectos'));
  container.appendChild(el('p', { class: 'subtitle' }, 'Cada proyecto se crea duplicando una plantilla: hereda todas sus fórmulas y variables, de forma totalmente independiente.'));

  const panel = el('div', { class: 'panel' });
  container.appendChild(panel);
  panel.appendChild(el('div', { class: 'toolbar' }, [
    el('div', { class: 'spacer' }),
    el('button', { class: 'primary', onClick: openNewForm }, '+ Nuevo proyecto'),
  ]));
  const tableWrap = el('div', { class: 'table-wrap' });
  panel.appendChild(tableWrap);

  let list;
  try {
    list = await api.get('/api/projects');
  } catch (err) {
    tableWrap.appendChild(el('div', { class: 'empty' }, `Error: ${err.message}`));
    return;
  }
  if (!list.length) {
    tableWrap.appendChild(el('div', { class: 'empty' }, 'Sin proyectos aún. Cree uno a partir de una plantilla.'));
    return;
  }
  const table = el('table', {}, el('thead', {}, el('tr', {}, [
    el('th', {}, 'Nombre'), el('th', {}, 'Plantilla origen'), el('th', {}, 'Creado'), el('th', {}, 'Actualizado'), el('th', {}, ''),
  ])));
  const tbody = el('tbody');
  for (const p of list) {
    tbody.appendChild(el('tr', {}, [
      el('td', {}, p.name),
      el('td', {}, p.template_name_snapshot ? `${p.template_name_snapshot} (v${p.template_version_snapshot})` : '—'),
      el('td', {}, new Date(p.created_at).toLocaleDateString('es-PE')),
      el('td', {}, new Date(p.updated_at).toLocaleString('es-PE')),
      el('td', {}, [
        el('button', { class: 'small primary', onClick: () => navigate(`#/proyectos/${p.id}`) }, 'Abrir'),
        ' ',
        el('button', { class: 'small danger', onClick: () => onDelete(p) }, 'Borrar'),
      ]),
    ]));
  }
  table.appendChild(tbody);
  tableWrap.appendChild(table);

  async function onDelete(p) {
    const ok = await confirmDialog(`¿Eliminar el proyecto "${p.name}"? Esta acción no se puede deshacer.`);
    if (!ok) return;
    try {
      await api.del(`/api/projects/${p.id}`);
      toast('Proyecto eliminado');
      renderProjectsList(container, navigate);
    } catch (err) { toast(err.message, 'error'); }
  }

  async function openNewForm() {
    let templates;
    try {
      templates = await api.get('/api/templates');
    } catch (err) { toast(err.message, 'error'); return; }
    if (!templates.length) { toast('Primero cree una plantilla', 'error'); return; }
    const form = await buildForm([
      { key: 'name', label: 'Nombre del proyecto', required: true },
      { key: 'template_id', label: 'Plantilla', type: 'select', required: true, options: templates.map((t) => ({ value: t.id, label: `${t.name} (v${t.version})` })) },
    ]);
    const { close } = openModal('Nuevo proyecto', el('div', {}, [
      form.node,
      el('div', { class: 'modal-actions' }, [
        el('button', { onClick: () => close() }, 'Cancelar'),
        el('button', { class: 'primary', onClick: save }, 'Crear'),
      ]),
    ]));
    async function save() {
      const values = form.getValues();
      if (!values.name || !values.template_id) { toast('Complete los campos requeridos', 'error'); return; }
      try {
        const proj = await api.post('/api/projects', values);
        toast('Proyecto creado');
        close();
        navigate(`#/proyectos/${proj.id}`);
      } catch (err) { toast(err.message, 'error'); }
    }
  }
}
