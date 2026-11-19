import { el, clear, toast, confirmDialog, openModal, fmt2 } from '../dom.js';
import { api } from '../api.js';
import { buildForm } from '../form.js';
import { renderLineItemsPanel } from './lineItemsPanel.js';

export async function renderTemplateDetail(container, navigate, templateId) {
  clear(container);
  const baseUrl = `/api/templates/${templateId}`;
  let tpl, calc;
  try {
    tpl = await api.get(baseUrl);
    calc = await api.get(`${baseUrl}/calculate`);
  } catch (err) {
    container.appendChild(el('div', { class: 'empty' }, `Error: ${err.message}`));
    return;
  }

  container.appendChild(el('div', { class: 'toolbar' }, [
    el('button', { onClick: () => navigate('#/plantillas') }, '← Volver a plantillas'),
  ]));
  container.appendChild(el('h1', {}, tpl.name));
  container.appendChild(el('p', { class: 'subtitle' }, [
    `Versión ${tpl.version} · ${tpl.description || 'Sin descripción'}  `,
    el('button', { class: 'small', style: 'margin-left:8px', onClick: openEditInfo }, 'Editar'),
  ]));

  const errorCount = Object.values(calc.results).filter((r) => r.error).length;
  container.appendChild(el('div', { class: 'kpi-row' }, [
    el('div', { class: 'kpi' }, [el('div', { class: 'label' }, 'Variables'), el('div', { class: 'value' }, tpl.variables.length)]),
    el('div', { class: 'kpi' }, [el('div', { class: 'label' }, 'Partidas'), el('div', { class: 'value' }, tpl.line_items.length)]),
    el('div', { class: `kpi ${errorCount ? 'error' : ''}` }, [el('div', { class: 'label' }, 'Cálculo (con valores por defecto)'), el('div', { class: 'value' }, errorCount ? `${errorCount} con error` : 'OK')]),
  ]));

  container.appendChild(el('h2', {}, 'Variables del proyecto'));
  container.appendChild(el('p', { class: 'hint' }, 'Inputs base (áreas, UIT, tipo de cambio, etc.) que las fórmulas pueden referenciar por su key.'));
  renderVariables(container);

  container.appendChild(el('h2', {}, 'Partidas y fórmulas'));
  const itemsContainer = el('div');
  container.appendChild(itemsContainer);
  renderLineItemsPanel(itemsContainer, {
    baseUrl, items: tpl.line_items, calc,
    onChange: () => renderTemplateDetail(container, navigate, templateId),
  });

  function renderVariables(root) {
    const panel = el('div', { class: 'panel' });
    root.appendChild(panel);
    panel.appendChild(el('div', { class: 'toolbar' }, [
      el('div', { class: 'spacer' }),
      el('button', { class: 'primary', onClick: () => openVarForm(null) }, '+ Nueva variable'),
    ]));
    if (!tpl.variables.length) {
      panel.appendChild(el('div', { class: 'empty' }, 'Sin variables. Agregue inputs como área vendible, UIT, tipo de cambio.'));
      return;
    }
    const tableWrap = el('div', { class: 'table-wrap' });
    panel.appendChild(tableWrap);
    const table = el('table', {}, el('thead', {}, el('tr', {}, [
      el('th', {}, 'Key'), el('th', {}, 'Etiqueta'), el('th', { class: 'num' }, 'Valor por defecto'), el('th', {}, 'Unidad'), el('th', {}, ''),
    ])));
    const tbody = el('tbody');
    for (const v of tpl.variables) {
      tbody.appendChild(el('tr', {}, [
        el('td', {}, el('span', { class: 'badge var' }, v.key)),
        el('td', {}, v.label),
        el('td', { class: 'num' }, fmt2(v.default_value)),
        el('td', {}, v.unit || ''),
        el('td', {}, [
          el('button', { class: 'small', onClick: () => openVarForm(v) }, 'Editar'),
          ' ',
          el('button', { class: 'small danger', onClick: () => onDeleteVar(v) }, 'Borrar'),
        ]),
      ]));
    }
    table.appendChild(tbody);
    tableWrap.appendChild(table);
  }

  async function onDeleteVar(v) {
    const ok = await confirmDialog(`¿Eliminar la variable "${v.key}"? Cualquier fórmula que la referencie quedará con error.`);
    if (!ok) return;
    try {
      await api.del(`${baseUrl}/variables/${v.id}`);
      toast('Variable eliminada');
      renderTemplateDetail(container, navigate, templateId);
    } catch (err) { toast(err.message, 'error'); }
  }

  async function openVarForm(v) {
    const isEdit = !!v;
    const form = await buildForm([
      { key: 'key', label: 'Key (identificador único)', required: true, value: v ? v.key : '' },
      { key: 'label', label: 'Etiqueta', required: true, value: v ? v.label : '' },
      { key: 'default_value', label: 'Valor por defecto', type: 'number', step: 'any', value: v ? v.default_value : 0 },
      { key: 'unit', label: 'Unidad (opcional)', value: v ? (v.unit || '') : '' },
    ]);
    const { close } = openModal(isEdit ? `Editar variable: ${v.key}` : 'Nueva variable', el('div', {}, [
      form.node,
      el('div', { class: 'modal-actions' }, [
        el('button', { onClick: () => close() }, 'Cancelar'),
        el('button', { class: 'primary', onClick: save }, isEdit ? 'Guardar' : 'Crear'),
      ]),
    ]));
    async function save() {
      const values = form.getValues();
      values.order = v ? v.order : tpl.variables.length + 1;
      if (!values.key || !values.label) { toast('Key y etiqueta son requeridos', 'error'); return; }
      try {
        if (isEdit) await api.put(`${baseUrl}/variables/${v.id}`, values);
        else await api.post(`${baseUrl}/variables`, values);
        toast(isEdit ? 'Variable actualizada' : 'Variable creada');
        close();
        renderTemplateDetail(container, navigate, templateId);
      } catch (err) { toast(err.message, 'error'); }
    }
  }

  async function openEditInfo() {
    const form = await buildForm([
      { key: 'name', label: 'Nombre', required: true, value: tpl.name },
      { key: 'description', label: 'Descripción', type: 'textarea', value: tpl.description || '' },
    ]);
    const { close } = openModal('Editar plantilla', el('div', {}, [
      form.node,
      el('div', { class: 'modal-actions' }, [
        el('button', { onClick: () => close() }, 'Cancelar'),
        el('button', { class: 'primary', onClick: save }, 'Guardar'),
      ]),
    ]));
    async function save() {
      try {
        await api.put(baseUrl, form.getValues());
        toast('Plantilla actualizada');
        close();
        renderTemplateDetail(container, navigate, templateId);
      } catch (err) { toast(err.message, 'error'); }
    }
  }
}
