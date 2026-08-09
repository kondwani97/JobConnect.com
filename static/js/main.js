// JobConnect — light-weight UI interactions (no framework, no build step)

document.addEventListener('DOMContentLoaded', function () {

  // ---- Star rating picker (used on rate_worker.html) ----
  const starWrap = document.querySelector('[data-star-picker]');
  if (starWrap) {
    const input = document.querySelector('#stars-input');
    const stars = Array.from(starWrap.querySelectorAll('.star-choice'));
    const paint = (value) => {
      stars.forEach(s => {
        s.classList.toggle('is-active', Number(s.dataset.value) <= value);
      });
    };
    stars.forEach(s => {
      s.addEventListener('mouseenter', () => paint(Number(s.dataset.value)));
      s.addEventListener('click', () => {
        input.value = s.dataset.value;
        paint(Number(s.dataset.value));
      });
    });
    starWrap.addEventListener('mouseleave', () => paint(Number(input.value || 0)));
    paint(Number(input.value || 0));
  }

  // ---- Show/hide password ----
  document.querySelectorAll('[data-toggle-password]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.togglePassword);
      if (!target) return;
      target.type = target.type === 'password' ? 'text' : 'password';
      btn.textContent = target.type === 'password' ? 'Show' : 'Hide';
    });
  });

  // ---- Registration form: toggle worker/employer only fields ----
  const roleRadios = document.querySelectorAll('input[name="role"]');
  if (roleRadios.length) {
    const workerFields = document.querySelector('[data-worker-fields]');
    const employerFields = document.querySelector('[data-employer-fields]');
    const sync = () => {
      const role = document.querySelector('input[name="role"]:checked');
      const val = role ? role.value : '';
      if (workerFields) workerFields.style.display = val === 'worker' ? '' : 'none';
      if (employerFields) employerFields.style.display = val === 'employer' ? '' : 'none';
    };
    roleRadios.forEach(r => r.addEventListener('change', sync));
    sync();
  }

  // ---- Confirm before destructive actions (reject application, etc.) ----
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', (e) => {
      if (!confirm(el.dataset.confirm)) e.preventDefault();
    });
  });

  // ---- Bio / textarea character counter ----
  document.querySelectorAll('[data-maxcount]').forEach(field => {
    const max = Number(field.dataset.maxcount);
    const counter = document.getElementById(field.dataset.counterFor);
    if (!counter) return;
    const update = () => { counter.textContent = `${field.value.length} / ${max}`; };
    field.addEventListener('input', update);
    update();
  });

});
