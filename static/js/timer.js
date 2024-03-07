setInterval(()=>{
    document.querySelector('#time').textContent = new Date().toLocaleString();
}, 100)