import { el, clear, toast, confirmDialog, openModal, fmt2 } from '../dom.js';
import { api } from '../api.js';
import { buildForm } from '../form.js';

// opts: { baseUrl, items, calc: {results, order}, onChange }
// baseUrl e.g. '/api/templates/12' or '/api/projects/7'
export function renderLineItemsPanel(container, opts) {
  const { baseUrl, items, calc, onChange } = opts;
  clear(container);

  const resultsByKey = calc ? calc.results : {};

  const toolbar = el('div', { class: 'toolbar' }, [
    el('div', {}, [
      el('strong', {}, `${items.length} partida(s)`),
      calc && calc.has_errors ? el('span', { class: 'badge err', style: 'margin-left:10px' }, '⚠ hay errores de cálculo') : null,
    ]),
    el('div', { class: 'spacer' }),
    el('button', { class: 'primary', onClick: () => openItemForm(null) }, '+ Nueva partida'),
  ]);
  container.appendChild(toolbar);

  if (!items.length) {
    container.appendChild(el('div', { class: 'empty' }, 'Sin partidas. Use "+ Nueva partida" para crear la primera (ej. Terreno).'));
    return;
  }

  const tableWrap = el('div', { class: 'table-wrap' });
  container.appendChild(tableWrap);
  const table = el('table', {}, el('thead', {}, el('tr', {}, [
    el('th', {}, 'Key'), el('th', {}, 'Nombre'), el('th', {}, 'Categoría'),
    el('th', {}, 'Fórmula'), el('th', {}, 'Depende de'),
    el('th', { class: 'num' }, 'Valor'), el('th', {}, ''),
  ])));
  const tbody = el('tbody');
  const byKey = new Map(items.map((it) => [it.key, it]));

  const orderedItems = calc && calc.order ? calc.order.filter((k) => byKey.has(k)).map((k) => byKey.get(k)) : items;

  for (const it of orderedItems) {
    const r = resultsByKey[it.key];
    const hasError = r && r.error;
    const indent = it.parent_key ? 'tree-indent-1' : '';
    tbody.appendChild(el('tr', { class: hasError ? 'row-error' : '' }, [
      el('td', {}, [
        el('span', { class: indent }, it.key),
        it.is_aggregator ? el('span', { class: 'badge agg', style: 'margin-left:6px' }, 'suma') : null,
        it.applies_igv_compra ? el('span', { class: 'badge igv', style: 'margin-left:6px' }, 'IGV') : null,
      ]),
      el('td', {}, it.name),
      el('td', {}, it.category || ''),
      el('td', { class: 'wrap' }, it.is_aggregator
        ? el('span', { class: 'hint' }, `= suma de hijas (${items.filter((c) => c.parent_key === it.key).map((c) => c.key).join(', ') || '—'})`)
        : el('span', { class: 'formula-code' }, it.formula || '(sin fórmula)')),
      el('td', {}, el('div', { class: 'deps-list' }, (r ? r.depends_on : []).map((d) => el('span', {
        class: `dep-chip ${resultsByKey[d] ? '' : 'missing'}`,
      }, d)))),
      el('td', { class: 'num' }, hasError ? el('span', { class: 'error-text' }, r.error) : (r ? fmt2(r.value) : '')),
      el('td', {}, [
        el('button', { class: 'small', onClick: () => openItemForm(it) }, 'Editar'),
        ' ',
        el('button', { class: 'small', onClick: () => openHistory(it) }, 'Historial'),
        ' ',
        el('button', { class: 'small danger', onClick: () => onDelete(it) }, 'Borrar'),
      ]),
    ]));
  }
  table.appendChild(tbody);
  tableWrap.appendChild(table);

  async function onDelete(it) {
    const children = items.filter((c) => c.parent_key === it.key);
    const warn = children.length ? ` Tiene ${children.length} sub-partida(s) que quedarán sin padre.` : '';
    const ok = await confirmDialog(`¿Eliminar la partida "${it.key} — ${it.name}"?${warn}`);
    if (!ok) return;
    try {
      await api.del(`${baseUrl}/items/${it.id}`);
      toast('Partida eliminada');
      onChange();
    } catch (err) { toast(err.message, 'error'); }
  }

  async function openHistory(it) {
    let history;
    try {
      history = await api.get(`${baseUrl}/items/${it.id}/history`);
    } catch (err) { toast(err.message, 'error'); return; }
    const content = history.length
      ? el('div', { class: 'table-wrap' }, el('table', {}, [
        el('thead', {}, el('tr', {}, [el('th', {}, 'Fecha'), el('th', {}, 'Fórmula anterior'), el('th', {}, 'Fórmula nueva')])),
        el('tbody', {}, history.map((h) => el('tr', {}, [
          el('td', {}, new Date(h.changed_at).toLocaleString('es-PE')),
          el('td', {}, el('span', { class: 'formula-code' }, h.old_formula || '(vacío)')),
          el('td', {}, el('span', { class: 'formula-code' }, h.new_formula || '(vacío)')),
        ]))),
      ]))
      : el('div', { class: 'empty' }, 'Sin cambios registrados todavía.');
    openModal(`Historial: ${it.key}`, content, { width: '640px' });
  }

  async function openItemForm(it) {
    const isEdit = !!it;
    const parentOptions = [{ value: '', label: '(ninguno)' }, ...items.filter((o) => !it || o.key !== it.key).map((o) => ({ value: o.key, label: `${o.key} — ${o.name}` }))];

    const keyInput = el('input', { value: it ? it.key : '' });
    const nameInput = el('input', { value: it ? it.name : '', required: true });
    const categoryInput = el('input', { value: it ? (it.category || '') : '' });
    const parentSelect = el('select', {}, parentOptions.map((o) => el('option', { value: o.value, selected: it && it.parent_key === o.value }, o.label)));
    const aggCheckbox = el('input', { type: 'checkbox' });
    aggCheckbox.checked = it ? it.is_aggregator : false;
    const igvCheckbox = el('input', { type: 'checkbox' });
    igvCheckbox.checked = it ? it.applies_igv_compra : false;
    const formulaInput = el('textarea', { class: 'formula-input', rows: 3 });
    formulaInput.value = it && it.formula ? it.formula : '';
    const notesInput = el('textarea', { rows: 2 });
    notesInput.value = it ? (it.notes || '') : '';

    const formulaField = el('div', { class: 'field' }, [
      el('label', {}, 'Fórmula (referencia variables u otras partidas por su key)'),
      formulaInput,
      el('div', { class: 'hint' }, 'Ej: max(0, Terreno - 10*UIT) * 0.03  ·  funciones: max, min, round, sqrt, abs, ceil, floor, if(cond,a,b)'),
    ]);
    const depsPreview = el('div', { class: 'deps-list', style: 'margin-top:6px' });
    const formulaError = el('div', { class: 'error-text', style: 'margin-top:4px' });
    formulaField.appendChild(depsPreview);
    formulaField.appendChild(formulaError);

    async function validateLive() {
      const text = formulaInput.value.trim();
      clear(depsPreview);
      formulaError.textContent = '';
      if (!text) return;
      try {
        const res = await api.post('/api/formulas/validate', { formula: text });
        if (!res.valid) { formulaError.textContent = res.error; return; }
        for (const d of res.dependencies) {
          const known = items.some((x) => x.key === d) || d === 'IGV_COMPRAS';
          depsPreview.appendChild(el('span', { class: `dep-chip ${known ? '' : 'missing'}` }, d));
        }
      } catch (err) { /* validation endpoint down: ignore, not fatal */ }
    }
    formulaInput.addEventListener('input', () => { clearTimeout(formulaInput._t); formulaInput._t = setTimeout(validateLive, 300); });

    function updateAggVisibility() {
      formulaField.style.display = aggCheckbox.checked ? 'none' : '';
    }
    aggCheckbox.addEventListener('change', updateAggVisibility);

    const content = el('div', {}, [
      el('div', { class: 'form-grid' }, [
        el('div', { class: 'field' }, [el('label', {}, 'Key (identificador único, sin espacios)'), keyInput]),
        el('div', { class: 'field' }, [el('label', {}, 'Nombre'), nameInput]),
        el('div', { class: 'field' }, [el('label', {}, 'Categoría'), categoryInput]),
        el('div', { class: 'field' }, [el('label', {}, 'Partida padre (agrupa como sub-partida de)'), parentSelect]),
      ]),
      el('div', { class: 'field' }, [el('label', { style: 'display:flex;align-items:center;gap:8px' }, [aggCheckbox, 'Es una partida agregadora (su valor = suma de sus sub-partidas)'])]),
      el('div', { class: 'field' }, [el('label', { style: 'display:flex;align-items:center;gap:8px' }, [igvCheckbox, 'Aplica IGV de compras (18%, se suma automáticamente a IGV_COMPRAS)'])]),
      formulaField,
      el('div', { class: 'field' }, [el('label', {}, 'Notas (opcional)'), notesInput]),
      el('div', { class: 'modal-actions' }, [
        el('button', { onClick: () => close() }, 'Cancelar'),
        el('button', { class: 'primary', onClick: save }, isEdit ? 'Guardar' : 'Crear'),
      ]),
    ]);
    updateAggVisibility();
    if (isEdit) validateLive();
    const { close } = openModal(isEdit ? `Editar: ${it.key}` : 'Nueva partida', content, { width: '620px' });

    async function save() {
      const payload = {
        key: keyInput.value.trim(),
        name: nameInput.value.trim(),
        category: categoryInput.value.trim() || null,
        parent_key: parentSelect.value || null,
        is_aggregator: aggCheckbox.checked,
        applies_igv_compra: igvCheckbox.checked,
        formula: aggCheckbox.checked ? null : (formulaInput.value.trim() || null),
        notes: notesInput.value.trim() || null,
        order: it ? it.order : items.length + 1,
      };
      if (!payload.key || !payload.name) { toast('Key y nombre son requeridos', 'error'); return; }
      try {
        if (isEdit) await api.put(`${baseUrl}/items/${it.id}`, payload);
        else await api.post(`${baseUrl}/items`, payload);
        toast(isEdit ? 'Partida actualizada' : 'Partida creada');
        close();
        onChange();
      } catch (err) { toast(err.message, 'error'); }
    }
  }
}
