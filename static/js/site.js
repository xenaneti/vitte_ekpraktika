const menuToggle = document.getElementById('menu-toggle');
const menu = document.getElementById('main-nav');

menuToggle.addEventListener('click', function () {
  const isOpen = menuToggle.getAttribute('aria-expanded') === 'true';
  menuToggle.setAttribute('aria-expanded', String(!isOpen));
  menu.classList.toggle('is-open', !isOpen);
});

document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape' && menu.classList.contains('is-open')) {
    menu.classList.remove('is-open');
    menuToggle.setAttribute('aria-expanded', 'false');
    menuToggle.focus();
  }
});

const accessToggle = document.getElementById('access-toggle');
const accessPanel = document.getElementById('access-panel');
const themeSelect = document.getElementById('access-theme');
const sizeSelect = document.getElementById('access-size');
const spacingInput = document.getElementById('access-spacing');
const imagesInput = document.getElementById('access-images');

function fillAccessibilityControls(settings) {
  themeSelect.value = settings.theme || 'normal';
  sizeSelect.value = settings.size || 'normal';
  spacingInput.checked = Boolean(settings.spacing);
  imagesInput.checked = Boolean(settings.images);
}

fillAccessibilityControls(readAccessibility());

accessToggle.addEventListener('click', function () {
  accessPanel.hidden = !accessPanel.hidden;
  accessToggle.setAttribute('aria-expanded', String(!accessPanel.hidden));
});

accessPanel.addEventListener('change', function () {
  const settings = {
    theme: themeSelect.value,
    size: sizeSelect.value,
    spacing: spacingInput.checked,
    images: imagesInput.checked
  };
  applyAccessibility(settings);
  try {
    localStorage.setItem('accessibility', JSON.stringify(settings));
  } catch (error) {
    // Настройки продолжают работать, если браузер запретил хранилище.
  }
});

document.getElementById('access-reset').addEventListener('click', function () {
  applyAccessibility({});
  fillAccessibilityControls({});
  try {
    localStorage.removeItem('accessibility');
  } catch (error) {
    // В приватном режиме хранилище может быть недоступно.
  }
});

function openLinkedArticle() {
  let id;
  try {
    id = decodeURIComponent(window.location.hash.slice(1));
  } catch (error) {
    return;
  }
  const target = document.getElementById(id);
  if (target && target.tagName === 'DETAILS') {
    target.open = true;
    target.scrollIntoView({block: 'start'});
  }
}

window.addEventListener('hashchange', openLinkedArticle);
openLinkedArticle();
