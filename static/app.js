const text = document.getElementById('text');
const wc = document.getElementById('wc');
const cc = document.getElementById('cc');
const form = document.getElementById('summarize-form');
const spin = document.getElementById('spin');
const statusEl = document.getElementById('status');
const copyBtn = document.getElementById('copyBtn');
const downloadBtn = document.getElementById('downloadBtn');
const result = document.getElementById('result');

function updateCounts(){
  const val = (text?.value || '').trim();
  const words = val.length ? val.split(/\s+/).filter(Boolean).length : 0;
  wc.textContent = `${words} word${words===1?'':'s'}`;
  cc.textContent = `${val.length} character${val.length===1?'':'s'}`;
}
if (text){ updateCounts(); text.addEventListener('input', updateCounts); }

document.getElementById('clearBtn')?.addEventListener('click', ()=>{
  if (text){ text.value=''; updateCounts(); text.focus(); }
  const urlField = document.getElementById('url');
  if (urlField) urlField.value='';
});

form?.addEventListener('submit', ()=>{
  if (spin){ spin.style.display='inline-block'; }
  if (statusEl){ statusEl.textContent = 'Summarizing…'; }
});

copyBtn?.addEventListener('click', async ()=>{
  const summaryEl = document.querySelector('.summary');
  if (!summaryEl) return;
  try{
    await navigator.clipboard.writeText(summaryEl.textContent);
    copyBtn.textContent='Copied!';
    setTimeout(()=> copyBtn.textContent='Copy', 1200);
  }catch(e){
    alert('Copy failed.');
  }
});

downloadBtn?.addEventListener('click', ()=>{
  const summaryEl = document.querySelector('.summary');
  if (!summaryEl) return;
  const blob = new Blob([summaryEl.textContent], {type:'text/plain'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'summary.txt';
  a.click();
  URL.revokeObjectURL(a.href);
});
