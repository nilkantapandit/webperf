(function(){
  function icons(){ if(window.lucide) window.lucide.createIcons({attrs:{"stroke-width":1.8}}); }
  function cookies(){
    const banner=document.getElementById('cookieBanner');
    if(!banner || localStorage.getItem('webperf-cookie-notice-v1')) return;
    banner.classList.remove('hidden');
    const close=()=>{localStorage.setItem('webperf-cookie-notice-v1','seen');banner.classList.add('hidden');};
    document.getElementById('cookieEssentialOnly')?.addEventListener('click',close);
    document.getElementById('cookieAccept')?.addEventListener('click',close);
  }
  function reveal(){
    const items=document.querySelectorAll('.reveal-on-scroll');
    if(!('IntersectionObserver' in window)){items.forEach(x=>x.classList.add('is-visible'));return;}
    const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target);}}),{threshold:.08,rootMargin:'0px 0px -40px 0px'});
    items.forEach(x=>observer.observe(x));
  }
  const year=document.getElementById('footerYear'); if(year) year.textContent=new Date().getFullYear();
  icons(); cookies(); reveal();
})();
