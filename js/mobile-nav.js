function initMobileNav() {
  var toggle = document.getElementById('mobile-nav-toggle');
  var sideNav = document.getElementById('side-nav');
  if (!toggle || !sideNav) return;

  toggle.addEventListener('click', function(event) {
    event.stopPropagation();
    sideNav.classList.toggle('open');
  });

  sideNav.querySelectorAll('a').forEach(function(link) {
    link.addEventListener('click', function() {
      sideNav.classList.remove('open');
    });
  });

  document.addEventListener('click', function(e) {
    if (!sideNav.contains(e.target) && e.target !== toggle) {
      sideNav.classList.remove('open');
    }
  });
}
