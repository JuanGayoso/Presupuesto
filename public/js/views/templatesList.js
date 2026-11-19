import { el, clear, toast, confirmDialog, openModal } from '../dom.js';
import { api } from '../api.js';
import { buildForm } from '../form.js';

export async function renderTemplatesList(container, navigate) {
  clear(container);
  container.appendChild(el('h1', {}, 'Plantillas'));
  container.appendChild(el('p', { class: 'subtitle' }, 'Conjuntos reutilizables de partidas y fórmulas, sin datos de proyecto específico. Un proyecto nuevo se crea duplicando una plantilla.'));

  const panel = el('div', { class: 'panel' });
  container.appendChild(panel);
  panel.appendChild(el('div', { class: 'toolbar' }, [
    el('div', { class: 'spacer' }),
    el('button', { class: 'primary', onClick: openNewForm }, '+ Nueva plantilla'),
  ]));
  const tableWrap = el('div', { class: 'table-wrap' });
  panel.appendChild(tableWrap);

  let list;
  try {
    list = await api.get('/api/templates');
  } catch (err) {
    tableWrap.appendChild(el('div', { class: 'empty' }, `Error: ${err.message}`));
    return;
  }
  if (!list.length) {
    tableWrap.appendChild(el('div', { class: 'empty' }, 'Sin plantillas aún.'));
    return;
  }
  const table = el('table', {}, el('thead', {}, el('tr', {}, [
    el('th', {}, 'Nombre'), el('th', {}, 'Descripción'), el('th', {}, 'Versión'), el('th', {}, 'Actualizada'), el('th', {}, ''),
  ])));
  const tbody = el('tbody');
  for (const t of list) {
    tbody.appendChild(el('tr', {}, [
      el('td', {}, t.name),
      el('td', { class: 'wrap' }, t.description || ''),
      el('td', {}, `v${t.version}`),
      el('td', {}, new Date(t.updated_at).toLocaleString('es-PE')),
      el('td', {}, [
        el('button', { class: 'small primary', onClick: () => navigate(`#/plantillas/${t.id}`) }, 'Abrir'),
        ' ',
        el('button', { class: 'small', onClick: () => onDuplicate(t) }, 'Duplicar'),
        ' ',
        el('button', { class: 'small danger', onClick: () => onDelete(t) }, 'Borrar'),
      ]),
    ]));
  }
  table.appendChild(tbody);
  tableWrap.appendChild(table);

  async function onDuplicate(t) {
    try {
      const clone = await api.post(`/api/templates/${t.id}/duplicate`);
      toast(`Plantilla duplicada como "${clone.name}"`);
      navigate(`#/plantillas/${clone.id}`);
    } catch (err) { toast(err.message, 'error'); }
  }

  async function onDelete(t) {
    const ok = await confirmDialog(`¿Eliminar la plantilla "${t.name}"? Los proyectos ya creados a partir de ella no se ven afectados (son copias independientes).`);
    if (!ok) return;
    try {
      await api.del(`/api/templates/${t.id}`);
      toast('Plantilla eliminada');
      renderTemplatesList(container, navigate);
    } catch (err) { toast(err.message, 'error'); }
  }

  async function openNewForm() {
    const form = await buildForm([
      { key: 'name', label: 'Nombre', required: true },
      { key: 'description', label: 'Descripción', type: 'textarea' },
    ]);
    const { close } = openModal('Nueva plantilla', el('div', {}, [
      form.node,
      el('div', { class: 'modal-actions' }, [
        el('button', { onClick: () => close() }, 'Cancelar'),
        el('button', { class: 'primary', onClick: save }, 'Crear'),
      ]),
    ]));
    async function save() {
      const values = form.getValues();
      if (!values.name) { toast('El nombre es requerido', 'error'); return; }
      try {
        const tpl = await api.post('/api/templates', values);
        toast('Plantilla creada');
        close();
        navigate(`#/plantillas/${tpl.id}`);
      } catch (err) { toast(err.message, 'error'); }
    }
  }
}
