// UI helpers: reveal on scroll and counter animation
document.addEventListener('DOMContentLoaded', function(){
  // Reveal elements on scroll
  const observer = new IntersectionObserver((entries)=>{
    entries.forEach(entry=>{
      if(entry.isIntersecting){
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  },{threshold:0.12});

  document.querySelectorAll('.reveal').forEach(el=>observer.observe(el));

  // Counter animation
  const counters = document.querySelectorAll('.animate-counter');
  counters.forEach(el=>{
    const target = parseFloat(el.dataset.target||el.textContent.replace(/[^0-9.-]/g,''))||0;
    const suffix = el.dataset.suffix||'';
    let start = 0;
    const duration = 1400;
    const startTime = performance.now();
    function step(now){
      const progress = Math.min((now-startTime)/duration,1);
      const value = Math.floor(progress*target);
      el.textContent = value + suffix;
      if(progress<1) requestAnimationFrame(step);
      else el.textContent = Math.round(target) + suffix;
    }
    // only animate when visible
    const inObs = new IntersectionObserver((entries)=>{
      if(entries[0].isIntersecting){
        requestAnimationFrame(step);
        inObs.disconnect();
      }
    },{threshold:0.2});
    inObs.observe(el);
  });
});
