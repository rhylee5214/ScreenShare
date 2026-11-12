const keyEl=document.getElementById("key"), deviceEl=document.getElementById("device");
const statusEl=document.getElementById("status");
let pollTimer=null, activeId=null;
function auth(){return {"Authorization":"Bearer "+keyEl.value.trim(),"Content-Type":"application/json"}}
document.getElementById("request").onclick=async()=>{
  const device_id=deviceEl.value.trim();
  if(!/^[a-f0-9]{32}$/.test(device_id)){statusEl.textContent="Enter the 32-character pairing ID from the remote app.";return}
  if(!keyEl.value.trim()){statusEl.textContent="Enter your admin key.";return}
  try{
    const r=await fetch("/api/requests",{method:"POST",headers:auth(),body:JSON.stringify({device_id})});
    const d=await r.json(); if(!r.ok)throw new Error(d.detail||"Request failed");
    activeId=d.request_id; statusEl.textContent="Request sent. Waiting for the computer owner to approve or deny…";
    if(pollTimer)clearInterval(pollTimer);
    pollTimer=setInterval(checkStatus,2000); checkStatus();
  }catch(e){statusEl.textContent="Error: "+e.message}
};
async function checkStatus(){
 if(!activeId)return;
 try{
  const r=await fetch("/api/requests/"+activeId,{headers:auth()}); const d=await r.json();
  if(!r.ok)throw new Error(d.detail||"Status check failed");
  if(d.status==="approved"){
    clearInterval(pollTimer);pollTimer=null;
    statusEl.innerHTML='Approved. The owner must still choose a screen. <a style="color:#93c5fd" target="_blank" rel="noopener" href="/view/'+encodeURIComponent(activeId)+'">Open live viewer</a>';
  }else if(d.status==="denied"){clearInterval(pollTimer);pollTimer=null;statusEl.textContent="The computer owner denied the request."}
 }catch(e){statusEl.textContent="Status error: "+e.message}
}
document.getElementById("clear").onclick=()=>{if(pollTimer)clearInterval(pollTimer);activeId=null;deviceEl.value="";statusEl.textContent="Cleared."};
