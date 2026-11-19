import { el } from './dom.js';

// fields: [{key,label,type:'text'|'number'|'select'|'textarea'|'checkbox', required, options, step, value, mono}]
export async function buildForm(fields, values = {}) {
  const inputs = {};
  const nodes = [];
  for (const f of fields) {
    let input;
    const currentValue = values[f.key] ?? f.value ?? '';
    if (f.type === 'select') {
      const options = typeof f.options === 'function' ? await f.options() : (f.options || []);
      input = el('select', { required: f.required }, [
        el('option', { value: '' }, f.placeholder || 'Seleccione...'),
        ...options.map((o) => el('option', { value: String(o.value), selected: String(o.value) === String(currentValue) }, o.label)),
      ]);
    } else if (f.type === 'textarea') {
      input = el('textarea', { rows: f.rows || 3, required: f.required, class: f.mono ? 'formula-input' : '' }, []);
      input.value = currentValue;
    } else if (f.type === 'checkbox') {
      input = el('input', { type: 'checkbox' });
      input.checked = !!(values[f.key] ?? f.value ?? false);
    } else {
      input = el('input', {
        type: f.type === 'number' ? 'number' : 'text',
        step: f.step || (f.type === 'number' ? 'any' : undefined),
        required: f.required,
        placeholder: f.placeholder || '',
        class: f.mono ? 'formula-input' : '',
      });
      input.value = currentValue;
    }
    inputs[f.key] = input;
    const labelNode = f.type === 'checkbox'
      ? el('label', { style: 'display:flex;align-items:center;gap:8px;margin-bottom:0' }, [input, f.label])
      : el('div', { class: 'field' }, [el('label', {}, f.label), input, f.hint ? el('div', { class: 'hint' }, f.hint) : null]);
    nodes.push(f.type === 'checkbox' ? el('div', { class: 'field' }, [labelNode]) : labelNode);
  }
  const formGrid = el('div', { class: 'form-grid' }, nodes);
  return {
    node: formGrid,
    getValues() {
      const out = {};
      for (const f of fields) {
        if (f.type === 'checkbox') { out[f.key] = inputs[f.key].checked; continue; }
        const raw = inputs[f.key].value;
        out[f.key] = f.type === 'number' ? (raw === '' ? null : Number(raw)) : (raw === '' ? null : raw);
      }
      return out;
    },
    setError(key) {
      if (inputs[key]) inputs[key].style.borderColor = 'var(--danger)';
    },
  };
}
