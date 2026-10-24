// Shared Custom Interactive Cursor and Global Helpers
(function() {
  const dot = document.getElementById('cursorDot');
  const ring = document.getElementById('cursorRing');
  if (!dot || !ring) return;

  // Track position
  let mouseX = -100, mouseY = -100;
  let ringX = -100, ringY = -100;

  window.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.transform = `translate(${mouseX}px, ${mouseY}px)`;
  });

  // Smooth lerp trailing animation for outer ring
  function animateRing() {
    ringX += (mouseX - ringX) * 0.18;
    ringY += (mouseY - ringY) * 0.18;
    ring.style.transform = `translate(${ringX}px, ${ringY}px)`;
    requestAnimationFrame(animateRing);
  }
  animateRing();

  // Hover expand effects on interactive links & buttons
  const interactives = 'a, button, input, select, textarea, .option, .icon-btn, .change-account-btn';
  document.addEventListener('mouseover', (e) => {
    if (e.target.closest(interactives)) {
      ring.classList.add('cursor-hover');
      dot.classList.add('dot-hover');
    }
  });

  document.addEventListener('mouseout', (e) => {
    if (e.target.closest(interactives)) {
      ring.classList.remove('cursor-hover');
      dot.classList.remove('dot-hover');
    }
  });

  // Click pulse animation
  document.addEventListener('mousedown', () => {
    ring.classList.add('cursor-click');
  });

  document.addEventListener('mouseup', () => {
    ring.classList.remove('cursor-click');
  });
})();
