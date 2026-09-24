document.documentElement.classList.add('js');

function applyAccessibility(settings) {
  const root = document.documentElement;
  root.dataset.theme = settings.theme || 'normal';
  root.dataset.size = settings.size || 'normal';
  root.dataset.spacing = settings.spacing ? 'wide' : 'normal';
  root.dataset.images = settings.images ? 'hidden' : 'visible';
}

function readAccessibility() {
  try {
    return JSON.parse(localStorage.getItem('accessibility')) || {};
  } catch (error) {
    return {};
  }
}

applyAccessibility(readAccessibility());
