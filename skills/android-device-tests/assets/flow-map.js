(function () {
  var map = document.getElementById('map');
  var board = document.getElementById('board');
  var flow = document.getElementById('flow');
  var closer = document.getElementById('closer');
  var parts = map.querySelectorAll('[data-flows]');
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var level = 1;

  // Picking a flow fades everything that isn't on its path, and brings its first screen into view.
  flow.addEventListener('change', function () {
    var wanted = flow.value === '' ? null : ' ' + flow.value + ' ';
    var first = null;
    map.classList.toggle('picked', wanted !== null);
    parts.forEach(function (part) {
      var on = wanted === null || part.dataset.flows.indexOf(wanted) !== -1;
      part.classList.toggle('off', !on);
      if (on && wanted !== null && !first && part.classList.contains('screen')) first = part;
    });
    if (first) first.scrollIntoView({ block: 'center', inline: 'start', behavior: calm ? 'auto' : 'smooth' });
  });

  function zoom(to) {
    level = Math.min(2, Math.max(0.1, to));
    map.style.zoom = level;
  }
  function fit() {
    var style = getComputedStyle(board);
    var wide = board.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    var high = board.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
    zoom(Math.min(1, wide / map.dataset.width, high / map.dataset.height));
    board.scrollTo(0, 0);
  }
  document.getElementById('zoom-out').addEventListener('click', function () { zoom(level / 1.25); });
  document.getElementById('zoom-in').addEventListener('click', function () { zoom(level * 1.25); });
  document.getElementById('zoom-fit').addEventListener('click', fit);
  document.getElementById('zoom-full').addEventListener('click', function () { zoom(1); });

  // Pinching a trackpad, or turning the wheel with Ctrl or Cmd held, zooms around the pointer.
  board.addEventListener('wheel', function (event) {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    var box = board.getBoundingClientRect();
    var x = event.clientX - box.left;
    var y = event.clientY - box.top;
    var atX = (board.scrollLeft + x) / level;
    var atY = (board.scrollTop + y) / level;
    zoom(level * Math.exp(-event.deltaY * 0.01));
    board.scrollLeft = atX * level - x;
    board.scrollTop = atY * level - y;
  }, { passive: false });

  // A click on a picture shows it larger, with the flows that walk through it.
  map.addEventListener('click', function (event) {
    var picture = event.target.closest('.picture');
    if (!picture) return;
    var screen = picture.closest('.screen');
    var list = closer.querySelector('ul');
    closer.querySelector('h2').textContent = screen.dataset.name;
    closer.querySelector('img').src = picture.querySelector('img').src;
    list.textContent = '';
    screen.dataset.flows.trim().split(' ').forEach(function (number) {
      var item = document.createElement('li');
      item.textContent = flow.options[Number(number) + 1].text;
      list.appendChild(item);
    });
    closer.showModal();
  });
  closer.addEventListener('click', function (event) {
    if (!event.target.closest('.sheet') || event.target.closest('button')) closer.close();
  });
})();
