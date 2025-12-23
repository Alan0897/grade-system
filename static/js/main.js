// Small UI helpers: mobile nav toggle and confirm dialogs
document.addEventListener('DOMContentLoaded', function(){
  var toggle = document.getElementById('nav-toggle');
  if(toggle){
    toggle.addEventListener('click', function(){
      document.querySelector('.nav-links').classList.toggle('open');
    });
  }

  // confirmation for elements with data-confirm attribute
  document.querySelectorAll('[data-confirm]').forEach(function(el){
    el.addEventListener('click', function(e){
      var msg = el.getAttribute('data-confirm') || '確定嗎？';
      if(!confirm(msg)){
        e.preventDefault();
      }
    });
  });
});