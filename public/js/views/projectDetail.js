import { el, clear, toast, fmt2 } from '../dom.js';
import { api } from '../api.js';
import { renderLineItemsPanel } from './lineItemsPanel.js';

const SUMMARY_CATEGORY = 'Resumen';

export async function renderProjectDetail(container, navigate, projectId) {
  clear(container);
  const baseUrl = `/api/projects/${projectId}`;
  let proj, calc;
  try {
    proj = await api.get(baseUrl);
    calc = await api.get(`${baseUrl}/calculate`);
  } catch (err) {
    container.appendChild(el('div', { class: 'empty' }, `Error: ${err.message}`));
    return;
  }

  container.appendChild(el('div', { class: 'toolbar' }, [
    el('button', { onClick: () => navigate('#/proyectos') }, '← Volver a proyectos'),
  ]));
  container.appendChild(el('h1', {}, proj.name));
  container.appendChild(el('p', { class: 'subtitle' }, `Plantilla origen: ${proj.template_name_snapshot || '—'} (v${proj.template_version_snapshot ?? '?'})`));

  const summaryItems = proj.line_items.filter((it) => it.category === SUMMARY_CATEGORY);
  const kpis = summaryItems.length
    ? summaryItems.map((it) => {
      const r = calc.results[it.key];
      return el('div', { class: `kpi ${r && r.error ? 'error' : ''}` }, [
        el('div', { class: 'label' }, it.name),
        el('div', { class: 'value' }, r && r.error ? '⚠ error' : (r ? fmt2(r.value) : '')),
      ]);
    })
    : [];
  const errorCount = Object.values(calc.results).filter((r) => r.error).length;
  container.appendChild(el('div', { class: 'kpi-row' }, [
    ...kpis,
    el('div', { class: `kpi ${errorCount ? 'error' : ''}` }, [el('div', { class: 'label' }, 'Estado del cálculo'), el('div', { class: 'value' }, errorCount ? `${errorCount} con error` : 'OK')]),
  ]));

  container.appendChild(el('h2', {}, 'Variables del proyecto'));
  container.appendChild(el('p', { class: 'hint' }, 'Edite los valores de entrada — el presupuesto se recalcula en cascada automáticamente.'));
  renderVariables(container);

  container.appendChild(el('h2', {}, 'Partidas y fórmulas'));
  const itemsContainer = el('div');
  container.appendChild(itemsContainer);
  renderLineItemsPanel(itemsContainer, {
    baseUrl, items: proj.line_items, calc,
    onChange: () => renderProjectDetail(container, navigate, projectId),
  });

  function renderVariables(root) {
    const panel = el('div', { class: 'panel' });
    root.appendChild(panel);
    if (!proj.variables.length) {
      panel.appendChild(el('div', { class: 'empty' }, 'Esta plantilla no define variables.'));
      return;
    }
    const tableWrap = el('div', { class: 'table-wrap' });
    panel.appendChild(tableWrap);
    const table = el('table', {}, el('thead', {}, el('tr', {}, [
      el('th', {}, 'Key'), el('th', {}, 'Etiqueta'), el('th', { class: 'num' }, 'Valor'), el('th', {}, 'Unidad'),
    ])));
    const tbody = el('tbody');
    for (const v of proj.variables) {
      const input = el('input', { type: 'number', step: 'any', value: v.value, style: 'width:160px' });
      input.addEventListener('change', async () => {
        try {
          await api.put(`${baseUrl}/variables/${v.id}`, { value: Number(input.value || 0) });
          toast(`"${v.key}" actualizado — recalculando`);
          renderProjectDetail(container, navigate, projectId);
        } catch (err) { toast(err.message, 'error'); }
      });
      tbody.appendChild(el('tr', {}, [
        el('td', {}, el('span', { class: 'badge var' }, v.key)),
        el('td', {}, v.label),
        el('td', { class: 'num' }, input),
        el('td', {}, v.unit || ''),
      ]));
    }
    table.appendChild(tbody);
    tableWrap.appendChild(table);
  }
}
